"""
Utility functions for handling PyArrow compatibility issues.
"""

import streamlit as st
import pandas as pd


def safe_dataframe(df: pd.DataFrame, **kwargs):
    """
    Safely display a DataFrame, falling back to HTML table if PyArrow fails.
    
    Args:
        df: The DataFrame to display
        **kwargs: Arguments to pass to st.dataframe
    """
    try:
        st.dataframe(df, **kwargs)
    except (ImportError, Exception) as e:
        if "pyarrow" in str(e).lower() or "arrow" in str(e).lower():
            st.warning("⚠️ Enhanced DataFrames temporarily unavailable. Showing HTML table:")
            
            # Create HTML table as fallback
            html_table = df.to_html(escape=False, classes='streamlit-table', table_id='fallback-table')
            
            # Add some basic styling
            styled_html = f"""
            <style>
            .streamlit-table {{
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                font-family: sans-serif;
                min-width: 400px;
                border-radius: 5px 5px 0 0;
                overflow: hidden;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
            }}
            .streamlit-table thead tr {{
                background-color: #009879;
                color: #ffffff;
                text-align: left;
            }}
            .streamlit-table th,
            .streamlit-table td {{
                padding: 12px 15px;
                border-bottom: 1px solid #dddddd;
            }}
            .streamlit-table tbody tr:nth-of-type(even) {{
                background-color: #f3f3f3;
            }}
            .streamlit-table tbody tr:last-of-type {{
                border-bottom: 2px solid #009879;
            }}
            </style>
            {html_table}
            """
            
            st.markdown(styled_html, unsafe_allow_html=True)
        else:
            raise e


def safe_bar_chart(data, **kwargs):
    """
    Safely display a bar chart, with fallback for PyArrow issues.
    
    Args:
        data: The data to chart
        **kwargs: Arguments to pass to st.bar_chart
    """
    try:
        st.bar_chart(data, **kwargs)
    except (ImportError, Exception) as e:
        if "pyarrow" in str(e).lower() or "arrow" in str(e).lower():
            st.warning("⚠️ Enhanced charts temporarily unavailable. Showing HTML table:")
            
            # Convert data to DataFrame if it isn't already
            if hasattr(data, 'reset_index'):
                chart_df = data.reset_index()
            else:
                chart_df = pd.DataFrame(data)
            
            # Create HTML table
            html_table = chart_df.to_html(escape=False, classes='chart-table')
            styled_html = f"""
            <style>
            .chart-table {{
                border-collapse: collapse;
                margin: 10px 0;
                font-size: 0.9em;
                min-width: 300px;
                border: 1px solid #ddd;
            }}
            .chart-table th, .chart-table td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            .chart-table th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            </style>
            {html_table}
            """
            st.markdown(styled_html, unsafe_allow_html=True)
        else:
            raise e


def safe_download_button(label: str, data, file_name: str, mime: str, **kwargs):
    """
    Safely create a download button, with fallback for PyArrow issues.
    
    Args:
        label: Button label
        data: Data to download
        file_name: Name of the file
        mime: MIME type
        **kwargs: Additional arguments
    """
    try:
        return st.download_button(
            label=label,
            data=data,
            file_name=file_name,
            mime=mime,
            **kwargs
        )
    except (ImportError, Exception) as e:
        if "pyarrow" in str(e).lower() or "arrow" in str(e).lower():
            st.warning("⚠️ Download functionality temporarily unavailable due to PyArrow issue.")
            st.info(f"💡 **Workaround:** Copy the data below and save manually as `{file_name}`")
            
            # Create an expandable section for the data
            with st.expander(f"📋 Click to view {file_name} content"):
                if mime == "text/csv":
                    st.text_area("CSV Data (select all and copy):", value=data, height=200, label_visibility="collapsed")
                elif mime == "application/json":
                    st.code(data, language="json")
                elif mime == "text/markdown":
                    st.text_area("Markdown Data (select all and copy):", value=data, height=200, label_visibility="collapsed")
                else:
                    st.text_area("Data (select all and copy):", value=str(data), height=200, label_visibility="collapsed")
            return False
        else:
            raise e
