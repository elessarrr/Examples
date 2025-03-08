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
except Exception as e:  # ← REQUIRED ERROR HANDLING
    st.error(f"Page configuration error: {str(e)}")

def run_simulation(input_df, params):
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
                demand_factor = 1.3  # 30% increase
                weekly_change = -15000  # Baseline weekly decrease
            elif params['demand_spike'] == "+15% Refining":
                demand_factor = 1.15  # 15% increase
                weekly_change = -10000  # Moderate weekly decrease
            else:
                demand_factor = 1.0
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
            # crude_oil_digital_twin_app.py

# Now define the decorator
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

#cahced download function for the EIA map
@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_padd_map(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.content
    except Exception as e:
        st.error(f"Failed to load PADD map: {str(e)}")
        return None

# Then modify the image section:
        map_content = get_padd_map(padd_map_url)
        if map_content:
            st.image(
                map_content,
                use_container_width=True,  # Updated parameter here 
                caption="Source: U.S. Energy Information Administration (EIA)",
                output_format="PNG"
            )

# Add this ABOVE the main() function
@handle_exceptions
@st.cache_data
def run_simulation(input_df, params):
    """
    Enhanced simulation with better parameter response
    Logic matches realistic crude oil market dynamics
    """
    # Baseline values from historical data
    baseline = input_df['inventory'].iloc[-1]
    last_date = input_df['period'].iloc[-1]
    
    # Scenario setup
    simulations = []
    current_inventory = baseline
    
    for week in range(params['sim_duration']):
        # Production impact
        if params['prod_cut']:
            production = baseline * 0.35  # 65% Gulf Coast cut
        else:
            production = baseline * 0.95  # Normal 5% decline
        
        # Demand impact 
        if params['demand_spike'] == "+15% Refining":
            consumption = production * 1.15
        elif params['demand_spike'] == "+30% Exports":
            consumption = production * 1.30
        else:
            consumption = production * 0.98  # Normal decline
            
        # SPR release impact
        if params['spr_release']:
            current_inventory += 5000  # 5M barrel release/week
            
        # Calculate net change
        inventory_change = production - consumption
        current_inventory += inventory_change
        
        simulations.append({
            "period": last_date + pd.DateOffset(weeks=week+1),
            "inventory": current_inventory,
            "scenario": params['demand_spike']
        })
    
    return pd.DataFrame(simulations)
    
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

    # Add PADD map visualization section
    #updated image handling w container width
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
                use_container_width=True,  # Updated parameter
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

    
    # ================== SIMULATION SECTION ==================
    st.header("🧪 Supply Chain Simulation Engine")
    
    # Initialize simulation results with fallback
    sim_results = None
    
        # Parameter collection 
    with st.expander("⚙️ Configure Simulation", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            sim_weeks = st.slider("Forecast Horizon (weeks)", 4, 26, 8)
            disruption = st.checkbox("Gulf Coast Storm Scenario")
        with col2:
            demand_change = st.slider("Demand Change (%)", -30, 30, 0)
            spr_release = st.checkbox("SPR Release (5M bbl/week)")

    
    with st.expander("⚙️ Simulation Parameters", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Define simulation duration
            sim_duration = st.slider(
                "Simulation Duration (weeks)", 
                min_value=1, 
                max_value=52, 
                value=8,
                help="Number of weeks to simulate into the future"
            )
            
        with col2:
            prod_cut = st.checkbox(
                "PADD 3 Production Disruption (-65%)", 
                help="Simulate Gulf Coast storm impacts"
            )
            spr_release = st.checkbox(
                "SPR Release (5M bbl/week)", 
                help="Strategic Petroleum Reserve activation"
            )

    # Define demand spike options
    demand_spike = st.selectbox(
        "Demand Scenario",
        options=["Normal", "+15% Refining", "+30% Exports"],
        index=0
    )

    # Package parameters
    sim_params = {
        "sim_duration": sim_duration,  # Now properly defined
        "prod_cut": prod_cut,
        "demand_spike": demand_spike,
        "spr_release": spr_release
    }

    # Validate parameters before execution
    required_params = ["sim_duration", "prod_cut", "demand_spike", "spr_release"]
    if not all(key in sim_params for key in required_params):
        st.error("Missing critical simulation parameters!")
        st.stop()

    # Execute simulation with validated parameters
    try:
        sim_results = run_simulation(
            data["analysis_data"], 
            sim_params  # Now contains sim_duration
        )
    except KeyError as e:
        st.error(f"Missing required data column: {str(e)}")
        st.stop()
                
    except Exception as e:
        st.error(f"Simulation failed: {str(e)}")
        st.stop()

    # ================== VISUALIZATION SECTION ================== 
    st.subheader("Simulation Output")
    
    if sim_results is not None:
        try:
            fig = go.Figure()
            
            # Simulation trace
            fig.add_trace(go.Scatter(
                x=sim_results['period'],
                y=sim_results['inventory'],
                name='Simulated',
                line=dict(color='red')
            ))
            
            # Historical trace
            fig.add_trace(go.Scatter(
                x=data["analysis_data"]['period'],
                y=data["analysis_data"]['inventory'],
                name='Historical',
                line=dict(color='blue', dash='dot')
            ))
            
            fig.update_layout(
                title="Inventory Simulation vs Historical",
                height=500,
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)
            
        except KeyError as e:
            st.error(f"Missing data column: {str(e)}")
    else:
        st.warning("No simulation results to display")

if __name__ == "__main__":
    main()

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

# VISUALIZATION IMPROVEMENTS
# Replace your current visualization code with this:

# Create enhanced visualization
st.subheader("Inventory Simulation vs Historical")

# Filter historical data to show only recent periods
historical_cutoff = sim_results['period'].min() - timedelta(weeks=26)
recent_historical = data["analysis_data"][
    data["analysis_data"]['period'] >= historical_cutoff
]

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

# Add historical trace with reduced emphasis
fig.add_trace(go.Scatter(
    x=recent_historical['period'],
    y=recent_historical['inventory'],
    mode='lines',
    name='Historical',
    line=dict(color='blue', width=2, dash='dot'),
    hovertemplate='<b>%{x|%b %d, %Y}</b><br>Inventory: %{y:,.0f} barrels<extra></extra>'
))

# Add reference point for today
fig.add_trace(go.Scatter(
    x=[recent_historical['period'].max()],
    y=[recent_historical['inventory'].iloc[-1]],
    mode='markers',
    marker=dict(color='green', size=12, symbol='star'),
    name='Current',
    hoverinfo='skip'
))

# Add vertical line at simulation start
fig.add_vline(
    x=recent_historical['period'].max(), 
    line_width=2, 
    line_dash="dash", 
    line_color="green",
    annotation_text="Simulation Start",
    annotation_position="top right"
)

# Configure layout for maximum impact
fig.update_layout(
    title=f"Supply Chain Digital Twin: {params['sim_duration']}-Week Projection",
    xaxis_title="Date",
    yaxis_title="Inventory (Barrels)",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=600,
    template="plotly_white",
    hovermode="x unified"
)

# Focus x-axis on recent history + simulation period
fig.update_xaxes(
    range=[historical_cutoff, sim_results['period'].max() + timedelta(weeks=4)],
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

st.info(f"**Scenario:** {scenario_desc.get(params['demand_spike'], 'Custom scenario')}")

# Add impact summary
col1, col2 = st.columns(2)
with col1:
    start_inv = recent_historical['inventory'].iloc[-1]
    end_inv = sim_results['inventory'].iloc[-1]
    pct_change = ((end_inv - start_inv) / start_inv) * 100
    
    st.metric(
        "Projected Inventory Change", 
        f"{pct_change:.1f}%",
        delta=f"{end_inv - start_inv:,.0f} barrels",
        delta_color="inverse"  # Red for decreases
    )

with col2:
    weeks_below = (sim_results['inventory'] < start_inv * 0.8).sum()
    st.metric(
        "Supply Risk", 
        f"{weeks_below} weeks below 80% capacity" if weeks_below > 0 else "Low Risk",
        delta=f"{weeks_below} weeks" if weeks_below > 0 else "Stable",
        delta_color="inverse"
    )