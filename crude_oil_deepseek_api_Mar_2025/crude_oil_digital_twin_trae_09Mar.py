import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import requests
from typing import Dict, Optional

# Configuration
try:
    st.set_page_config(
        page_title="Crude Oil Digital Twin",
        page_icon="🛢️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception as e:
    st.error(f"Page configuration error: {str(e)}")

# Error handling decorator
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

@st.cache_data(ttl=3600)
@handle_exceptions
def load_crude_oil_data() -> Optional[Dict]:
    """Load and process EIA crude oil inventory data"""
    try:
        api_key = 'nsH8duWHIP4GA3eL1RgSoWh8my1gGOBpfzqyIeKp'
        url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
        params = {
            "frequency": "weekly",
            "data[0]": "value",
            "facets[product][]": "EPC0",
            "start": "2016-01-04",
            "end": "2025-02-04",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": 0,
            "length": 5000,
            "api_key": api_key
        }
        
        with st.spinner("Loading EIA data..."):
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data["response"]["data"])
            
            if df.empty:
                st.error("No data received from API")
                return None
                
            # Process data
            df = df.rename(columns={"value": "inventory", "area-name": "region"})
            df["period"] = pd.to_datetime(df["period"])
            df["inventory"] = pd.to_numeric(df["inventory"])
            
            return {
                "full_data": df,
                "regions": df["region"].unique().tolist()
            }
            
    except Exception as e:
        st.error(f"Data load failed: {str(e)}")
        return None

def main():
    st.title("🛢️ Crude Oil Inventory Digital Twin")
    st.markdown("Interactive analysis of U.S. crude oil stockpiles using EIA API data")
    
    # Load data
    data = load_crude_oil_data()
    if not data:
        st.stop()

    # Key metrics
    latest = data["full_data"].head(1)
    col1, col2, col3 = st.columns(3)
    with col1:
        try:
            inv_val = latest["inventory"].iloc[0]
            st.metric("Latest Inventory", f"{float(inv_val):,.1f} Million BBL")
        except Exception as e:
            st.error(f"Inventory error: {str(e)}")
    with col2:
        try:
            report_date = latest["period"].iloc[0].strftime("%Y-%m-%d")
            st.metric("Report Date", report_date)
        except Exception as e:
            st.error(f"Date error: {str(e)}")
    with col3:
        st.metric("Data Frequency", "Weekly")

    # Create visualization
    st.subheader("Weekly Crude Oil Inventories")
    fig = px.line(
        data["full_data"],
        x="period",
        y="inventory",
        color="region",
        labels={"inventory": "Inventory (Million Barrels)", "period": "Date"},
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()