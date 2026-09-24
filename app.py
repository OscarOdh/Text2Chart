import streamlit as st
import pandas as pd
from config_manager import load_config
from db_manager import DatabaseManager
from ai_manager import AIManager
import time
import os
import uuid
import streamlit.components.v1 as components
from datetime import datetime
from chart_utils import generate_chart
from style_manager import load_css
from ui_components import render_sidebar, display_dataframe, render_chart_editor, render_autocomplete, handle_menu_click

# Page Layout
st.set_page_config(page_title="Text2Chart", layout="wide", initial_sidebar_state="expanded")

# Load Styles
load_css()

# Session State Initialization
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = None
if 'ai_manager' not in st.session_state:
    st.session_state.ai_manager = None
if 'schema_context' not in st.session_state:
    st.session_state.schema_context = ""
if 'connected' not in st.session_state:
    st.session_state.connected = False

# JS Injection for Menu Closing (kept here as it interacts with the re-run cycle)
if st.session_state.get("trigger_js_close", False):
    components.html(f"""
    <script>
        const doc = window.parent.document;
        doc.body.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true }}));
        doc.body.click();
    </script>
    """, height=0, width=0)
    del st.session_state["trigger_js_close"]

def init_connection(config_data):
    """Initialize DB and AI connections."""
    st.session_state.ai_manager = AIManager(config_data['AI'])
    st.session_state.db_manager = DatabaseManager(config_data['SQL'])
    success, msg = st.session_state.db_manager.connect()
    
    if success:
        st.sidebar.markdown('<div class="status-box status-success">SQL Connected</div>', unsafe_allow_html=True)
        with st.spinner("Extracting Schema..."):
            st.session_state.schema_context = st.session_state.db_manager.get_schema()
        st.session_state.connected = True
        return True
    else:
        st.sidebar.markdown(f'<div class="status-box status-error">Connection Failed</div>', unsafe_allow_html=True)
        st.error(f"DB Connection Error: {msg}")
        return False

# --- SIDEBAR & CONFIG ---
# --- SIDEBAR & CONFIG ---
js_to_inject = render_sidebar(load_config(), init_connection)

if js_to_inject:
    import json
    # Inject JS to populate the input
    safe_text = json.dumps(js_to_inject)
    components.html(f"""
        <script>
            const doc = window.parent.document;
            const input = doc.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (input) {{
                const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                valueSetter.call(input, {safe_text});
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.focus();
            }}
        </script>
    """, height=0, width=0)

# Auto-Connect Logic
if 'auto_connect_attempted' not in st.session_state:
    st.session_state.auto_connect_attempted = False

if not st.session_state.connected and not st.session_state.auto_connect_attempted:
    if os.path.exists('settings.ini'):
        config = load_config()
        if init_connection(config):
            st.session_state.auto_connect_attempted = True
            st.rerun()
        else:
            st.session_state.auto_connect_attempted = True
    else:
        st.session_state.auto_connect_attempted = True

# --- MAIN CHAT ---
if not st.session_state.connected:
    st.info("Please configure connection in the sidebar to start.")
