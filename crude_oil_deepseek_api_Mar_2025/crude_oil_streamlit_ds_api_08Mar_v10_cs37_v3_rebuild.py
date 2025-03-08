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
                weekly_change += 8000  # 8M barrels/week
            
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

def main():
    # Executive summary in sidebar
    st.sidebar.title("Executive Summary")
    st.sidebar.markdown("""
    This digital twin provides:
    - Real-time inventory monitoring
    - Scenario-based risk analysis
    - Supply chain disruption modeling
    - Strategic reserve impact assessment
    
    **Key Capabilities:**
    - Model production disruptions
    - Simulate demand spikes
    - Evaluate SPR release effectiveness
    - Quantify recovery timelines
    """)

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

    # Add PADD map in sidebar
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

        # ================== SIMULATION SECTION ==================
    st.header("🧪 Supply Chain Simulation Engine")
    
    with st.expander("⚙️ Configure Simulation Parameters", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            sim_duration = st.slider(
                "Simulation Duration (weeks)",
                min_value=1,
                max_value=52,
                value=8,
                help="Number of weeks to simulate into the future"
            )
            prod_cut = st.checkbox(
                "PADD 3 Production Disruption (-65%)",
                help="Simulate Gulf Coast storm impacts"
            )
        with col2:
            demand_spike = st.selectbox(
                "Demand Scenario",
                options=["Normal", "+15% Refining", "+30% Exports"],
                index=0,
                help="Select demand impact scenario"
            )
            spr_release = st.checkbox(
                "SPR Release (5M bbl/week)",
                help="Strategic Petroleum Reserve activation"
            )

    # Scenario presets
    st.subheader("Quick Scenarios")
    scenario_cols = st.columns(4)
    with scenario_cols[0]:
        if st.button("🌀 Hurricane Scenario"):
            sim_params = {
                "sim_duration": 12,
                "prod_cut": True,
                "demand_spike": "Normal",
                "spr_release": True
            }
            st.session_state.update(sim_params)
            st.experimental_rerun()

    with scenario_cols[1]:
        if st.button("🚢 Export Surge"):
            sim_params = {
                "sim_duration": 16,
                "prod_cut": False,
                "demand_spike": "+30% Exports",
                "spr_release": False
            }
            st.session_state.update(sim_params)
            st.experimental_rerun()

    with scenario_cols[2]:
        if st.button("🚗 Summer Driving"):
            sim_params = {
                "sim_duration": 8,
                "prod_cut": False,
                "demand_spike": "+15% Refining",
                "spr_release": False
            }
            st.session_state.update(sim_params)
            st.experimental_rerun()

    with scenario_cols[3]:
        if st.button("↺ Reset Defaults"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.experimental_rerun()

        # Package simulation parameters
    sim_params = {
        "sim_duration": sim_duration,
        "prod_cut": prod_cut,
        "demand_spike": demand_spike,
        "spr_release": spr_release
    }

    # Execute simulation
    try:
        sim_results = run_simulation(data["analysis_data"], sim_params)
        if sim_results.empty:
            st.error("Simulation produced no results")
            st.stop()
    except Exception as e:
        st.error(f"Simulation failed: {str(e)}")
        st.stop()

    # ================== VISUALIZATION SECTION ==================
    st.subheader("Simulation Results")

    # Create enhanced figure
    fig = go.Figure()

    # Add simulation trace with enhanced styling
    fig.add_trace(go.Scatter(
        x=sim_results['period'],
        y=sim_results['inventory'],
        mode='lines+markers',
        name='Simulated',
        line=dict(color='red', width=4),
        marker=dict(size=8),
        hovertemplate='<b>%{x|%b %d, %Y}</b><br>Inventory: %{y:,.0f} barrels<extra></extra>'
    ))

    # Filter and add historical trace
    historical_cutoff = sim_results['period'].min() - pd.Timedelta(weeks=26)
    recent_historical = data["analysis_data"][
        data["analysis_data"]['period'] >= historical_cutoff
    ]

    fig.add_trace(go.Scatter(
        x=recent_historical['period'],
        y=recent_historical['inventory'],
        mode='lines',
        name='Historical',
        line=dict(color='blue', width=2, dash='dot'),
        hovertemplate='<b>%{x|%b %d, %Y}</b><br>Inventory: %{y:,.0f} barrels<extra></extra>'
    ))

    # Add reference point for current inventory
    fig.add_trace(go.Scatter(
        x=[recent_historical['period'].max()],
        y=[recent_historical['inventory'].iloc[-1]],
        mode='markers',
        marker=dict(color='green', size=12, symbol='star'),
        name='Current',
        hoverinfo='skip'
    ))

    # Add simulation start line using shapes instead of add_vline
    fig.add_shape(
        type="line",
        x0=recent_historical['period'].max(),
        x1=recent_historical['period'].max(),
        y0=0,
        y1=1,
        yref="paper",
        line=dict(color="green", width=2, dash="dash"),
    )

    # Add annotation for the vertical line
    fig.add_annotation(
        x=recent_historical['period'].max(),
        y=1,
        yref="paper",
        text="Simulation Start",
        showarrow=False,
        textangle=0,
        xanchor="left",
        yanchor="bottom"
    )

    # Configure layout
    fig.update_layout(
        title=f"Supply Chain Digital Twin: {sim_duration}-Week Projection",
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
            x=1
        )
    )

    # Set axis ranges using proper timestamp handling
    fig.update_xaxes(
        range=[historical_cutoff, sim_results['period'].max() + pd.Timedelta(weeks=4)],
        tickformat="%b %Y"
    )

    # Auto-scale y-axis with padding
    y_min = min(sim_results['inventory'].min(), recent_historical['inventory'].min()) * 0.9
    y_max = max(sim_results['inventory'].max(), recent_historical['inventory'].max()) * 1.1
    fig.update_yaxes(
        range=[y_min, y_max],
        tickformat=",d"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Add scenario description
    scenario_desc = {
        "+30% Exports": "Increased global demand drives exports up 30%, rapidly depleting inventories.",
        "+15% Refining": "Domestic refining demand increases 15% during summer driving season.",
        "Normal": "Baseline scenario with typical seasonal patterns."
    }
    st.info(f"**Scenario:** {scenario_desc.get(demand_spike, 'Custom scenario')}")

    # ================== IMPACT ANALYSIS SECTION ==================
    st.subheader("Business Impact Analysis")
    impact_cols = st.columns(3)

    with impact_cols[0]:
        start_inv = recent_historical['inventory'].iloc[-1]
        end_inv = sim_results['inventory'].iloc[-1]
        pct_change = ((end_inv - start_inv) / start_inv) * 100
        
        st.metric(
            "Projected Inventory Change",
            f"{pct_change:.1f}%",
            delta=f"{end_inv - start_inv:,.0f} barrels",
            delta_color="inverse"
        )

    with impact_cols[1]:
        weeks_below = (sim_results['inventory'] < start_inv * 0.8).sum()
        st.metric(
            "Supply Risk",
            f"{weeks_below} weeks below 80% capacity" if weeks_below > 0 else "Low Risk",
            delta=f"{weeks_below} weeks" if weeks_below > 0 else "Stable",
            delta_color="inverse"
        )

    with impact_cols[2]:
        recovery_week = 0
        for i, row in sim_results.iterrows():
            if row['inventory'] >= start_inv:
                recovery_week = i + 1
                break
        
        st.metric(
            "Recovery Timeline",
            f"{recovery_week} weeks" if recovery_week > 0 else "No recovery needed",
            delta=f"{recovery_week} weeks" if recovery_week > 0 else "Stable",
            delta_color="inverse"
        )

    # Optional: Data Table View
    with st.expander("View Detailed Simulation Data"):
        st.dataframe(
            sim_results.style.format({
                'inventory': '{:,.0f}',
            }),
            use_container_width=True
        )

# Entry point
if __name__ == "__main__":
    main()
