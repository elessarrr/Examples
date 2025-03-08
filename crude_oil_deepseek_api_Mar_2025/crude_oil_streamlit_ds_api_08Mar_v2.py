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

# Configuration
try:
    st.set_page_config(
        page_title="Crude Oil Digital Twin",
        page_icon="🛢️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception as e:
    st.error(f"Page config error: {e}")

# Error handling decorator
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

# Data loading
@st.cache_data(ttl=3600)
@handle_exceptions
def load_crude_oil_data() -> Optional[Dict[str, Union[pl.DataFrame, pd.DataFrame]]]:
    """Load and process EIA crude oil inventory data"""
    try:
        api_key = 'nsH8duWHIP4GA3eL1RgSoWh8my1gGOBpfzqyIeKp'
        url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?frequency=weekly&data[0]=value&facets[product][]=EPC0&start=2016-01-04&end=2025-02-04&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}"
        
        
        with st.spinner("Loading EIA data..."):
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            df = pl.DataFrame(data["response"]["data"])
            
            if df.is_empty():
                st.error("No data received from API")
                return None
                
            # Process data
            df = df.rename({"value": "inventory", "area-name": "region"})
            df = df.with_columns([
                pl.col("period").str.to_datetime("%Y-%m-%d"),
                pl.col("inventory").cast(pl.Float64)
            ])
            
            # Convert to pandas for visualization compatibility
            pd_df = df.to_pandas()
            
            return {
                "full_data": df,
                "analysis_data": pd_df,
                "regions": df["region"].unique().to_list()
            }
            
    except Exception as e:
        st.error(f"Data load failed: {str(e)}")
        return None

# Main application
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
            inv_val = latest["inventory"].item()
            st.metric("Latest Inventory", f"{float(inv_val):,.1f} Million BBL")
        except Exception as e:
            st.error(f"Inventory error: {str(e)}")
    with col2:
        try:
            report_date = latest["period"].dt.strftime("%Y-%m-%d").item()
            st.metric("Report Date", report_date)
        except Exception as e:
            st.error(f"Date error: {str(e)}")
    with col3:
        st.metric("Data Frequency", "Weekly")

    # Region selection
    st.sidebar.header("Filter Options")
    selected_padds = st.sidebar.multiselect(
        "Select PADD Regions:",
        options=data["regions"],
        default=["PADD 2"],
        help="Select 1 or more regions to analyze"
    )

    # Filter data
    filtered_data = data["analysis_data"][
        data["analysis_data"]["region"].isin(selected_padds)
    ]
    
    # Create visualization
    fig = go.Figure()
    
    # Always add individual region traces
    for padd in selected_padds:
        padd_df = filtered_data[filtered_data["region"] == padd]
        fig.add_trace(go.Scatter(
            x=padd_df["period"],
            y=padd_df["inventory"],
            mode="lines",
            name=padd,
            hovertemplate="%{x|%b %d %Y}: %{y:,.0f}M bbl<extra></extra>",
            showlegend=True  # Force legend visibility
        ))
    
    # Always add total line when any regions are selected
    if selected_padds:
        total_df = filtered_data.groupby("period", as_index=False)["inventory"].sum()
        total_df["region"] = "Total"
        fig.add_trace(go.Scatter(
            x=total_df["period"],
            y=total_df["inventory"],
            mode="lines",
            name="Total",
            line=dict(dash="dot", width=2),
            hovertemplate="%{x|%b %d %Y}: %{y:,.0f}M bbl<extra>Total</extra>",
            showlegend=True  # Force legend visibility
        ))

    # Updated layout configuration
    fig.update_layout(
        title="Crude Oil Stock Levels by Region",
        xaxis_title="Date",
        yaxis_title="Inventory (Million Barrels)",
        height=600,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            title_text="Legend:",
            font=dict(size=12)
        ),
        showlegend=True  # Ensure legend is always visible
    )
    
    # Dynamic axis scaling
    fig.update_yaxes(
        autorange=True,
        tickformat=",.0f",
        gridcolor="rgba(200,200,200,0.2)"
    )
    
    fig.update_xaxes(
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(step="all")
            ])
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Raw data view
    with st.expander("View Filtered Data"):
        st.dataframe(filtered_data, use_container_width=True)

if __name__ == "__main__":
    main()