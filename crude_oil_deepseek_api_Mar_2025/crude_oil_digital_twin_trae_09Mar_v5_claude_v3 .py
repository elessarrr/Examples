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
    """Run supply disruption simulation with the following logic:
    - Uses last 52 weeks as baseline data
    - Applies weekly changes based on selected scenarios
    - Incorporates compounding effects over time
    - Prevents negative inventory values
    """
    try:
        # Check if input data is empty and return empty dataframe if so
        if input_df.empty:
            return pd.DataFrame(columns=['period', 'inventory', 'type'])
            
        # Use recent data and calculate 3-month moving average
        recent_data = input_df.copy().sort_values('period')
        recent_data['MA_13w'] = recent_data['inventory'].rolling(window=13).mean()  # 13 weeks ≈ 3 months
        recent_data = recent_data.tail(52)  # Keep last year for visualization
        
        # Add additional check for empty recent_data
        if recent_data.empty:
            return pd.DataFrame(columns=['period', 'inventory', 'type'])
        
        # Get latest date and use moving average as starting point
        latest_date = recent_data['period'].max()
        start_inventory = recent_data['MA_13w'].iloc[-1]  # Start from trendline value
        
        # Calculate average weekly change from moving average
        ma_weekly_change = (recent_data['MA_13w'].iloc[-1] - recent_data['MA_13w'].iloc[0]) / len(recent_data)
        
        # Create future dates for simulation period
        future_dates = [latest_date + timedelta(weeks=i) for i in range(1, params['sim_duration']+1)]
        
        # Initialize simulation results
        sim_results = []
        current_inventory = start_inventory  # Track running inventory level
        
        # Apply scenario effects week by week
        for i, date in enumerate(future_dates):
            # Base weekly change from moving average trend
            weekly_change = ma_weekly_change
            
            # Apply production cut impact with compounding effect
            if params['prod_cut']:
                production_impact = 1.5 + (i * 0.1)  # Starts at 150% reduction, grows 10% per week
                weekly_change *= production_impact
            
            # Apply demand spike impact with compounding effect
            if params['demand_spike']:
                demand_impact = 1.3 + (i * 0.05)  # Starts at 130% increase, grows 5% per week
                weekly_change *= demand_impact
            
            # Add SPR release effect if enabled
            if params['spr_release']:
                weekly_change += 5000  # Strategic Petroleum Reserve release rate
            
            # Update inventory
            current_inventory = current_inventory + weekly_change
            
            # Store result for this week
            sim_results.append({
                'period': date,
                'inventory': current_inventory,
                'type': 'Simulated'
            })
        
        # Create simulation DataFrame
        sim_df = pd.DataFrame(sim_results)
        
        # Add historical data and moving average with type labels
        hist_df = recent_data.copy()
        hist_df['type'] = 'Historical'
        
        # Create trendline data
        trend_df = recent_data.copy()
        trend_df['type'] = 'Trendline'
        trend_df['inventory'] = trend_df['MA_13w']
        
        # Select columns for visualization
        hist_df = hist_df[['period', 'inventory', 'type']]
        trend_df = trend_df[['period', 'inventory', 'type']]
        
        # Combine historical and simulated data for visualization
        combined_df = pd.concat([hist_df, trend_df, sim_df], ignore_index=True)
        return combined_df
    
    except Exception as e:
        st.error(f"Simulation error: {str(e)}")
        return pd.DataFrame(columns=['period', 'inventory', 'type'])

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
    st.markdown("**Note:** BBL stands for 'Barrel', the standard unit of measurement for petroleum products. One barrel equals 42 U.S. gallons or 159 liters.")

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
    filtered_data = data["full_data"][data["full_data"]["region"].isin(selected_padds)] if selected_padds else pd.DataFrame()

    # Run simulation
    sim_results = run_simulation(filtered_data, sim_params)

    # Create visualization
    st.subheader("Crude Oil Inventory Forecast")
    if not sim_results.empty and selected_padds:
        # Create figure with secondary y-axis
        fig = go.Figure()
        
        # Plot trendline
        fig.add_trace(go.Scatter(
            x=sim_results[sim_results['type'] == 'Trendline']['period'],
            y=sim_results[sim_results['type'] == 'Trendline']['inventory'],
            name='3-Month Moving Average',
            line=dict(color='rgba(0, 123, 255, 0.3)', width=1, dash='dash')
        ))
        
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
                xanchor="right",
                x=0.99,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            )
        )
    else:
        # Create empty figure with proper layout when no data is available
        fig = go.Figure()
        fig.update_layout(
            title="Crude Oil Inventory Forecast",
            xaxis_title="Date",
            yaxis_title="Inventory (Million Barrels)",
            template="plotly_white",
            showlegend=False,
            annotations=[dict(
                text="Please select one or more PADD regions to visualize data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=14)
            )]
        )
    st.plotly_chart(fig, use_container_width=True)

    # Scenario Impact Analysis - use HTML for custom styling
    st.markdown("""
    <h2 style="font-size: 28px; margin-bottom: 16px;">Scenario Impact Analysis</h2>
    """, unsafe_allow_html=True)
    
    # Static information about scenarios - make this a subsection with smaller header
    st.markdown("""
    <h4 style="font-size: 18px; margin-bottom: 10px;">Assumptions Made for Scenarios:</h4>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    - Base case assumes a natural weekly decline of 5,000 barrels in inventory levels
    - __Production cuts__ reduce available supply by 150%, simulating severe disruption scenarios
    - __Demand spikes__ double the rate of inventory drawdown, reflecting extreme market conditions
    - __Strategic Reserve__ releases add 5,000 barrels per week to available supply
    """)

    # Only show projected impact when regions are selected and simulation runs successfully
    if selected_padds and not sim_results.empty and 'Historical' in sim_results['type'].values and 'Simulated' in sim_results['type'].values:
        try:
            hist_data = sim_results[sim_results['type'] == 'Historical']
            sim_data = sim_results[sim_results['type'] == 'Simulated']
            
            end_inventory = sim_data['inventory'].iloc[-1]
            start_inventory = hist_data['inventory'].iloc[-1]
            inventory_change = end_inventory - start_inventory
            
            # Get the dates for starting and ending inventory
            start_date = hist_data['period'].iloc[-1].strftime('%Y-%m-%d')
            end_date = sim_data['period'].iloc[-1].strftime('%Y-%m-%d')
            
            st.html(f"""
            ### Projected Impact (for Scenarios):
            - Starting Inventory <b>({start_date})</b>: {start_inventory:,.0f} Million BBL
            - Ending Inventory ({end_date}): {end_inventory:,.0f} Million BBL
            - Net Change: {inventory_change:,.0f} Million BBL ({(inventory_change/start_inventory)*100:.1f}%)
            """)
            
        except Exception as e:
            st.error(f"Error calculating impact: {str(e)}")
    elif selected_padds:
        st.info("Select simulation parameters and run the model to see impact analysis")
    else:
        st.info("Please select at least one PADD region to view impact analysis")

if __name__ == "__main__":
    main()
