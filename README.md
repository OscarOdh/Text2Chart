# Text2Chart

**Ask your database a question in plain English. Get a table or a chart back.**

```
"show me the 10 customers with the highest loan balance"
        ↓
   local AI writes the SQL
        ↓
   SQL Server runs it
        ↓
   table + one-click bar/line/pie chart
```

![Text2Chart in use: the sidebar shows the connected database, saved question
history and the size of the extracted schema. In the main panel a plain-English
question returns a table of remaining balance by loan type, and one click turns
that same result into a bar chart.](docs/Text2Chart.png)

---

## What problem does this solve?

Databases hold the answers, but getting them out requires SQL, and SQL is a real
programming language. So in most teams there's a bottleneck: the people who have
the questions can't write the queries, and the people who can write the queries
are busy.

Text2Chart removes that step. You type a question the way you'd say it out loud,
a language model translates it into a real SQL query, the query runs against your
database, and you get the result as a formatted table. One click turns that table
into an interactive chart.

Two things make it different from pasting your question into ChatGPT.

1. **It knows your database.** Before you ask anything, the app reads your
   schema (every table, column, data type, foreign key, index, and description)
   and hands that to the model as context. So it writes queries against *your*
   actual table names, not invented ones.
2. **Nothing leaves your machine.** It talks to a local model server: LM Studio,
   Ollama, or anything speaking the OpenAI API format. Your schema and your
   questions never go to a cloud provider. That's the whole reason it exists in
   this shape, because it means you can point it at a production database without
   a data-exfiltration conversation.

---

## Features

**Plain-English to real T-SQL.** Type a question, get a syntactically valid
Microsoft SQL Server query. The generated SQL is always shown in a collapsible
"View code" panel, so you can read it, learn from it, or paste it into SSMS.

**Schema-aware, not schema-guessing.** The app extracts far more than table
names. It pulls foreign-key relationships so the model knows how tables join,
indexes and primary keys so it knows what's unique, and SQL Server *extended
properties*, the description text a DBA attaches to columns. That last one means
a column called `st` can be understood as "state" without anyone explaining it in
the prompt.

**Schema caching that actually invalidates.** Reading a big schema is slow, so
it's cached to disk. The cache key is a checksum of every object's modification
date plus every extended-property value, so the moment someone alters a table or
edits a column description, the cache busts itself. No stale-context bugs, no
manual "refresh" ritual, though there's a Refresh Schema button if you want one.

**Charts without a chart builder.** Any result table gets a `⋮` menu with Bar,
Line, and Pie. The app inspects your columns and picks sensible axes: first text
column for categories, first numeric column for values. Wrong guess? The chart
editor lets you override the title, both axes, the axis labels, and even
hand-reorder the categories.

**A table that formats itself.** Columns named like money (`amount`, `balance`,
`paid`, `price`, `payment`, `cost`, `revenue`) render as `$1,234.56`. Columns
named like rates (`pct`, `percent`, `rate`) render as percentages. Columns named
`address` become clickable Google Maps links. All of it inferred from the column
name, with no configuration.

**Autocomplete on your own history.** Every question you ask is saved, tagged
with the database it was asked against. Start typing and you get a floating
suggestion list of your past questions, filtered to the current database,
navigable with the arrow keys. Streamlit has no such widget, so this one is
hand-built in JavaScript and injected into the page.

**Built to not hurt the database.** Every generated query is forced to
`SELECT TOP 1000` by default. Connections carry a 20-second timeout, results are
fetched in 5,000-row batches, and a watchdog timer cancels the cursor if a fetch
overruns. A careless question can't turn into a table scan that takes down the
server.

**Live latency readout.** While the model is thinking, a JavaScript timer counts
up in hundredths of a second, without triggering a Python re-run. Every answer is
permanently stamped with how long it took.

**Conversational follow-ups.** The last few turns are fed back to the model, so
"now group that by month" works as a follow-up instead of needing the whole
question restated.

---

## Requirements

