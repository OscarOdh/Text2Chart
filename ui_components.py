import streamlit as st
import streamlit.components.v1 as components
import os
import json
import uuid
import time
from datetime import datetime
from config_manager import save_config

def handle_menu_click(msg_id, target_key, target_value):
    """
    Callback to handle menu actions.
    Sets a flag to force the menu to be replaced (closed) on the next run.
    """
    st.session_state[f"force_close_menu_{msg_id}"] = True
    # Set the actual action to be processed
    st.session_state[target_key] = target_value

def display_dataframe(df):
    """
    Display a dataframe with enhanced formatting.
    - Auto-detects 'address' columns and makes them clickable Google Maps links.
    """
    
    # Check for address columns
    address_cols = [col for col in df.columns if 'address' in col.lower()]
    
    display_df = df.copy()
    
    # Safety Net: Deduplicate columns if they exist
    if not display_df.columns.is_unique:
        new_columns = []
        seen_columns = {}
        for col in display_df.columns:
            if col in seen_columns:
                seen_columns[col] += 1
                new_columns.append(f"{col}.{seen_columns[col]}")
            else:
                seen_columns[col] = 0
                new_columns.append(col)
        display_df.columns = new_columns
        
    if address_cols:
        for col in address_cols:
            display_df[col] = "https://www.google.com/maps/search/?api=1&query=" + display_df[col].astype(str)
            
    col_config = {}
    
    for col in address_cols:
        col_config[col] = st.column_config.LinkColumn(
            col,
            display_text=r"query=(.*)"
        )

    # Detect currency and percentage columns dynamically
    import pandas as pd
    currency_keywords = ['amount', 'paid', 'balance', 'cost', 'price', 'payment', 'revenue']
    pct_keywords = ['pct', 'percent', 'rate']
    
    format_dict = {}
    
    for col in display_df.columns:
        col_lower = col.lower()
        is_money = any(kw in col_lower for kw in currency_keywords)
        is_pct = any(kw in col_lower for kw in pct_keywords)
        
        # PyODBC returns Decimals as Python objects which pandas maps to 'object' dtype instead of numeric.
        # We must try coercing them to numeric before testing their dtype
        if is_money or is_pct:
            try:
                # Convert Decimals/strings to float automatically, ignoring errors to keep original data if it fails
                display_df[col] = pd.to_numeric(display_df[col], errors='ignore')
            except:
                pass

        if pd.api.types.is_numeric_dtype(display_df[col]):
            if is_money:
                format_dict[col] = "${:,.2f}"
            elif is_pct:
                format_dict[col] = "{:,.2%}"
                
    styled_df = display_df
    if format_dict:
        styled_df = display_df.style.format(format_dict)
                
    if col_config:
        st.dataframe(styled_df, column_config=col_config)
    else:
        st.dataframe(styled_df)

