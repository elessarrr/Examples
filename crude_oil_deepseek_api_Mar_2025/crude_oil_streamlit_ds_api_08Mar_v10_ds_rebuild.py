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

# Simulation function
@handle_exceptions
def run_simulation(input_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Enhanced simulation with dramatic visual impact"""
    try:
        # Use only recent data as baseline (last 52 weeks)
        recent_data = input_df.copy().sort_values('period').tail(52)
        
        # Get the latest date and inventory as starting point
        latest_date = recent_data['period'].max()
        start_inventory = recent_data['inventory'].iloc[-1]
        
        # Create future dates for simulation
        future_dates = [latest_date + timedelta(weeks=i) for i in range(1, params['sim_duration']+1)]
        
        # Initialize simulation dataframe
        sim_results = []
        current_inventory = start_inventory
        
        # Apply dramatic effects based on parameters
        for i, date in enumerate(future_dates):
            # Calculate weekly change factors
            production_factor = 0.35 if params['prod_cut'] else 1.0  # 65% reduction if disruption
            
            # Demand impact (more dramatic for visualization)
            if params['demand_spike'] == "+30% Exports":
                weekly_change = -15000  # Baseline weekly decrease
            elif params['demand_spike'] == "+15% Refining":
                weekly_change = -10000  # Moderate weekly decrease
            else:
                weekly_change = -5000  # Minimal weekly decrease
            
            # Apply production disruption effect
            weekly_change *= production_factor
            
            # Add SPR release effect (more dramatic)
            if params['spr_release']:
                weekly_change += 8000  # 8M barrels/week (more dramatic than reality)
            
            # Cumulative effect (increasing impact over time)
            cumulative_factor = (i + 1) * 1.2  # Amplify effect over time
            period_change = weekly_change * cumulative_factor
            
            # Update inventory with constraints
            current_inventory = max(100000, current_inventory + period_change)  # Prevent negative
            
            # Store result
            sim_results.append({
                'period': date,
                'inventory': current_inventory,
                'scenario': params['demand_spike']
            })
        
        return pd.DataFrame(sim_results)
    
    except Exception as e:
        st.error(f"Simulation error: {str(e)}")
        return pd.DataFrame()

# Main application
def main():
    st.title("🛢️ Crude Oil Inventory Digital Twin")
    st.markdown("Interactive analysis of U.S. crude oil stockpiles using EIA data")
    
    # Load data
    data = load_crude_oil_data()
    if data is None:
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

    # Simulation controls
    st.header("🧪 Supply Chain Simulation Engine")
    
    with st.expander("⚙️ Configure Simulation Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            sim_duration = st.slider("Simulation Weeks", 1, 26, 8)
            prod_cut = st.checkbox("Production Disruption (PADD 3)")
        with col2:
            demand_spike = st.selectbox("Demand Scenario", 
                                      ["Normal", "+15% Refining", "+30% Exports"])
            spr_release = st.checkbox("Strategic Petroleum Reserve Release")
        with col3:
            transport_cap = st.slider("Transport Capacity (%)", 50, 100, 85)
            risk_factor = st.slider("Risk Multiplier", 0.5, 2.0, 1.0)

    # Run simulation
    sim_params = {
        "sim_duration": sim_duration,
        "prod_cut": prod_cut,
        "demand_spike": demand_spike,
        "spr_release": spr_release,
        "transport_cap": transport_cap,
        "risk_factor": risk_factor
    }

    try:
        sim_results = run_simulation(data["analysis_data"], sim_params)
    except Exception as e:
        st.error(f"Simulation failed: {str(e)}")
        st.stop()

    # Visualization
    st.subheader("Simulation Results")
    fig = go.Figure()
    
    # Simulation trace
    fig.add_trace(go.Scatter(
        x=sim_results['period'],
        y=sim_results['inventory'],
        mode='lines+markers',
        name='Simulated Inventory',
        line=dict(color='red', width=3)
    ))
    
    # Historical trace
    fig.add_trace(go.Scatter(
        x=data["analysis_data"]['period'],
        y=data["analysis_data"]['inventory'],
        mode='lines',
        name='Historical',
        line=dict(color='blue', dash='dot')
    ))
    
    fig.update_layout(
        title="Crude Oil Inventory Simulation",
        xaxis_title="Date",
        yaxis_title="Inventory (Million Barrels)",
        height=600,
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
