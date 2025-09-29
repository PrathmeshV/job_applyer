from datetime import datetime
import streamlit as st

def calendar_dropdown(label="Select Date"):
    """Creates a calendar dropdown for date selection."""
    selected_date = st.date_input(label, datetime.today())
    return selected_date