def render_sidebar(config, init_connection_func):
    """Render the sidebar configuration and history."""
    with st.sidebar:
        if st.session_state.connected:
            st.markdown(f"### 🗃️ {config['SQL']['database']}")
            st.divider()

        # Use if/else to force a new component instance (resetting state) as 'key' is not supported
        suffix = "\u200b" * st.session_state.get('connection_count', 0)
        
        if not st.session_state.connected:
            config_expander = st.expander(f"Configuration{suffix}", expanded=True)
        else:
            config_expander = st.expander(f"Configuration{suffix}", expanded=False)

        with config_expander:
            st.subheader("SQL Connection")
            server = st.text_input("Server", value=config['SQL']['server'])
            port = st.text_input("Port", value=config['SQL']['port'])
            # Database Selection
            db_options = []
            if st.session_state.connected and st.session_state.db_manager:
                db_options = st.session_state.db_manager.get_databases()
            
            if db_options:
                 # Find index if possible
                 try:
                     db_index = db_options.index(config['SQL']['database'])
                 except ValueError:
                     db_index = 0
                 database = st.selectbox("Database", options=db_options, index=db_index)
            else:
                 database = st.text_input("Database", value=config['SQL']['database'])
            username = st.text_input("Username", value=config['SQL']['username'])
            password = st.text_input("Password", value=config['SQL']['password'], type="password")
            
            st.subheader("AI Connection")
            base_url = st.text_input("Base URL", value=config['AI']['base_url'])
            model = st.text_input("Model ID", value=config['AI']['model'])
            
            if st.button("Connect & Save Config"):
                # Update Config object
                config['SQL']['server'] = server
                config['SQL']['port'] = port
                config['SQL']['database'] = database
                config['SQL']['username'] = username
                config['SQL']['password'] = password
                config['AI']['base_url'] = base_url
                config['AI']['model'] = model
                
                save_config(config)
                
                if init_connection_func(config):
                    st.session_state.connection_count = st.session_state.get('connection_count', 0) + 1
                    st.success("Configuration Saved & Connected!")
                    time.sleep(1) # Rerun trigger
                    st.rerun()

        with st.expander("Chat History", expanded=st.session_state.connected):
            # Display Persistent History
            st.caption("Saved History")
            
            history_items = []
            js_to_inject = None
            if os.path.exists("history.txt"):
                with open("history.txt", "r", encoding="utf-8") as f:
                    raw_lines = [line.strip() for line in f.readlines() if line.strip()]
                
                # Filter by current database
                current_view_db = config['SQL']['database'] 
                filtered_items = []
                
                for line in raw_lines:
                    if '|' in line:
                        parts = line.split('|', 1)
                        if len(parts) == 2:
                            db_name, query = parts
                            if db_name.strip() == current_view_db.strip():
                                filtered_items.append(query)
                    else:
                        filtered_items.append(line)

                # Deduplicate while preserving order
                seen = set()
                history_items = []
                for item in filtered_items:
                    if item not in seen:
                        history_items.append(item)
                        seen.add(item)
            
            # Reverse to show newest first
            history_items = history_items[::-1]
            
            if not history_items:
                 st.caption("No history yet.")
            else:
                 # Interactive History List (Streamlit Buttons)
                 js_to_inject = None
                 for idx, text in enumerate(history_items):
                     # Use a tight column layout: Tiny X column (minimal ratio), Fluid Text column
                     c1, c2 = st.columns([1, 100])
                     
                     with c1:
                         # X Button for Deletion
                         if st.button("✕", key=f"hist_del_{idx}"):
                             try:
                                if os.path.exists("history.txt"):
                                    with open("history.txt", "r", encoding="utf-8") as f:
                                        lines = f.readlines()
                                    
                                    # Logic to remove the specific line
                                    current_db = config['SQL']['database'].strip()
                                    # We need to be careful to delete the *correct* instance if duplicates exist
                                    # But since we display deduplicated, we'll delete all matching queries for this DB
                                    target_line_modern = f"{current_db}|{text}"
                                    
                                    new_lines = []
                                    deleted = False
                                    for line in lines:
                                        stripped = line.strip()
                                        if stripped == text or stripped == target_line_modern:
                                            # Only delete if it matches
                                            continue
                                        new_lines.append(line)
                                        
                                    with open("history.txt", "w", encoding="utf-8") as f:
                                        f.writelines(new_lines)
                                st.rerun()
                             except Exception as e:
                                 st.error(f"Error: {e}")

                     with c2:
                         # Text Button for Populating Input
                         # We use a button to make it clickable
                         if st.button(text, key=f"hist_btn_{idx}", help=text, use_container_width=True):
                             js_to_inject = text



            # Clear History Link (Immediately after list)
            if st.button("Clear History", key="clear_history"):
                try:
                    with open("history.txt", "w", encoding="utf-8") as f:
                        pass # Truncate file
                except Exception as e:
                    st.error(f"Failed to clear history: {e}")
                st.rerun()

            # Clear Chat Link (Bottom)
            if st.button("Clear Current Chat", key="clear_chat"):
                st.session_state.messages = []
                st.rerun()



        # Status Check (if already connected in session)
        if st.session_state.connected:
             with st.expander(f"Schema Loaded: {len(st.session_state.schema_context)} chars"):
                 st.caption("Schema Context Used for AI")
                 if st.button("Refresh Schema", key="refresh_schema"):
                     with st.spinner("Rebuilding schema..."):
                         st.session_state.schema_context = st.session_state.db_manager.get_schema(force_refresh=True)
                     st.rerun()
                 st.code(st.session_state.schema_context)
    
    return js_to_inject

