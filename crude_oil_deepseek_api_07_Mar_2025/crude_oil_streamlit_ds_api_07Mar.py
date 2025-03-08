# crude_oil_digital_twin_app.py
import streamlit as st
import polars as pl
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from typing import Dict, List, Optional, Union

# Set page configuration with error handling <source_id data="crude_oil_digital_twin_claude_API_v1.py" />
try:
    st.set_page_config(
        page_title="Digital Twin: Crude Oil Inventory Analysis",
        page_icon="🛢️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception as e:
    st.error(f"Error in page configuration: {e}")

# Improved error handling decorator <source_id data="crude_oil_digital_twin_claude_API_v1.py" />
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

# Main data loading function <source_id data="crude_oil_digital_twin_claude_API_v1.py" />
@st.cache_data(ttl=3600)
@handle_exceptions
def load_crude_oil_data() -> Optional[Dict[str, pl.DataFrame]]:
    """
    Load crude oil stock data from EIA API with improved error handling and caching
    Returns: Dictionary of processed dataframes for analysis
    """
    try:
        api_key = st.secrets["eia_api_key"]
        url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?frequency=weekly&data[0]=value&facets[product][]=EPC0&start=2016-01-04&end=2025-02-04&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}"
        
        with st.spinner("Fetching latest crude oil data from EIA..."):
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            records = data["response"]["data"]
            
            # Process data with Polars
            df = pl.DataFrame(records)
            df = df.with_columns(pl.col("period").str.to_datetime())
            df = df.rename({"value": "inventory", "area-name": "region"})
            
            # Convert to pandas for compatibility with existing visualization code
            pd_df = df.to_pandas()
            
            return {
                "full_dataset": df,
                "analysis_ready": pd_df,
                "recent_data": df.head(100)
            }
            
    except Exception as e:
        st.error(f"Critical data loading error: {str(e)}")
        return None

# Main application function
def main():
    st.title("🛢️ Crude Oil Inventory Digital Twin")
    st.markdown("Interactive analysis of U.S. crude oil stockpiles using EIA data")
    
    # Load data
    data = load_crude_oil_data()
    
    if data is None:
        st.error("Failed to load data. Please check the connection and API key.")
        return
    
    # Show raw data
    with st.expander("View Raw Data"):
        st.dataframe(data["analysis_ready"], use_container_width=True)
    
    # Create visualization
    st.subheader("Weekly Crude Oil Inventories")
    fig = px.line(data["analysis_ready"], 
                 x="period", 
                 y="inventory",
                 labels={"inventory": "Inventory (Million Barrels)", "period": "Date"},
                 template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    
    # Show key metrics
    latest = data["recent_data"].head(1)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Latest Inventory", f"{latest['inventory'].values[0]:,.1f} Million BBL")
    with col2:
        st.metric("Report Date", latest["period"].dt.strftime("%Y-%m-%d").values[0])
    with col3:
        st.metric("Data Frequency", "Weekly")

if __name__ == "__main__":
    main()