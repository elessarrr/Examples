import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Optional, List

# Error handling decorator
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

@handle_exceptions
def display_key_metrics(latest_data: pd.DataFrame, price_data: Optional[pd.DataFrame] = None) -> None:
    """Display key metrics in the dashboard"""
    try:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            try:
                # Get the latest date from the data
                latest_date = latest_data['period'].max()
                # Filter data for U.S. region and the latest date
                us_data = latest_data[(latest_data['region'] == 'U.S.') & (latest_data['period'] == latest_date)]
                if not us_data.empty:
                    inv_val = us_data.iloc[0]['inventory']
                    st.metric('Latest Inventory (U.S.)', f'{float(inv_val):,.1f} Million BBL')
                else:
                    st.metric('Latest Inventory (U.S.)', 'Data unavailable')
            except Exception as e:
                st.error(f'Inventory error: {str(e)}')
        with col2:
            try:
                latest_date = latest_data['period'].max()
                report_date = latest_date.strftime('%Y-%m-%d')
                st.metric('Report Date', report_date)
            except Exception as e:
                st.error(f'Date error: {str(e)}')
        with col3:
            st.metric('Data Frequency', 'Weekly')
        with col4:
            try:
                if price_data is not None and not price_data.empty:
                    latest_date = latest_data['period'].max()  # Get latest inventory date
                    # Find the exact matching price for the report date
                    matching_price = price_data[price_data['period'] == latest_date]
                    if not matching_price.empty:
                        latest_price = matching_price.iloc[0]['price']
                        st.metric('Latest WTI Price', f'${float(latest_price):.2f} per BBL')
                    else:
                        st.metric('Latest WTI Price', 'Price not available for report date')
                else:
                    st.metric('Latest WTI Price', 'Data unavailable')
            except Exception as e:
                st.error(f'Price error: {str(e)}')
    except Exception as e:
        st.error(f'Error displaying metrics: {str(e)}')

@handle_exceptions
def display_scenario_controls() -> Dict:
    """Display and handle simulation scenario controls"""
    st.sidebar.header("Simulation Parameters")
    return {
        'sim_duration': st.sidebar.slider("Simulation Duration (weeks)", 4, 52, 12),
        'prod_cut': st.sidebar.checkbox("Production Cut Scenario", False),
        'demand_spike': st.sidebar.checkbox("Demand Spike Scenario", False),
        'spr_release': st.sidebar.checkbox("Strategic Reserve Release", False)
    }

@handle_exceptions
def display_region_selector(regions: List[str]) -> str:
    """Display PADD region selector with map"""
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

    st.sidebar.header("Filter Options")
    return st.sidebar.selectbox(
        "Select PADD Region:",
        options=regions,
        index=regions.index("PADD 2") if "PADD 2" in regions else 0,
        help="Select a region to analyze"
    )

