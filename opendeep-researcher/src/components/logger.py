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
        self.log(message, "⚠️ WARNING")
        
    def error(self, message):
        self.log(message, "❌ ERROR")
        
    def success(self, message):
        self.log(message, "✅ SUCCESS")

    def display(self):
        if st.session_state.log_messages:
            for message in reversed(st.session_state.log_messages[-20:]):  # Show last 20 messages
                st.text(message)
        else:
            st.text("No log messages yet.")