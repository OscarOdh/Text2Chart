import streamlit as st

def load_css():
    """Load custom CSS styles."""
    st.markdown("""
    <style>
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stChatMessage {
            background-color: #262730;
            border-radius: 10px;
            padding: 10px;
            margin-bottom: 10px;
        }
        .stButton>button {
            width: 100%; /* Fill the tight column */
            min-width: 0;
            border-radius: 4px;
            height: auto;
            background-color: #ff4b4b;
            color: white;
            padding: 4px 8px; /* Compact padding */
            font-size: 12px; /* Smaller font */
            line-height: 1.2;
            white-space: nowrap; /* Prevent text wrapping */
        }
        
        /* Clear Button Links */
        .st-key-clear_chat {
            margin-top: -10px !important;
            margin-bottom: -10px !important;
        }
        .st-key-clear_history {
            margin-top: 20px !important; /* Space above */
            margin-bottom: -15px !important;
        }
        .st-key-clear_chat button, .st-key-clear_chat button:hover,
        .st-key-clear_history button, .st-key-clear_history button:hover {
            background-color: transparent !important;
            border: none !important;
            color: #ff4b4b !important;
            text-decoration: underline;
            padding: 0 !important;
            font-size: 13px !important;
            width: auto !important;
            height: auto !important;
            box-shadow: none !important;
            min-width: 0 !important;
        }
        /* Status indicators */
        .status-box {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
            text-align: center;
            font-weight: bold;
        }
        .status-success { background-color: #28a745; color: white; }
        .status-error { background-color: #dc3545; color: white; }
        
        /* Hide Deploy Button - Robust */
        .stDeployButton, .stAppDeployButton {
            display: none !important;
            visibility: hidden !important;
        }
        
        [data-testid="stDeployButton"] {
            display: none !important;
        }

        /* Chat UI Refinement */
        .user-msg-container {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 10px;
        }
        .user-msg-bubble {
            background-color: #ff4b4b;
            color: white;
            padding: 10px 15px;
            border-radius: 15px 15px 0 15px;
            max-width: 70%;
            text-align: right;
        }
        
        .status-box {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .timestamp-label {
            font-size: 0.8em;
            color: #888;
            margin-bottom: 2px;
        }
        .timestamp-right {
            text-align: right;
            margin-bottom: 2px;
        }
        .duration-label {
            font-size: 1em;
            color: #888;
            margin-left: 3px;
        }
        
        /* Input Visibility */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
            border: 1px solid rgba(250, 250, 250, 0.2) !important;
        }
        .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox div[data-baseweb="select"]:focus-within > div {
            border-color: #ff4b4b !important;
        }
        
        /* Menu/Popover Button Styling */
        [data-testid="stPopoverBody"] button {
            background-color: transparent !important;
            border: none !important;
            color: #fafafa !important;
            text-align: left !important;
            padding: 8px 12px !important;
            display: block !important;
            width: 100% !important;
            font-weight: normal !important;
            font-size: 12px !important;
            margin: 0 !important;
        }
        [data-testid="stPopoverBody"] button:hover {
            background-color: transparent !important;
            color: white !important;
            text-decoration: underline !important;
            border: none !important;
            box-shadow: none !important;
        }
        
        /* Dropdown Menu Border */
        div[data-baseweb="popover"], div[data-baseweb="menu"] {
             border: 1px solid rgba(250, 250, 250, 0.2) !important;
             border-radius: 4px !important;
        }
        [data-testid="stPopoverBody"] hr {
            margin: 5px 0 !important;
        }
        [data-testid="stPopoverBody"] {
            width: 200px !important;
            min-width: unset !important;
        }
        
        /* Ensure content column takes remaining space */
        [data-testid="stChatMessage"] [data-testid="column"]:nth-of-type(1) {
             flex: 1 !important;
             width: auto !important;
             min-width: 0 !important; /* Allow shrinking */
        }
        
    /* --- NEW HISTORY UI STYLING (Transparent, Borderless) --- */
        
        /* 1. Target the Row Container */
        div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-hist_del"]) {
            gap: 2px !important; /* Minimal gap, handle spacing via margins */
            align-items: center !important;
            margin-bottom: -30px !important; /* Tighten vertical spacing further */
        }
        
        /* Force Fixed Width for X Column - HARDENED */
        /* Force Fixed Width for X Column - HARDENED & WIDENED */
        div[data-testid="column"]:has(div[class*="st-key-hist_del"]) {
            flex: 0 0 32px !important;
            width: 32px !important;
            min-width: 32px !important;
            max-width: 32px !important;
            padding: 0 !important;
            margin: 0 !important;
        }

        /* 2. Target the 'X' Button Key */
        div[class*="st-key-hist_del"] button {
            border: none !important;
            background: transparent !important;
            color: #666 !important;
            padding: 0 !important;
            margin: 0 !important;
            height: auto !important;
            min-height: 0 !important;
            line-height: 1 !important;
            box-shadow: none !important;
            box-shadow: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        div[class*="st-key-hist_del"] button:hover {
            color: #ff4b4b !important;
            background: transparent !important;
            border: none !important;
        }

        /* 3. Target the 'Text' Button Key - AGGRESSIVE FIX */
        div[class*="st-key-hist_btn"] {
             width: 100% !important;
             display: flex !important;
             justify-content: flex-start !important;
        }
        
        div[class*="st-key-hist_btn"] button {
            border: none !important; 
            background: transparent !important;
            color: #fafafa !important;
            
            font-size: 13px !important;
            font-weight: normal !important;
            
            /* RESET EVERYTHING */
            padding: 0 !important;
            margin: 0 !important;
            margin-left: 8px !important; /* Rigid separation margin */
            min-width: 0 !important;
            width: 100% !important; /* Force full width */
            
            /* FLEX ALIGNMENT */
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important; /* Left Align */
            text-align: left !important;
            
            height: auto !important;
            box-shadow: none !important;
        }

        /* Target INNER divs of the button (Streamlit wraps text in a div) */
        div[class*="st-key-hist_btn"] button > div {
             display: flex !important;
             justify-content: flex-start !important;
             text-align: left !important;
             width: 100% !important;
             flex: 1 !important;
        }

        /* Target the P tag or any text content */
        div[class*="st-key-hist_btn"] button p,
        div[class*="st-key-hist_btn"] button span {
             margin: 0 !important;
             padding: 0 !important;
             text-align: left !important;
             font-size: 13px !important;
             width: 100% !important;
             display: block !important;
             white-space: nowrap !important;
             overflow: hidden !important;
             text-overflow: ellipsis !important;
        }
        
        /* Force the column itself to align items to start */
        div[data-testid="column"]:has(div[class*="st-key-hist_btn"]) {
             align-items: flex-start !important;
             justify-content: flex-start !important;
             display: flex !important;
        }

        /* Hover Effect - Subtle background change on text only */
        /* Hover Effect - Subtle text color change only, no box */
        div[class*="st-key-hist_btn"] button:hover {
            color: #ff4b4b !important;
            background: transparent !important; /* No highlight box */
            border: none !important;
            text-decoration: none !important;
        }
        
        /* Remove Focus Outlines */
        div[class*="st-key-hist"] button:focus,
        div[class*="st-key-hist"] button:active {
             outline: none !important;
             box-shadow: none !important;
             border: none !important;
        }
             box-shadow: none !important;
             border: none !important;
         }
         
         /* Hide Zero-Height Components (Script Injections) completely from layout flow */
         iframe[height="0"] {
             display: none;
         }
         /* Also target the streamlit container to remove margins/padding */
         div[data-testid="stElementContainer"]:has(iframe[height="0"]) {
             position: absolute !important;
             width: 0 !important;
             height: 0 !important;
             margin: 0 !important;
             padding: 0 !important;
             overflow: hidden !important;
         }
    </style>
    """, unsafe_allow_html=True)