else:
    # Display Chat
    for i, message in enumerate(st.session_state.messages):
        if "id" not in message: message["id"] = str(uuid.uuid4())
        msg_id = message["id"]
        
        ts = message.get("timestamp", datetime.now())
        ts_str = ts.strftime("%I:%M:%S %p") if isinstance(ts, datetime) else ts

        if message["role"] == "user":
            st.markdown(f"""
            <div class='timestamp-label timestamp-right'>{ts_str}</div>
            <div class='user-msg-container'>
                <div class='user-msg-bubble'>{message['content']}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            duration_html = f"<span class='duration-label'>({message.get('duration', 0):.2f}s)</span>"
            st.markdown(f"<div class='timestamp-label'>{ts_str} {duration_html}</div>", unsafe_allow_html=True)
            
            with st.chat_message(message["role"]):
                content_col, action_col = st.columns([1, 0.05])
                
                with content_col:
                    if message.get("type") == "dataframe":
                        display_dataframe(message["content"])
                        if "sql" in message:
                            with st.expander("View code"):
                                st.code(message["sql"], language="sql")
                    
                    elif message.get("type") == "error":
                        st.error(message["content"])
                        if "sql" in message:
                            with st.expander("View code"):
                                st.code(message["sql"], language="sql")
                        
                    elif message.get("type") == "chart":
                        chart_config = message.get("chart_config", {})
                        edit_key = f"edit_mode_{msg_id}"
                        
                        if not st.session_state.get(edit_key, False):
                            fig = generate_chart(message["content"], 
                                                 message["chart_type"], 
                                                 title=chart_config.get("title"), 
                                                 x_label=chart_config.get("x_label"), 
                                                 y_label=chart_config.get("y_label"),
                                                 order_list=chart_config.get("order"),
                                                 x_col=chart_config.get("x_col"),
                                                 y_col=chart_config.get("y_col"))
                            if fig:
                                st.plotly_chart(fig, use_container_width=True, key=f"chart_{msg_id}", config={
                                    'displayModeBar': True,
                                    'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'resetScale2d'],
                                    'displaylogo': False
                                })
                            else:
                                st.error("Could not generate chart.")
                        else:
                            # Render Edit UI
                            new_config = render_chart_editor(message["content"], chart_config, msg_id, edit_key)
                            if new_config:
                                message["chart_config"] = new_config
                                st.session_state[edit_key] = False
                                st.rerun()
                    else:
                        st.markdown(message["content"])

                # Menu Actions
                with action_col:
                    with st.popover("⋮"):
                        if message.get("type") == "dataframe":
                            st.markdown("**Make a chart:**")
                            c1, c2, c3 = st.columns(3)
                            for c_type, btn_col in zip(["bar", "line", "pie"], [c1, c2, c3]):
                                with btn_col:
                                    st.button(c_type.capitalize(), key=f"{c_type}_{msg_id}",
                                            on_click=handle_menu_click,
                                            args=(msg_id, "pending_chart_action", {
                                                "type": c_type, "content": message["content"]
                                            }))
                            st.divider()

                        if message.get("type") == "chart":
                            st.button("Edit Graph", key=f"menu_edit_{msg_id}",
                                      on_click=handle_menu_click,
                                      args=(msg_id, "pending_edit_action", msg_id))

                        st.button("Delete", key=f"del_{msg_id}",
                                  on_click=handle_menu_click,
                                  args=(msg_id, "pending_delete_action", i))

    # Process Actions (Outside loop/popover)
    if "pending_chart_action" in st.session_state:
        action = st.session_state.pop("pending_chart_action")
        st.session_state["trigger_js_close"] = True
        st.session_state.messages.append({
            "role": "assistant",
            "type": "chart",
            "chart_type": action["type"],
            "content": action["content"],
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(),
            "duration": 0
        })
        st.rerun()

    if "pending_edit_action" in st.session_state:
        edit_msg_id = st.session_state.pop("pending_edit_action")
        st.session_state["trigger_js_close"] = True
        st.session_state[f"edit_mode_{edit_msg_id}"] = True
        st.rerun()

    if "pending_delete_action" in st.session_state:
        idx = st.session_state.pop("pending_delete_action")
        st.session_state["trigger_js_close"] = True
        if 0 <= idx < len(st.session_state.messages):
            st.session_state.messages.pop(idx)
        st.rerun()

    # Chat Input
    # 1. Prepare history for autocomplete
    user_history = []
    if os.path.exists("history.txt"):
        try:
            with open("history.txt", "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
            
            curr_db = load_config()['SQL']['database']
            for line in lines:
                if '|' in line:
                    db, query = line.split('|', 1)
                    if db.strip() == curr_db.strip():
                        user_history.append(query)
                else:
                    user_history.append(line)
        except:
            pass
    
    # 2. Render Autocomplete JS
    render_autocomplete(list(set(user_history)))

    # Input Widget
    if prompt := st.chat_input("Ask about your data..."):
        # Add User Message
        user_msg = {"role": "user", "content": prompt, "id": str(uuid.uuid4()), "timestamp": datetime.now()}
        st.session_state.messages.append(user_msg)
        
        # Save to history
        try:
            curr_db = load_config()['SQL']['database']
            new_entry = f"{curr_db}|{prompt}"
            
            # Check for duplicates
            is_duplicate = False
            if os.path.exists("history.txt"):
                with open("history.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip() == new_entry:
                            is_duplicate = True
                            break
            
            if not is_duplicate:
                with open("history.txt", "a", encoding="utf-8") as f:
                    f.write(f"{new_entry}\n")
        except Exception:
            pass
            
        # Immediate Render of User Message for responsiveness
        ts_str = datetime.now().strftime("%I:%M:%S %p")
        st.markdown(f"""
        <div class='timestamp-label timestamp-right'>{ts_str}</div>
        <div class='user-msg-container'>
            <div class='user-msg-bubble'>{prompt}</div>
        </div>
        """, unsafe_allow_html=True)

        start_time = time.time()
        
        # Process with AI
        ai = st.session_state.ai_manager
        db = st.session_state.db_manager
        
        with st.status("Thinking...", expanded=True) as status:
            # Inject Real-time Timer
            timer_id = f"timer_{uuid.uuid4()}"
            st.markdown(f"""
            <div id="{timer_id}" class="timestamp-label" style="margin-bottom: 10px; color: #888;">Starting timer...</div>
            </main>
            """, unsafe_allow_html=True)
            
            components.html(f"""
            <script>
                const timerElement = window.parent.document.getElementById('{timer_id}');
                const startTime = Date.now();
                
                function updateTimer() {{
                    if (!timerElement) return;
                    
                    const now = new Date();
                    const elapsed = (now - startTime) / 1000;
                    
                    // Format Time: HH:MM:SS PM
                    let hours = now.getHours();
                    const minutes = now.getMinutes().toString().padStart(2, '0');
                    const seconds = now.getSeconds().toString().padStart(2, '0');
                    const ampm = hours >= 12 ? 'PM' : 'AM';
                    hours = hours % 12;
                    hours = hours ? hours : 12; // the hour '0' should be '12'
                    const timeString = `${{hours.toString().padStart(2, '0')}}:${{minutes}}:${{seconds}} ${{ampm}}`;
                    
                    timerElement.innerText = `${{timeString}} (${{elapsed.toFixed(2)}}s)`;
                    timerElement.style.color = '#888';
                    timerElement.style.fontSize = '14px';
                    timerElement.style.fontFamily = '"Source Sans Pro", sans-serif';
                }}
                
                // Update every 50ms
                const intervalId = setInterval(updateTimer, 50);
            </script>
            """, height=0, width=0)

            status.write("Generating Query...")
            # Pass all messages EXCEPT the current prompt we just appended
            history = st.session_state.messages[:-1] 
            curr_db = load_config()['SQL']['database'].strip()
            sql_response = ai.generate_sql(st.session_state.schema_context, prompt, db_name=curr_db, history_messages=history)
            
            if "[ERROR]" in sql_response or "INVALID REQUEST" in sql_response:
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "error",
                    "content": sql_response,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now(),
                    "duration": time.time() - start_time
                })
            else:
                status.write("Executing SQL...")
                with st.expander("View generated SQL", expanded=False):
                    st.code(sql_response, language="sql")
                df, error = db.execute_query(sql_response)
                
                if error:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "error",
                        "content": f"Execution Failed: {error}",
                        "sql": sql_response,
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now(),
                        "duration": time.time() - start_time
                    })
                else:
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "dataframe",
                        "content": df,
                        "sql": sql_response,
                        "id": str(uuid.uuid4()),
                        "timestamp": datetime.now(),
                        "duration": time.time() - start_time
                    })
            
            status.update(label="Complete", state="complete", expanded=False)
        st.rerun()