def render_chart_editor(df, config, msg_id, edit_key):
    """Render the chart editor UI."""
    with st.container(border=True):
         st.markdown("### ✏️ Edit Chart")
         
         all_cols = df.columns.tolist()
         
         # Heuristics for defaults
         str_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
         num_cols = df.select_dtypes(include=['number']).columns.tolist()
         
         default_x_val = str_cols[0] if len(str_cols) > 0 else (all_cols[0] if all_cols else None)
         default_y_val = num_cols[0] if len(num_cols) > 0 else (all_cols[1] if len(all_cols) > 1 else (all_cols[0] if all_cols else None))
         
         current_x_col = config.get("x_col") if config.get("x_col") in all_cols else default_x_val
         current_y_col = config.get("y_col") if config.get("y_col") in all_cols else default_y_val

         try:
             x_idx = all_cols.index(current_x_col) if current_x_col in all_cols else 0
         except:
             x_idx = 0
         
         try:
             y_idx = all_cols.index(current_y_col) if current_y_col in all_cols else 0
         except:
             y_idx = 0

         new_title = st.text_input("Title", value=config.get("title", ""), key=f"title_{msg_id}")
         
         c1, c2 = st.columns(2)
         with c1:
             new_x_col = st.selectbox("X Axis Data", options=all_cols, index=x_idx, key=f"xcol_{msg_id}")
             new_x = st.text_input("X Label", value=config.get("x_label", ""), key=f"x_{msg_id}")
         with c2:
             new_y_col = st.selectbox("Y Axis Data", options=all_cols, index=y_idx, key=f"ycol_{msg_id}")
             new_y = st.text_input("Y Label", value=config.get("y_label", ""), key=f"y_{msg_id}")
         
         # Reordering Logic
         str_cols = df.select_dtypes(include=['object', 'string']).columns
         new_order = None
         if len(str_cols) > 0:
             cat_col = str_cols[0]
             unique_vals = df[cat_col].unique().tolist()
             current_order = config.get("order", unique_vals)
             # Validate/fix order list
             current_order = [str(x) for x in current_order if x in unique_vals] # Ensure strings
             missing = [str(x) for x in unique_vals if x not in current_order]
             current_order.extend(missing)
             
             # Use text area for reordering
             st.caption("Reorder Items (Edit the list below)")
             order_text = st.text_area("Order", value=", ".join(current_order), height=68, key=f"order_{msg_id}", label_visibility="collapsed")
             
             # Parse back to list
             if order_text:
                  new_order = [x.strip() for x in order_text.split(',') if x.strip()]
         
         btn_spacer, btn_c1, btn_c2 = st.columns([6, 1, 1.2]) # Push to right
         with btn_c1:
              if st.button("Cancel", key=f"cancel_{msg_id}"):
                  st.session_state[edit_key] = False
                  st.rerun()
         with btn_c2:
             if st.button("Save Changes", key=f"save_{msg_id}", type="primary"):
                 return {
                     "title": new_title,
                     "x_label": new_x,
                     "y_label": new_y,
                     "x_col": new_x_col,
                     "y_col": new_y_col,
                     "order": new_order
                 }
    return None

