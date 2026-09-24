import pyodbc
import pandas as pd
import hashlib
import os
import threading
import time
from textwrap import dedent
from collections import defaultdict

CACHE_DIR = ".cache"

class DatabaseManager:
    def __init__(self, config):
        """
        Initialize with a config dictionary (from settings.ini section).
        Expects: server, port, database, username, password
        """
        self.server = config.get('server', 'localhost')
        self.port = config.get('port', '1433')
        self.database = config.get('database', 'MyData')
        self.username = config.get('username', 'sa')
        self.password = config.get('password', '')
        self.conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self):
        """Establish connection to SQL Server."""
        try:
            # Using ODBC Driver 17 for SQL Server is standard
            driver = '{ODBC Driver 17 for SQL Server}'
            
            conn_str = (
                f'DRIVER={driver};'
                f'SERVER={self.server},{self.port};'
                f'DATABASE={self.database};'
                f'UID={self.username};'
                f'PWD={self.password}'
            )
            
            self.conn = pyodbc.connect(conn_str, timeout=5)
            self.conn.timeout = 20 # Kill queries taking longer than 20 seconds
            return True, "Connected successfully"
        except Exception as e:
            return False, str(e)

    def _schema_fingerprint(self):
        """
        Returns a short, stable hash of the DB's structural state.
        Combines sys.objects.modify_date and extended_properties values so
        edits to descriptions also bust the cache.
        """
        if not self.conn:
            return None
        try:
            cursor = self.conn.cursor()
            cursor.execute(dedent("""
                SELECT
                    ISNULL((SELECT CHECKSUM_AGG(CHECKSUM(modify_date))
                            FROM sys.objects WHERE is_ms_shipped = 0), 0) AS obj_hash,
                    ISNULL((SELECT CHECKSUM_AGG(CHECKSUM(CAST(value AS NVARCHAR(MAX))))
                            FROM sys.extended_properties), 0) AS ep_hash
            """))
            obj_hash, ep_hash = cursor.fetchone()
            key = f"{self.server}|{self.database}|{obj_hash}|{ep_hash}"
            return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        except Exception:
            return None

    def _cache_path(self, fingerprint):
        return os.path.join(CACHE_DIR, f"schema_{fingerprint}.txt")

    def get_schema(self, force_refresh=False):
        """
        Fetch table and column information to build context for LLM.
        Cached to disk; invalidated when sys.objects.modify_date or
        extended_properties values change.
        """
        if not self.conn:
            return "Error: No database connection."

        fingerprint = self._schema_fingerprint()
        if fingerprint and not force_refresh:
            cache_file = self._cache_path(fingerprint)
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        return f.read()
                except Exception:
                    pass  # fall through to rebuild

        try:
            cursor = self.conn.cursor()

            # 1. Fetch all columns for relevant tables in ONE query
            schema_query = dedent("""
                SELECT 
                    t.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE
                FROM 
                    INFORMATION_SCHEMA.COLUMNS c
                JOIN 
                    INFORMATION_SCHEMA.TABLES t ON c.TABLE_NAME = t.TABLE_NAME
                WHERE 
                    t.TABLE_TYPE = 'BASE TABLE' 
                    AND t.TABLE_NAME NOT LIKE 'sys%'
                    AND t.TABLE_NAME NOT LIKE 'dt%'
                ORDER BY 
                    t.TABLE_NAME, c.ORDINAL_POSITION
            """)
            cursor.execute(schema_query)
            rows = cursor.fetchall()
            
            # Organize by Table
            schema_map = defaultdict(list)
            for table, col, dtype in rows:
                schema_map[table].append(f"{col} ({dtype})")
            
            # 2. Fetch Foreign Keys
            fk_query = dedent("""
                SELECT 
                    tp.name AS ParentTable,
                    cp.name AS ParentColumn,
                    tr.name AS ReferencedTable,
                    cr.name AS ReferencedColumn
                FROM 
                    sys.foreign_keys fk
                INNER JOIN 
                    sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                INNER JOIN 
                    sys.tables tp ON fkc.parent_object_id = tp.object_id
                INNER JOIN 
                    sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
                INNER JOIN 
                    sys.tables tr ON fkc.referenced_object_id = tr.object_id
                INNER JOIN 
                    sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            """)
            cursor.execute(fk_query)
            fk_rows = cursor.fetchall()
            
            fk_map = defaultdict(list)
            for p_table, p_col, r_table, r_col in fk_rows:
                fk_map[p_table].append(f"FK: {p_col} -> {r_table}.{r_col}")

            # 3. Fetch Indexes
            idx_query = dedent("""
                SELECT 
                    t.name AS TableName,
                    i.name AS IndexName,
                    c.name AS ColumnName,
                    i.type_desc AS IndexType,
                    i.is_unique,
                    i.is_primary_key
                FROM 
                    sys.indexes i
                JOIN 
                    sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                JOIN 
                    sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
                JOIN 
                    sys.tables t ON i.object_id = t.object_id
                WHERE 
                    t.is_ms_shipped = 0
                ORDER BY 
                    t.name, i.name, ic.key_ordinal
            """)
            cursor.execute(idx_query)
            idx_rows = cursor.fetchall()
            
            idx_map = defaultdict(lambda: defaultdict(list))
            for table, idx_name, col, idx_type, is_unique, is_pk in idx_rows:
                meta = []
                if is_unique: meta.append("UNIQUE")
                if is_pk: meta.append("PK")
                meta_str = f" ({', '.join(meta)})" if meta else ""
                
                # key by table -> index_name
                idx_map[table][f"{idx_name} [{idx_type}]{meta_str}"].append(col)

            # 4. Fetch Extended Properties
            ep_query = dedent("""
                SELECT 
                    t.name AS TableName,
                    c.name AS ColumnName,
                    ep.name AS PropertyName,
                    ep.value AS PropertyValue
                FROM 
                    sys.extended_properties ep
                JOIN 
                    sys.tables t ON ep.major_id = t.object_id
                LEFT JOIN 
                    sys.columns c ON ep.major_id = c.object_id AND ep.minor_id = c.column_id
                WHERE 
                    ep.class = 1
                ORDER BY 
                    t.name, c.name
            """)
            cursor.execute(ep_query)
            ep_rows = cursor.fetchall()
            
            ep_map = defaultdict(list)
            for table, col, prop_name, prop_val in ep_rows:
                target = f"{col}" if col else "TABLE"
                ep_map[table].append(f"{target}: {prop_name} = {prop_val}")

            # Construct Final String
            output_lines = []
            for table in sorted(schema_map.keys()):
                cols = schema_map[table]
                col_str = ", ".join(cols)
                
                parts = [f"Table: {table}", f"  Columns: {col_str}"]
                
                if table in fk_map:
                    parts.append("  Foreign Keys:")
                    parts.extend([f"    - {x}" for x in fk_map[table]])
                
                if table in idx_map:
                    parts.append("  Indexes:")
                    for idx_desc, idx_cols in idx_map[table].items():
                        parts.append(f"    - {idx_desc}: {', '.join(idx_cols)}")
                        
                if table in ep_map:
                    parts.append("  Extended Properties:")
                    parts.extend([f"    - {x}" for x in ep_map[table]])

                output_lines.append("\n".join(parts))

            result = "\n\n".join(output_lines)

            if fingerprint:
                try:
                    os.makedirs(CACHE_DIR, exist_ok=True)
                    with open(self._cache_path(fingerprint), "w", encoding="utf-8") as f:
                        f.write(result)
                except Exception:
                    pass  # cache write failure is non-fatal

            return result

        except Exception as e:
            return f"Error getting schema: {str(e)}"
            
    def get_databases(self):
        """Fetch list of available databases, excluding system ones."""
        if not self.conn:
            return []
            
        try:
            cursor = self.conn.cursor()
            query = "SELECT name FROM sys.databases WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb') ORDER BY name"
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]
        except:
            return []
            
    def execute_query(self, query, timeout_seconds=20, batch_size=5000):
        """
        Execute a SELECT query and return a DataFrame.
        Uses cursor.execute + fetchmany so column metadata is preserved on
        empty result sets, and a watchdog timer cancels the cursor on overrun.
        """
        if not self.conn:
            return None, "No connection"

        self.conn.timeout = timeout_seconds

        cursor = self.conn.cursor()
        timed_out = {"flag": False}

        def _cancel():
            timed_out["flag"] = True
            try:
                cursor.cancel()
            except Exception:
                pass

        watchdog = threading.Timer(timeout_seconds, _cancel)
        watchdog.daemon = True
        watchdog.start()

        try:
            cursor.execute(query)

            if cursor.description is None:
                # Non-result-producing statement; return empty frame
                return pd.DataFrame(), None

            columns = [col[0] for col in cursor.description]
            rows = []
            start = time.monotonic()

            while True:
                batch = cursor.fetchmany(batch_size)
                if not batch:
                    break
                rows.extend(tuple(r) for r in batch)

                if time.monotonic() - start > timeout_seconds:
                    _cancel()
                    return None, (
                        f"Query fetch timed out after {timeout_seconds} seconds "
                        f"(fetched {len(rows)} rows)."
                    )

            df = pd.DataFrame.from_records(rows, columns=columns)

            # Deduplicate columns to please Streamlit/PyArrow
            if not df.columns.is_unique:
                new_columns = []
                seen_columns = {}
                for col in df.columns:
                    if col in seen_columns:
                        seen_columns[col] += 1
                        new_columns.append(f"{col}.{seen_columns[col]}")
                    else:
                        seen_columns[col] = 0
                        new_columns.append(col)
                df.columns = new_columns

            # pyodbc returns datetimes/Decimals as Python objects; let pandas
            # promote object columns where possible.
            df = df.infer_objects()

            df.index = df.index + 1
            return df, None

        except pyodbc.OperationalError as e:
            if timed_out["flag"] or 'Query timeout expired' in str(e):
                return None, f"Query execution timed out after {timeout_seconds} seconds."
            return None, str(e)
        except pyodbc.Error as e:
            if timed_out["flag"]:
                return None, f"Query execution timed out after {timeout_seconds} seconds."
            return None, str(e)
        except Exception as e:
            return None, str(e)
        finally:
            watchdog.cancel()
            try:
                cursor.close()
            except Exception:
                pass

    def close(self):
        if self.conn:
            self.conn.close()
