import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
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

# Data loading with proper caching
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

@handle_exceptions
def run_simulation(input_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Run supply disruption simulation"""
    try:
        # Use recent data as baseline (last 52 weeks)
        recent_data = input_df.copy().sort_values('period').tail(52)
        
        # Get latest date and inventory as starting point
        latest_date = recent_data['period'].max()
        start_inventory = recent_data['inventory'].iloc[-1]
        
        # Create future dates for simulation
        future_dates = [latest_date + timedelta(weeks=i) for i in range(1, params['sim_duration']+1)]
        
        # Initialize simulation results
        sim_results = []
        current_inventory = start_inventory
        
        # Apply scenario effects
        for i, date in enumerate(future_dates):
            # Base weekly change (normal conditions)
            weekly_change = -5000  # Baseline weekly decrease
            
            # Apply production cut impact with compounding effect
            if params['prod_cut']:
                production_impact = 1.5 + (i * 0.1)  # Increasing impact over time
                weekly_change *= production_impact
            
            # Apply demand spike impact with compounding effect
            if params['demand_spike']:
                demand_impact = 1.3 + (i * 0.05)  # Increasing impact over time
                weekly_change *= demand_impact
            
            # Add SPR release effect if enabled
n             if params['spr_release']:
                weekly_change += 5000  # 5M barrels/week SPR release
            
            # Update inventory with constraints
            current_inventory = max(100000, current_inventory + weekly_change)  # Prevent negative
            
            # Store result
            sim_results.append({
                'period': date,
                'inventory': current_inventory,
                'type': 'Simulated'
            })
        
        # Create simulation DataFrame
        sim_df = pd.DataFrame(sim_results)
        
        # Add historical data with type label
        hist_df = recent_data.copy()
        hist_df['type'] = 'Historical'
        hist_df = hist_df[['period', 'inventory', 'type']]
        
        # Combine historical and simulated data
        combined_df = pd.concat([hist_df, sim_df], ignore_index=True)
        return combined_df
    
    except Exception as e:
        st.error(f"Simulation error: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_padd_map(url: str) -> Optional[bytes]:
    """Fetch and cache PADD region map"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Failed to load PADD map: {str(e)}")
        return None

def main():
    st.title("🛢️ Crude Oil Inventory Digital Twin")
    st.markdown("Interactive analysis of U.S. crude oil stockpiles with supply disruption simulation")
    
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

    # Simulation controls
    st.sidebar.header("Simulation Parameters")
    sim_params = {
        'sim_duration': st.sidebar.slider("Simulation Duration (weeks)", 4, 52, 12),
        'prod_cut': st.sidebar.checkbox("Production Cut Scenario", False),
        'demand_spike': st.sidebar.checkbox("Demand Spike Scenario", False),
        'spr_release': st.sidebar.checkbox("Strategic Reserve Release", False)
    }

    # Add PADD map visualization section
    st.sidebar.header("PADD Regions Reference")
    with st.sidebar.expander("🗺️ What are PADD Regions?"): 
        st.markdown("""
        **Petroleum Administration for Defense Districts (PADD):**
        - PADD 1: East Coast
        - PADD 2: Midwest
        - PADD 3: Gulf Coast
        - PADD 4: Rocky Mountain
        - PADD 5: West Coast
        """)
        
        # Responsive image with caching
        padd_map_url = "https://www.eia.gov/todayinenergy/images/2012.02.07/PADDsMap.png"
        
        try:
            st.image(
                padd_map_url,
                use_container_width=True,
                caption="Source: U.S. Energy Information Administration (EIA)",
                output_format="PNG"
            )
        except Exception as e:
            st.error(f"Error loading PADD map: {str(e)}")
            st.markdown(f"[View PADD Map Here]({padd_map_url})")

    # Region selection
    st.sidebar.header("Filter Options")
    selected_padds = st.sidebar.multiselect(
        "Select PADD Regions:",
        options=data["regions"],
        default=["PADD 2"],
        help="Select 1 or more regions to analyze"
    )

    # Filter data
    filtered_data = data["full_data"][data["full_data"]["region"].isin(selected_padds)]

    # Run simulation
    sim_results = run_simulation(filtered_data, sim_params)

    # Visualization
    st.subheader("Crude Oil Inventory Forecast")
    if not sim_results.empty:
        fig = go.Figure()

        # Plot historical data
        hist_data = sim_results[sim_results['type'] == 'Historical']
        fig.add_trace(go.Scatter(
            x=hist_data['period'],
            y=hist_data['inventory'],
            name=f'Historical ({", ".join(selected_padds)})',
            line=dict(color='blue'),
            hovertemplate='%{x|%Y-%m-%d}<br>Inventory: %{y:,.0f} Million BBL<extra></extra>'
        ))

        # Plot simulated data
        sim_data = sim_results[sim_results['type'] == 'Simulated']
        fig.add_trace(go.Scatter(
            x=sim_data['period'],
            y=sim_data['inventory'],
            name=f'Simulated ({", ".join(selected_padds)})',
            line=dict(color='red', dash='dash'),
            hovertemplate='%{x|%Y-%m-%d}<br>Inventory: %{y:,.0f} Million BBL<extra></extra>'
        ))

        fig.update_layout(
            title="Crude Oil Inventory Forecast",
            xaxis_title="Date",
            yaxis_title="Inventory (Million Barrels)",
            hovermode='x unified',
            template="plotly_white",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # Scenario Impact Analysis
        st.subheader("Scenario Impact Analysis")
        end_inventory = sim_data['inventory'].iloc[-1]
        start_inventory = hist_data['inventory'].iloc[-1]
        inventory_change = end_inventory - start_inventory
        
        st.markdown(f"""
        ### Projected Impact:
        - Starting Inventory: {start_inventory:,.0f} Million BBL
        - Ending Inventory: {end_inventory:,.0f} Million BBL
        - Net Change: {inventory_change:,.0f} Million BBL ({(inventory_change/start_inventory)*100:.1f}%)
        
        ### Assumptions Made:
        - Base case assumes a natural weekly decline of 5,000 barrels in inventory levels
        - Production cuts reduce available supply by 150%, simulating severe disruption scenarios
        - Demand spikes double the rate of inventory drawdown, reflecting extreme market conditions
        """)

if __name__ == "__main__":
    main()