| What | Why |
|---|---|
| Python 3.10+ | The app |
| Microsoft SQL Server | The database it queries |
| [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) | How Python talks to SQL Server. Not optional, since the driver name is hardcoded. |
| A local OpenAI-compatible model server | [LM Studio](https://lmstudio.ai/) is what this was built against. Ollama or vLLM work too. Any model server exposing `/v1/chat/completions`. |

A code-capable model is strongly recommended. A general chat model will produce
SQL, but it will produce *wrong* SQL more often.

---

## Setup

```bash
git clone https://github.com/OscarOdh/Text2Chart.git
cd Text2Chart
pip install -r requirements.txt
```

Start your model server and load a model. In LM Studio that's the "Local Server"
tab, then Start Server. Note the port (LM Studio defaults to `1234`).

Then run:

```bash
python -m streamlit run app.py
```

Or just double-click `open.cmd`, which does exactly that.

Streamlit opens `http://localhost:8501` in your browser. Fill in the sidebar's
**Configuration** panel with the server, port, database, username, password, plus
the model server's base URL and model ID, then hit **Connect & Save Config**.

Your answers overwrite the `YYYY` placeholders in `settings.ini`, and from then
on the app auto-connects on startup and drops you straight into the chat. That
file stores the password in plaintext, so keep your filled-in copy out of version
control.

### Make the AI better at your schema (optional, high payoff)

The single cheapest way to improve the SQL you get back is to **describe your
columns in the database itself**, using SQL Server's extended properties. The app
reads them and feeds them to the model as context, so the model stops guessing at
what your column names mean.

This matters most for the names that are obvious to you and opaque to everyone
else. A column called `st` could be state, status, street, or start. A flag
called `active_fl` could mean anything. Tell the database once:

```sql
-- Describe a column
EXEC sp_addextendedproperty
    @name       = N'MS_Description',
    @value      = N'Two-letter US state code, e.g. TX',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'Customers',
    @level2type = N'COLUMN', @level2name = N'st';

-- Describe a whole table (drop the @level2 lines)
EXEC sp_addextendedproperty
    @name       = N'MS_Description',
    @value      = N'One row per customer. Inactive customers are kept, not deleted.',
    @level0type = N'SCHEMA', @level0name = N'dbo',
    @level1type = N'TABLE',  @level1name = N'Customers';
```

Use `sp_updateextendedproperty` to change one and `sp_dropextendedproperty` to
remove it. If you'd rather click than type, SSMS exposes the same field as the
**Description** box in the table designer's column properties.

A description is worth writing whenever a name is an abbreviation, a code with a
fixed set of values, a flag whose meaning isn't obvious, or a date that could
mean several things (created, modified, effective). Business rules help too:
"amounts are stored in cents" or "soft-deleted rows have `deleted_at` set" are
exactly the kind of thing a model cannot infer from a schema dump.

Descriptions are part of the cache fingerprint, so editing one invalidates the
cached schema automatically and the next question picks it up. No restart needed.

### Want a database to try it against?

`bank_schema_and_data.sql` is a self-contained script that builds a `BankDB` with
customers, accounts, loans, amortization schedules, and payment history: about
100 customers of entirely **mock** data, with credit scores drawn from a rough
normal distribution and simulated delinquency. Run it in SSMS, point the app at
`BankDB`, and you have something real to ask questions about.

---

## How it works, file by file

The app is seven Python files. Streamlit re-runs the entire script top-to-bottom
on every interaction, which is the single most important thing to understand
about this codebase. There is no persistent program state except what's stored in
`st.session_state`, and any "did the user click that?" logic has to survive a
full script restart.

### `app.py`, the controller

The file Streamlit actually runs. It does five jobs.

**Session setup.** On the very first run it creates the state that has to survive
re-runs: the chat `messages` list, the `db_manager` and `ai_manager` objects, the
extracted `schema_context` string, and a `connected` flag.

**Auto-connect.** If `settings.ini` exists, it connects on startup without
asking, guarded by an `auto_connect_attempted` flag so a failed connection doesn't
retry forever on every re-run.

**The chat loop.** It walks the message list and renders each one based on a
`type` field: `dataframe`, `chart`, `error`, or plain text. User messages get
right-aligned bubbles built from raw HTML; assistant messages go in Streamlit's
native chat container. Each message carries a UUID, which is how per-message
widget keys stay stable across re-runs.

**The `⋮` action menu.** Each message gets a popover with actions like "turn this
table into a chart", "edit this chart", "delete this message". Here's the re-run
problem in miniature: a button inside a popover can't directly do the work,
because the script will restart before the work finishes. So the button's callback
just writes a *pending action* into session state (`pending_chart_action`,
`pending_edit_action`, `pending_delete_action`). After the chat loop finishes,
`app.py` checks for those keys, performs the action, and calls `st.rerun()`.

There's a second wrinkle. Streamlit popovers don't close when you click something
inside them, so the menu stays stuck open. The fix is a flag called
`trigger_js_close` that injects a zero-height HTML component whose script
dispatches a synthetic `mousedown` on the parent document's body, fooling the
popover into thinking you clicked elsewhere.

**The question pipeline.** When you submit a question, `app.py`:

1. Appends it to the message list and immediately renders it, so the UI feels
   responsive before the slow part starts.
2. Saves it to `history.txt` as `DatabaseName|your question`, skipping exact
   duplicates.
3. Injects a JavaScript timer that updates every 50ms. This is JavaScript
   specifically *because* a Python timer would need re-runs to update, and each
   re-run would restart the whole script.
4. Sends the schema, the last few turns, and the question to `ai_manager`.
5. Runs the returned SQL through `db_manager`.
6. Appends the result (DataFrame, chart, or error) with a duration stamp.

### `ai_manager.py`, talking to the model

A thin wrapper over the OpenAI Python client, pointed at your local server. The
API key is a dummy string, because local servers don't check it.

The interesting part is the **system prompt**, which is a list of hard rules
rather than a friendly description. It pins the model to T-SQL syntax with
bracketed identifiers (`[Table].[Column]`, so a column named `Order` doesn't
collide with the SQL keyword). It forbids DDL and DML: no `DROP`, `DELETE`,
`UPDATE`, `INSERT`, `ALTER`, `EXEC`. It mandates `SELECT TOP 1000`. It requires
`TRY_CAST` over `CAST` so bad data returns `NULL` instead of failing the whole
query. It requires `CONCAT()` instead of `+` for strings, because `+` silently
does arithmetic when SQL Server thinks the operands are numbers. And it enforces
the rule that every non-aggregated `SELECT` column must appear in `GROUP BY`,
which is the single most common way LLM-written SQL fails to compile.

There's also a prompt-injection rule. If asked to reveal its instructions or
change persona, the model must answer with `SELECT 'Please view code'` plus a SQL
comment explaining the refusal. Since every response is executed as SQL, the
refusal has to *be* valid SQL.

**Domain-specific injectors** append extra rules based on which database you're
connected to. For `BankDB`, the model is told exactly how to join the loan
payments table to the amortization schedule, and never to return money as a
formatted string, because the table renderer in `ui_components.py` needs raw
numbers to format them itself. For `OpenDB`, it's told how to wrap restaurant
names in `LIKE` wildcards. This is the honest, unglamorous way to get reliable
output from a small local model: when it keeps making the same mistake, write the
rule down.

Only the last 6 messages of history go to the model, to keep token cost bounded,
and error messages are filtered out so a failed attempt doesn't teach it bad
patterns. Temperature is `0.1`, because code generation wants determinism, not
creativity.

`_sanitize_sql()` strips markdown code fences, because models wrap code in
```` ``` ```` no matter how firmly you ask them not to.

### `db_manager.py`, the database layer

Wraps `pyodbc`. Three parts worth understanding.

**`get_schema()`, building the model's context.** Four separate queries against
SQL Server's system catalogs, assembled into one dense text block:

1. Tables and columns with data types, from `INFORMATION_SCHEMA`, filtering out
   system tables.
2. Foreign keys, from `sys.foreign_keys`. This is what lets the model write
   correct `JOIN`s instead of guessing.
3. Indexes, from `sys.indexes`, tagged `PK` and `UNIQUE` where applicable.
4. Extended properties, from `sys.extended_properties`, the human-written
   descriptions attached to tables and columns. Free semantic hints, if your DBA
   filled them in.

The output is formatted for token efficiency rather than human readability, since
its only reader is a language model with a limited context window.

**The cache.** `_schema_fingerprint()` asks SQL Server for two checksums:
`CHECKSUM_AGG` over every non-system object's `modify_date`, and the same over
every extended-property value. Those, plus the server and database name, get
SHA-256'd into a 32-character key, and the built schema text is written to
`.cache/schema_<key>.txt`. Next startup, the same fingerprint means a disk read
instead of four catalog queries. Change a table or a description and the
fingerprint changes, so the cache invalidates itself. A cache write failure is
swallowed on purpose, since a broken cache should slow the app down, not break
it.

**`execute_query()`, running SQL without hanging.** Defense in depth, three
layers:

- The connection's own `timeout` property is set to 20 seconds, which SQL Server
  enforces server-side.
- A Python `threading.Timer` watchdog fires at 20 seconds and calls
  `cursor.cancel()`. This catches the case where the query itself is fast but
  returning the rows is slow.
- Rows are pulled with `cursor.fetchmany(5000)` in a loop rather than all at
  once, with an elapsed-time check on each batch.

It uses `cursor.execute` + `fetchmany` rather than `pandas.read_sql` for a
specific reason: `read_sql` loses column metadata when a query returns zero rows,
so an empty result would render as a blank nothing instead of an empty table with
proper headers.

Two post-processing touches. Duplicate column names get suffixed (`Name`,
`Name.1`), because the Arrow serializer Streamlit uses crashes on duplicates. And
the DataFrame index is shifted to start at 1, because the first row being "row 0"
confuses everyone who isn't a programmer.

### `ui_components.py`, the hard frontend parts

This is where Streamlit's limits get worked around.

**`display_dataframe()`, the self-formatting table.** For each column it checks
the *name* against keyword lists. Money keywords get `${:,.2f}`, rate keywords
get `{:,.2%}`, and anything containing `address` gets rewritten into a Google
Maps search URL and rendered as a `LinkColumn`. Before formatting, it coerces
with `pd.to_numeric`, because ODBC hands back SQL `DECIMAL` values as Python
`Decimal` objects, which pandas stores as generic objects and refuses to format
as numbers.

**`render_autocomplete()`, the part with the real engineering in it.** Streamlit
has no autocomplete for its chat input, so this builds one:

- A vanilla-JS installer attaches `focusin` / `input` / `keydown` listeners to
  the chat textarea, identified by its `data-testid` attribute.
- Matches are rendered into a floating `<div>` positioned with
  `getBoundingClientRect()` so it sits directly above the input box.
- Arrow keys move the selection; Enter accepts it.
- Writing the chosen text back into the box can't be a simple
  `input.value = text` assignment. The textarea is controlled by React, which
  tracks its own idea of the value and would overwrite yours. The workaround
  reaches for the native property setter via `Object.getOwnPropertyDescriptor`
  and calls it directly, then dispatches a synthetic `input` event so React
  notices.
- The installer is appended to the **parent document's `<head>`**, not left
  inside the component's iframe. Streamlit destroys and recreates component
  iframes on every re-run, which would take the listeners with them. Living in
  the parent document, they install exactly once, guarded by a
  `window.__t2c_autocomplete_installed` flag, and later calls only refresh the
  history array on `window`.

**`render_sidebar()`** handles connection config, the saved-history list (one row
per question, with an `✕` delete button), Clear History, Clear Current Chat, and
a schema inspector showing the exact context string sent to the model plus its
character count. Filtering history by the current database means switching
databases gives you a clean, relevant list.

**`render_chart_editor()`** is the chart override UI: title, X/Y data columns,
axis labels, and a text area holding the category order as a comma-separated
list. It validates that list against the actual data on every render, dropping
values that no longer exist and appending ones that appeared, so an edited chart
can't be left pointing at columns that aren't there.

### `chart_utils.py`, DataFrame to Plotly

Small and heuristic. If you didn't specify axes, it picks the first text column
for X and the first numeric column for Y. It supports bar, line, and pie.

The one subtle piece is reordering. When you supply a category order, it first
checks how much of your list actually appears in the data. If nothing overlaps,
which happens when you switch the X axis to a numeric column while the saved
order is still for the old text column, it skips reordering entirely rather than
producing a table full of `NaN`. Otherwise it does the standard
`set_index → reindex → reset_index` dance to force the row order Plotly will
draw.

### `config_manager.py`, settings

`configparser` over `settings.ini`, with two sections (`SQL` and `AI`) and a
default for every key. Load it on a machine with no config file and you get
`localhost:1433` and `http://localhost:1234/v1/`, sensible enough that a first
run isn't a blank form.

### `style_manager.py`, the CSS

One large injected stylesheet. Dark theme, chat-bubble styling, compressed button
padding, the hidden Streamlit "Deploy" header. A lot of it targets Streamlit's
internal DOM directly (`[data-testid="column"]`, `.st-key-<widget_key>`) to get
the tight sidebar history layout the Python API won't produce. That's a known
trade-off: it's pixel-accurate today and it's the first thing that will break on
a Streamlit upgrade.

### Supporting files

| File | What it is |
|---|---|
| `settings.ini` | Your saved connection settings. Ships with `YYYY` placeholders. **Stores your database password in plaintext**, so don't commit your filled-in copy. |
| `history.txt` | Question history, one per line, `DatabaseName\|question`. Feeds autocomplete and the sidebar list. |
| `.cache/` | Cached schema text, keyed by schema fingerprint. Safe to delete; it rebuilds. |
| `bank_schema_and_data.sql` | Mock `BankDB` for testing. Around 100 fake customers with loans and payment history. |
| `help.html` | Standalone HTML version of the original architecture document. |
| `open.cmd` | One-line launcher: `python -m streamlit run app.py`. |

---

## Security, read this before pointing it at anything real

**The read-only guarantee is a prompt, not a lock.** The system prompt forbids
`DROP`, `DELETE`, `UPDATE` and friends, and in practice the model obeys. But
`execute_query()` will run whatever SQL it is handed. There is no allowlist, no
statement parser, no `SELECT`-only check in the Python. If a jailbreak or a plain
model mistake produces a destructive statement, it executes.

**So the actual protection is the database account.** Connect with a SQL Server
login that has `SELECT` and nothing else. Then the guarantee is enforced by SQL
Server, which cannot be talked out of it.

**Classic SQL injection is mostly sidestepped, prompt injection is not.** Your
input is never concatenated into a query string. The model sits in between as an
interpreter, so `'; DROP TABLE--` is just text it reads. But you can still *ask*
for a query that reads data you shouldn't see. There is no row-level or
column-level authorization layer here. Anything the connecting account can read,
a user of the app can read.

**Resource exhaustion is handled.** `SELECT TOP 1000`, a 20-second connection
timeout, a cancelling watchdog, and batched fetches. This is the part that is
properly defended.

---

## Known limits

- **SQL Server only.** The ODBC driver name is hardcoded and the prompt is
  T-SQL-specific. PostgreSQL or MySQL would need both changed.
- **Three chart types.** Bar, line, pie. No scatter, no stacked, no dual-axis.
- **`requirements.txt` is unpinned.** Every dependency is a bare name. A fresh
  install a year from now may not resolve to the versions this was built
  against, particularly Streamlit, given how much of the CSS and JS depends on
  its internal DOM.
- **The CSS and JS target Streamlit internals.** `data-testid` attributes and
  class names are not a public API. Expect the autocomplete and the sidebar
  layout to be the first casualties of a major Streamlit upgrade.
- **Chart config lives in session state.** Close the browser tab and your charts
  and conversation are gone. Only the question history persists to disk.