_AUTOCOMPLETE_INSTALLER_JS = r"""
(function() {
    if (window.__t2c_autocomplete_installed) return;
    window.__t2c_autocomplete_installed = true;

    const doc = document;
    let activeInput = null;
    let suggestionBox = null;
    let currentMatches = [];
    let selectedIndex = -1;

    function ensureSuggestionBox() {
        let existing = doc.getElementById('smart-autocomplete-list');
        if (existing) { suggestionBox = existing; return existing; }
        const box = doc.createElement('div');
        box.id = 'smart-autocomplete-list';
        Object.assign(box.style, {
            position: 'fixed', display: 'none',
            backgroundColor: 'rgba(28, 30, 38, 0.9)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            zIndex: '2147483647', maxHeight: '200px', overflowY: 'auto',
            boxShadow: '0 4px 30px rgba(0, 0, 0, 0.5)', color: '#f0f2f6',
            fontFamily: '"Source Sans Pro", sans-serif', fontSize: '13px',
            boxSizing: 'border-box'
        });
        doc.body.appendChild(box);
        suggestionBox = box;
        return box;
    }

    function closeSuggestions() {
        if (suggestionBox) {
            suggestionBox.style.display = 'none';
            selectedIndex = -1;
        }
    }

    function updatePosition() {
        if (!activeInput || !suggestionBox || suggestionBox.style.display === 'none') return;
        const rect = activeInput.getBoundingClientRect();
        if (rect.width === 0) return;
        const viewportHeight = window.innerHeight;
        Object.assign(suggestionBox.style, {
            width: 'auto', minWidth: '200px',
            maxWidth: rect.width + 'px',
            left: rect.left + 'px',
            bottom: (viewportHeight - rect.top + 6) + 'px',
            top: 'auto'
        });
    }

    function selectSuggestion(text) {
        if (!activeInput) return;
        const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
        valueSetter.call(activeInput, text);
        activeInput.dispatchEvent(new Event('input', { bubbles: true }));
        closeSuggestions();
        setTimeout(() => activeInput.focus(), 50);
    }

    function updateSelection() {
        if (!suggestionBox) return;
        const items = suggestionBox.children;
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (i === selectedIndex) {
                item.style.backgroundColor = 'rgba(255, 255, 255, 0.2)';
                item.scrollIntoView({ block: 'nearest' });
            } else {
                item.style.backgroundColor = 'transparent';
            }
        }
    }

    function handleInput(target) {
        const box = ensureSuggestionBox();
        activeInput = target;
        const history = window.__t2c_history || [];
        const val = target.value.toLowerCase().trim();
        if (!val) {
            currentMatches = history.slice(-3);
        } else {
            currentMatches = history.filter(item => item.toLowerCase().includes(val)).slice(-5);
        }
        selectedIndex = -1;
        box.innerHTML = '';
        if (currentMatches.length > 0) {
            currentMatches.forEach((match, idx) => {
                const div = doc.createElement('div');
                div.textContent = match;
                Object.assign(div.style, {
                    padding: '6px 12px', cursor: 'pointer',
                    borderBottom: '1px solid rgba(128, 128, 128, 0.1)',
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    transition: 'background-color 0.1s'
                });
                div.onmouseenter = () => {
                    if (selectedIndex === -1) div.style.backgroundColor = 'rgba(255, 255, 255, 0.1)';
                };
                div.onmouseleave = () => {
                    if (selectedIndex !== idx) div.style.backgroundColor = 'transparent';
                };
                div.onmousedown = (ev) => { ev.preventDefault(); selectSuggestion(match); };
                box.appendChild(div);
            });
            box.style.display = 'block';
            updatePosition();
            updateSelection();
        } else {
            closeSuggestions();
        }
    }

    function isChatInput(target) {
        return target.tagName === 'TEXTAREA' &&
               (target.dataset.testid === 'stChatInputTextArea' ||
                (target.placeholder && target.placeholder.toLowerCase().includes('ask')));
    }

    doc.addEventListener('focusin', (e) => { if (isChatInput(e.target)) handleInput(e.target); });
    doc.addEventListener('input',   (e) => { if (isChatInput(e.target)) handleInput(e.target); });
    doc.addEventListener('click',   (e) => { if (isChatInput(e.target)) handleInput(e.target); });

    doc.addEventListener('keydown', (e) => {
        if (!suggestionBox || suggestionBox.style.display === 'none') return;
        if (!activeInput || e.target !== activeInput) return;
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            if (selectedIndex === -1) selectedIndex = currentMatches.length - 1;
            else { selectedIndex--; if (selectedIndex < 0) selectedIndex = -1; }
            updateSelection();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            if (selectedIndex === -1) selectedIndex = 0;
            else { selectedIndex++; if (selectedIndex >= currentMatches.length) selectedIndex = -1; }
            updateSelection();
        } else if (e.key === 'Enter') {
            if (selectedIndex > -1) {
                e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
                selectSuggestion(currentMatches[selectedIndex]);
            } else {
                closeSuggestions();
            }
        }
    }, true);

    doc.addEventListener('mousedown', (e) => {
        if (suggestionBox && suggestionBox.style.display !== 'none') {
            if (suggestionBox.contains(e.target)) return;
            if (activeInput && activeInput.contains(e.target)) return;
            closeSuggestions();
        }
    });

    doc.addEventListener('focusout', (e) => {
        if (isChatInput(e.target)) {
            const relatedTarget = e.relatedTarget;
            if (!suggestionBox || !suggestionBox.contains(relatedTarget)) closeSuggestions();
        }
    });

    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);

    setInterval(() => {
        if (suggestionBox && suggestionBox.style.display !== 'none') {
            if (!activeInput || !doc.body.contains(activeInput)) {
                closeSuggestions();
                activeInput = null;
            }
        }
    }, 250);
})();
"""

def render_autocomplete(user_history):
    """Injects JS for autocomplete/history suggestions.

    The installer script is appended to the parent document's <head>, so its
    closures and setInterval live in the parent window's JS context and
    survive Streamlit rerun teardown of the components.html iframe.
    Listeners install exactly once; subsequent calls only refresh the mutable
    history array on window.
    """
    user_history = user_history[:20]
    js_history_array = json.dumps(user_history)
    installer_js_literal = json.dumps(_AUTOCOMPLETE_INSTALLER_JS)

    components.html(f"""
    <script>
    (function() {{
        const parentWin = window.parent;
        const pdoc = parentWin.document;

        // Refresh mutable history (read by installed listeners each fire).
        parentWin.__t2c_history = {js_history_array}.slice().reverse();

        // Hide any lingering popup from previous renders.
        const zombieBox = pdoc.getElementById('smart-autocomplete-list');
        if (zombieBox) zombieBox.style.display = 'none';

        if (parentWin.__t2c_autocomplete_installed) return;

        // Inject installer into the parent document so its closures live
        // in the parent context and outlive this iframe.
        const s = pdoc.createElement('script');
        s.textContent = {installer_js_literal};
        pdoc.head.appendChild(s);
    }})();
    </script>
    """, height=0)