@handle_exceptions
def plot_inventory_trends(df: pd.DataFrame, price_data: Optional[pd.DataFrame] = None) -> None:
    """Create and display inventory trend plots with optional price data"""
    try:
        st.subheader("Crude Oil Inventory and Price Analysis")
        
        # Create figure with subplots if price data is available
        if price_data is not None and not price_data.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                               subplot_titles=("Crude Oil Inventory Forecast", "WTI Crude Oil Price"))
        else:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Plot inventory data
        colors = {"Historical": "#1f77b4", "Trendline": "#2ca02c", "Simulated": "#ff0000"}
        line_styles = {"Historical": "solid", "Trendline": "dash", "Simulated": "solid"}
        
        # Create lookup dictionaries for price and inventory data if price data exists
        if price_data is not None and not price_data.empty:
            price_dict = dict(zip(price_data['period'], price_data['price']))
            inventory_dict = dict(zip(df['period'], df['inventory']))
        
        for data_type in ["Historical", "Trendline", "Simulated"]:
            mask = df["type"] == data_type
            if any(mask):
                data = df[mask]
                if price_data is not None and not price_data.empty:
                    price_data_points = [price_dict.get(date, None) for date in data['period']]
                    fig.add_trace(
                        go.Scatter(
                            x=data["period"],
                            y=data["inventory"],
                            name=f"{data_type} Inventory",
                            line=dict(color=colors[data_type], dash=line_styles[data_type]),
                            customdata=price_data_points,
                            hovertemplate='%{x|%Y-%m-%d}<br>Inventory: %{y:,.0f} Million BBL<br>Price: $%{customdata:.2f} per BBL<extra></extra>'
                        ),
                        row=1, col=1
                    )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=data["period"],
                            y=data["inventory"],
                            name=data_type,
                            line=dict(color=colors[data_type], dash=line_styles[data_type]),
                            mode="lines"
                        )
                    )
        
        # Add price trace if price data is available
        if price_data is not None and not price_data.empty:
            inventory_data_points = [inventory_dict.get(date, None) for date in price_data['period']]
            fig.add_trace(
                go.Scatter(
                    x=price_data['period'],
                    y=price_data['price'],
                    name='WTI Crude Oil Price',
                    line=dict(color='green', width=2),
                    customdata=inventory_data_points,
                    hovertemplate='%{x|%Y-%m-%d}<br>Price: $%{y:.2f} per BBL<br>Inventory: %{customdata:,.0f} Million BBL<extra></extra>'
                ),
                row=2, col=1
            )
            
            # Update axes labels and layout
            fig.update_yaxes(title_text="Inventory (Million Barrels)", row=1, col=1)
            fig.update_yaxes(
                title_text="Price ($ per Barrel)",
                row=2,
                col=1,
                tickformat="$.2f"
            )
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_layout(
                height=800,
                showlegend=True,
                hovermode='x unified'
            )
        else:
            # Update layout for single plot
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Inventory (Million Barrels)",
                hovermode="x unified",
                showlegend=True,
                height=600
            )

        # Display the plot
        st.plotly_chart(fig, use_container_width=True)

        # Add risk gauge visualization if we have simulation results
        if 'Simulated' in df['type'].values:
            display_risk_gauge(df)
            display_scenario_impact(df)

    except Exception as e:
        st.error(f"Error creating plot: {str(e)}")

@handle_exceptions
def display_risk_gauge(df: pd.DataFrame) -> None:
    """Display risk gauge visualization based on days of supply"""
    try:
        # Get the last simulated inventory value
        sim_data = df[df['type'] == 'Simulated']
        if not sim_data.empty:
            end_inventory = float(sim_data['inventory'].iloc[-1])
        else:
            # If no simulation data, use latest historical value
            hist_data = df[df['type'] == 'Historical']
            end_inventory = float(hist_data['inventory'].iloc[-1])

        # Calculate days of supply
        daily_consumption = 5000  # Typical regional consumption
        days_of_supply = end_inventory / daily_consumption

        # Create gauge visualization
        gauge_col, text_col = st.columns([0.6, 0.4])

        with gauge_col:
            # Create gauge figure
            fig_gauge = go.Figure()

            # Calculate gauge value and color
            if days_of_supply < 15:
                color = "red"
                risk_level = "Critical"
                risk_message = "Immediate action required. Critical supply shortage risk."
            elif days_of_supply < 25:
                color = "orange"
                risk_level = "Warning"
                risk_message = "Supply levels below comfort zone. Consider increasing inventory."
            elif days_of_supply < 45:
                color = "lightgreen"
                risk_level = "Normal"
                risk_message = "Supply levels within acceptable range."
            else:
                color = "green"
                risk_level = "Optimal"
                risk_message = "Healthy supply buffer maintained."

            # Add gauge trace
            fig_gauge.add_trace(go.Indicator(
                mode="gauge+number+delta",
                value=days_of_supply,
                domain={'x': [0, 1], 'y': [0, 1]},
                delta={'reference': 30},
                gauge={
                    'axis': {'range': [0, 60], 'tickwidth': 1},
                    'bar': {'color': color},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 15], 'color': "lightgray"},
                        {'range': [15, 25], 'color': "lightgray"},
                        {'range': [25, 45], 'color': "lightgray"},
                        {'range': [45, 60], 'color': "lightgray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 30
                    }
                },
                title={'text': "Days of Supply", 'font': {'size': 24}}
            ))

            fig_gauge.update_layout(
                height=300,
                margin=dict(l=30, r=30, t=30, b=30)
            )

            st.plotly_chart(fig_gauge, use_container_width=True)

        with text_col:
            st.markdown(f"""
            ### Supply Risk Level: {risk_level}
            {risk_message}

            **Current Status:**
            - Days of Supply: {days_of_supply:.1f} days
            - Inventory Level: {end_inventory:,.0f} Million BBL
            """)

    except Exception as e:
        st.error(f"Error creating risk gauge: {str(e)}")

