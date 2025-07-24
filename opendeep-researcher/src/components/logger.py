import streamlit as st
import datetime

class Logger:
    def __init__(self):
        if 'log_messages' not in st.session_state:
            st.session_state.log_messages = []

    def log(self, message, level="INFO"):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{level}] {timestamp} - {message}"
        st.session_state.log_messages.append(log_entry)
        
        # Keep only last 100 messages to prevent memory issues
        if len(st.session_state.log_messages) > 100:
            st.session_state.log_messages = st.session_state.log_messages[-100:]

    def info(self, message):
        self.log(message, "INFO")
        
    def warning(self, message):
        self.log(message, "WARNING")
        
    def error(self, message):
        self.log(message, "ERROR")
        
    def success(self, message):
        self.log(message, "SUCCESS")

    def display(self, height=200):
        """Display log messages in a terminal-like format with fixed height."""
        if st.session_state.log_messages:
            # Join all messages into a single string for better formatting
            log_text = "\n".join(reversed(st.session_state.log_messages[-50:]))  # Show last 50 messages
            st.text_area(
                "",
                value=log_text,
                height=height,
                disabled=True,
                key="log_display",
                label_visibility="collapsed",
                help="Terminal output - showing last 50 log entries"
            )
        else:
            st.text_area(
                "",
                value="Terminal ready...",
                height=height,
                disabled=True,
                key="log_display_empty",
                label_visibility="collapsed",
                help="Terminal output - no messages yet"
            )