@handle_exceptions
def display_scenario_impact(df: pd.DataFrame) -> None:
    """Display scenario impact analysis"""
    try:
        st.markdown("""
        <h2 style="font-size: 28px; margin-bottom: 16px;">Scenario Impact Analysis</h2>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <h4 style="font-size: 18px; margin-bottom: 10px;">Assumptions Made for Scenarios:</h4>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        - Base case assumes a natural weekly decline of 5,000 barrels in inventory levels
        - __Production cuts__ reduce available supply by 150%, simulating severe disruption scenarios
        - __Demand spikes__ double the rate of inventory drawdown, reflecting extreme market conditions
        - __Strategic Reserve__ releases add 5,000 barrels per week to available supply
        """)

        if 'Historical' in df['type'].values and 'Simulated' in df['type'].values:
            try:
                hist_data = df[df['type'] == 'Historical']
                sim_data = df[df['type'] == 'Simulated']
                
                end_inventory = float(sim_data['inventory'].iloc[-1])
                start_inventory = float(hist_data['inventory'].iloc[-1])
                inventory_change = end_inventory - start_inventory
                
                start_date = hist_data['period'].iloc[-1].strftime('%Y-%m-%d')
                end_date = sim_data['period'].iloc[-1].strftime('%Y-%m-%d')
                
                st.markdown(f"""
                ### Projected Impact (for Scenarios):
                - Starting Inventory ({start_date}): {start_inventory:,.0f} Million BBL
                - Ending Inventory ({end_date}): {end_inventory:,.0f} Million BBL
                - Net Change: {inventory_change:,.0f} Million BBL ({(inventory_change/start_inventory)*100:.1f}%)
                """)
                
                # Business Implications section
                st.markdown("""
                <h2 style="font-size: 28px; margin-bottom: 16px;">Business Implications</h2>
                """, unsafe_allow_html=True)

                # Calculate working capital impact
                avg_oil_price = 75.0  # Use a reasonable current price
                working_capital_impact = inventory_change * avg_oil_price * 1000  # Convert to dollars
                
                # Calculate storage cost impact (assuming $0.35/bbl/month storage cost)
                monthly_storage_cost = 0.35
                storage_cost_impact = inventory_change * monthly_storage_cost * 3  # 3-month horizon
                
                st.markdown(f"""
                ### Financial Implications:
                - **Working Capital Impact**: ${working_capital_impact:,.0f} {' freed up' if inventory_change < 0 else ' additional required'}
                - **Quarterly Storage Cost Impact**: ${abs(storage_cost_impact):,.0f} {' saved' if inventory_change < 0 else ' increased'}
                - **Supply Risk**: {'⚠️ High' if end_inventory < start_inventory * 0.8 else '✅ Managed'}
                
                ### Recommended Actions:
                {'- Consider hedging strategies to lock in favorable prices' if working_capital_impact < 0 else 
                 '- Review capital allocation for increased inventory requirements'}
                {'- Evaluate storage capacity constraints and contract terms' if inventory_change > 0 else
                 '- Assess supplier reliability with lower inventory buffers'}
                """)
                
            except Exception as e:
                st.error(f"Error calculating impact: {str(e)}")

    except Exception as e:
        st.error(f"Error displaying scenario impact: {str(e)}")