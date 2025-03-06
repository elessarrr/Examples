import streamlit as st
import polars as pl
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Digital Twin: Crude Oil Inventory Analysis",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better aesthetics
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4e8cff;
        color: white;
    }
    h1, h2, h3 {
        color: #1E3A8A;
    }
    .metric-card {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 0 8px rgba(0, 0, 0, 0.1);
        padding: 15px;
        margin-bottom: 10px;
    }
    .insight-card {
        background-color: white;
        border-radius: 5px;
        box-shadow: 0 0 8px rgba(0, 0, 0, 0.1);
        padding: 20px;
        margin-bottom: 15px;
    }
    .stProgress .st-eb {
        background-color: #4e8cff;
    }
    .annotation {
        font-size: 0.9em;
        color: #555;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

# App Header
col1, col2 = st.columns([3, 1])
with col1:
    st.title("🛢️ Digital Twin: Crude Oil Inventory Dynamics")
    st.markdown("#### Real-time monitoring, forecasting, and strategic insights for operational excellence")

with col2:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/EIA_logo.svg/640px-EIA_logo.svg.png", width=100)
    st.markdown("<p class='annotation'>Data Source: U.S. Energy Information Administration</p>", unsafe_allow_html=True)

# Data Loading Function
@st.cache_data(ttl=3600)
def load_crude_oil_data():
    """
    Load crude oil stock data from EIA API with caching
    Returns processed dataframes for analysis
    """
    try:
        api_key = 'nsH8duWHIP4GA3eL1RgSoWh8my1gGOBpfzqyIeKp'
        url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?frequency=weekly&data[0]=value&facets[product][]=EPC0&start=2016-01-04&end=2025-02-04&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=5000&api_key={api_key}"
        
        with st.spinner("Fetching latest crude oil data from EIA..."):
            response = requests.get(url)
            if response.status_code != 200:
                st.error(f"API Error: {response.status_code}")
                return None
                
            data = response.json()
            records = data["response"]["data"]
            
            # Convert to Polars DataFrame
            df = pl.DataFrame(records)
            
            # Process data for analysis
            df = df.with_columns(pl.col("value").cast(pl.Float64))
            
            # Filter out NA and prepare regional data
            df_regional = df.filter(pl.col("area-name") != "NA")
            
            # Create datetime column
            df_regional = df_regional.with_columns(
                pl.col("period").str.to_datetime("%Y-%m-%d").alias("date")
            )
            
            # Extract time components
            df_regional = df_regional.with_columns([
                pl.col("date").dt.year().alias("year"),
                pl.col("date").dt.month().alias("month"),
                pl.col("date").dt.month_name().alias("month_name"),
                pl.col("date").dt.quarter().alias("quarter")
            ])
            
            # Create bimonthly grouping
            df_regional = df_regional.with_columns(
                ((pl.col("month") - 1) // 2 + 1).alias("bimonthly_period")
            )
            
            # Create year-bimonthly identifier
            df_regional = df_regional.with_columns(
                (pl.col("year") * 10 + pl.col("bimonthly_period")).alias("year_bimonthly")
            )
            
            # Group by bimonthly period and area-name
            bimonthly_df = df_regional.group_by(["year_bimonthly", "area-name"]).agg([
                pl.col("value").mean().alias("avg_stocks"),
                pl.col("value").std().alias("std_dev"),
                pl.col("date").min().alias("start_date"),
                pl.col("date").max().alias("end_date"),
                pl.col("year").first().alias("year"),
                pl.col("bimonthly_period").first().alias("bimonth")
            ])
            
            # Sort by date and area
            bimonthly_df = bimonthly_df.sort(["start_date", "area-name"])
            
            # Calculate moving averages for trend analysis
            regional_pivoted = df_regional.pivot(
                values="value",
                index="date",
                columns="area-name"
            )
            
            # Convert to pandas for rolling calculations
            regional_pivoted_pd = regional_pivoted.to_pandas()
            
            # Drop U.S. for district level analysis
            us_data = df_regional.filter(pl.col("area-name") == "U.S.")
            district_data = df_regional.filter(pl.col("area-name") != "U.S.")
            
            return {
                'raw_df': df,
                'regional_df': df_regional,
                'bimonthly_df': bimonthly_df,
                'pivoted_df': regional_pivoted,
                'us_data': us_data,
                'district_data': district_data
            }
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# Load data
data_dict = load_crude_oil_data()

if data_dict:
    df = data_dict['raw_df']
    df_regional = data_dict['regional_df'] 
    bimonthly_df = data_dict['bimonthly_df']
    us_data = data_dict['us_data']
    district_data = data_dict['district_data']

    # Create tabs for different app sections
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Advanced Analytics", "🧠 Digital Twin Simulation", "📈 Business Impact"])

    #------------------------------------------------#
    # TAB 1: Main Dashboard
    #------------------------------------------------#
    with tab1:
        # Top level metrics
        st.subheader("Key Performance Indicators")
        
        # Calculate key metrics
        latest_date = df_regional["date"].max()
        previous_year = latest_date - timedelta(days=365)
        
        latest_us_stock = us_data.filter(pl.col("date") == latest_date)["value"].item() if len(us_data.filter(pl.col("date") == latest_date)) > 0 else 0
        year_ago_us_stock = us_data.filter(pl.col("date") >= previous_year)["value"].head(1).item() if len(us_data.filter(pl.col("date") >= previous_year)) > 0 else 0
        
        yoy_change = ((latest_us_stock - year_ago_us_stock) / year_ago_us_stock) * 100 if year_ago_us_stock != 0 else 0
        
        # Display metrics in cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Current U.S. Crude Stock", f"{latest_us_stock:,.0f} k barrels", 
                      f"{yoy_change:.1f}% YoY")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            # Calculate 5-year average
            five_years_ago = latest_date - timedelta(days=5*365)
            five_year_avg = us_data.filter(pl.col("date") >= five_years_ago)["value"].mean()
            vs_5yr_avg = ((latest_us_stock - five_year_avg) / five_year_avg) * 100
            
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("vs. 5-Year Average", f"{five_year_avg:,.0f} k barrels", 
                      f"{vs_5yr_avg:.1f}%")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col3:
            # Calculate inventory days
            # Assumption: Average daily consumption is ~19.78 million barrels (adjust based on actual data)
            avg_daily_consumption = 19780  # in thousand barrels
            days_supply = latest_us_stock / avg_daily_consumption
            
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Days of Supply", f"{days_supply:.1f} days", 
                      f"{((days_supply/30)-1)*100:.1f}% of target")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col4:
            # Calculate storage utilization
            # Assumption: Total U.S. storage capacity is ~650 million barrels (adjust as needed)
            total_capacity = 650000  # in thousand barrels
            utilization = (latest_us_stock / total_capacity) * 100
            
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Storage Utilization", f"{utilization:.1f}%", 
                      f"{utilization - 75:.1f}% from optimal")
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Main visualization
        st.subheader("Regional Crude Oil Inventory Trends")
        
        # Sidebar filters
        st.sidebar.header("Dashboard Controls")
        
        available_districts = district_data["area-name"].unique()
        default_districts = available_districts
        
        selected_districts = st.sidebar.multiselect(
            "Select PAD Districts:", 
            options=available_districts,
            default=default_districts
        )
        
        # Date range
        date_min = district_data["date"].min()
        date_max = district_data["date"].max()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            [date_max - timedelta(days=730), date_max],
            min_value=date_min,
            max_value=date_max
        )
        
        # Apply filters
        if len(date_range) == 2:
            start_date, end_date = date_range
            start_date = datetime.combine(start_date, datetime.min.time())
            end_date = datetime.combine(end_date, datetime.min.time())
            
            filtered_data = district_data.filter(
                (pl.col("date") >= start_date) & 
                (pl.col("date") <= end_date) &
                (pl.col("area-name").is_in(selected_districts))
            )
        else:
            filtered_data = district_data.filter(
                pl.col("area-name").is_in(selected_districts)
            )
        
        # Visualization options
        viz_type = st.sidebar.radio(
            "Visualization Type:",
            ["Interactive Line Chart", "Area Chart", "Bar Chart", "Heatmap"]
        )
        
        # Aggregation period
        agg_period = st.sidebar.radio(
            "Aggregation Period:",
            ["Weekly", "Monthly", "Quarterly", "Bimonthly"]
        )
        
        # Normalize data option
        normalize = st.sidebar.checkbox("Normalize Data (% Change from Start)", value=False)
        
        # Process based on aggregation period
        if agg_period == "Weekly":
            plot_data = filtered_data
            x_col = "date"
            
        elif agg_period == "Monthly":
            plot_data = filtered_data.group_by(["year", "month", "area-name"]).agg([
                pl.col("value").mean().alias("value"),
                pl.col("date").min().alias("date")
            ]).sort(["date", "area-name"])
            x_col = "date"
            
        elif agg_period == "Quarterly":
            plot_data = filtered_data.group_by(["year", "quarter", "area-name"]).agg([
                pl.col("value").mean().alias("value"),
                pl.col("date").min().alias("date")
            ]).sort(["date", "area-name"])
            x_col = "date"
            
        else:  # Bimonthly
            plot_data = filtered_data.group_by(["year", "bimonthly_period", "area-name"]).agg([
                pl.col("value").mean().alias("value"),
                pl.col("date").min().alias("date")
            ]).sort(["date", "area-name"])
            x_col = "date"
        
        # Normalize data if requested
        if normalize:
            # Convert to pandas for easier normalization
            plot_data_pd = plot_data.to_pandas()
            
            # Group by area-name and normalize
            normalized_dfs = []
            for area in plot_data_pd['area-name'].unique():
                area_data = plot_data_pd[plot_data_pd['area-name'] == area].copy()
                base_value = area_data.iloc[0]['value']
                area_data['value'] = ((area_data['value'] - base_value) / base_value) * 100
                normalized_dfs.append(area_data)
            
            plot_data_pd = pd.concat(normalized_dfs)
            y_axis_label = "% Change from Base Period"
        else:
            plot_data_pd = plot_data.to_pandas()
            y_axis_label = "Stock Level (Thousand Barrels)"
        
        # Create the selected visualization
        if viz_type == "Interactive Line Chart":
            fig = px.line(
                plot_data_pd, 
                x=x_col, 
                y="value", 
                color="area-name",
                labels={"value": y_axis_label, "date": "Date", "area-name": "PAD District"},
                title="Crude Oil Stocks by PAD District Over Time",
                hover_data=["area-name", "value"],
                markers=True,
                template="plotly_white"
            )
            
            # Add trendlines
            for area in plot_data_pd['area-name'].unique():
                area_data = plot_data_pd[plot_data_pd['area-name'] == area]
                fig.add_trace(
                    go.Scatter(
                        x=area_data[x_col],
                        y=area_data['value'].rolling(5).mean(),
                        mode='lines',
                        line=dict(width=1, dash='dash'),
                        showlegend=False,
                        opacity=0.7,
                        hoverinfo='skip'
                    )
                )
            
            fig.update_layout(
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(tickangle=-45),
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        elif viz_type == "Area Chart":
            fig = px.area(
                plot_data_pd, 
                x=x_col, 
                y="value", 
                color="area-name",
                labels={"value": y_axis_label, "date": "Date", "area-name": "PAD District"},
                title="Crude Oil Stocks Distribution by PAD District",
                template="plotly_white"
            )
            
            fig.update_layout(
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(tickangle=-45),
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        elif viz_type == "Bar Chart":
            fig = px.bar(
                plot_data_pd, 
                x=x_col, 
                y="value", 
                color="area-name",
                barmode="group",
                labels={"value": y_axis_label, "date": "Date", "area-name": "PAD District"},
                title="Comparative Crude Oil Stocks by PAD District",
                template="plotly_white"
            )
            
            fig.update_layout(
                height=600,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(tickangle=-45, tickmode='auto', nticks=20),
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:  # Heatmap
            # Prepare data for heatmap
            heatmap_data = plot_data_pd.pivot_table(
                values="value", 
                index="area-name", 
                columns=x_col,
                fill_value=0
            )
            
            fig = px.imshow(
                heatmap_data,
                labels=dict(x="Date", y="PAD District", color=y_axis_label),
                title="Crude Oil Stock Levels Heat Map",
                color_continuous_scale="Blues",
                aspect="auto"
            )
            
            fig.update_layout(
                height=500,
                xaxis=dict(tickangle=-45, tickmode='auto', nticks=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Insights and Analysis Section
        st.subheader("Key Insights")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown("##### Inventory Volatility Analysis")
            
            # Calculate volatility for each region
            volatility_data = []
            for area in selected_districts:
                area_data = filtered_data.filter(pl.col("area-name") == area)
                if len(area_data) > 0:
                    std_dev = area_data["value"].std()
                    mean = area_data["value"].mean()
                    cov = (std_dev / mean) * 100  # Coefficient of variation
                    
                    volatility_data.append({
                        "area": area,
                        "mean": mean,
                        "std_dev": std_dev,
                        "cov": cov
                    })
            
            if volatility_data:
                volatility_df = pd.DataFrame(volatility_data)
                
                # Find most and least volatile regions
                most_volatile = volatility_df.loc[volatility_df['cov'].idxmax()]
                least_volatile = volatility_df.loc[volatility_df['cov'].idxmin()]
                
                # Create comparison chart
                fig = px.bar(
                    volatility_df,
                    x="area",
                    y="cov",
                    color="cov",
                    labels={"cov": "Coefficient of Variation (%)", "area": "PAD District"},
                    title="Inventory Volatility by Region",
                    color_continuous_scale="Viridis"
                )
                
                fig.update_layout(height=300, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown(f"""
                - **Most volatile region**: {most_volatile['area']} (±{most_volatile['cov']:.1f}%)
                - **Most stable region**: {least_volatile['area']} (±{least_volatile['cov']:.1f}%)
                - Volatility indicates potential supply chain challenges or demand fluctuations
                """
                ")
            else:
                st.write("Insufficient data for volatility analysis")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown("##### Seasonal Patterns")
            
            # Analyze seasonal patterns
            seasonal_data = filtered_data.group_by(["month", "area-name"]).agg([
                pl.col("value").mean().alias("avg_value")
            ]).sort(["month", "area-name"])
            
            seasonal_pd = seasonal_data.to_pandas()
            
            fig = px.line(
                seasonal_pd, 
                x="month", 
                y="avg_value", 
                color="area-name",
                markers=True,
                labels={"avg_value": "Average Stock Level", "month": "Month", "area-name": "PAD District"},
                title="Seasonal Stock Level Patterns",
                template="plotly_white"
            )
            
            fig.update_layout(
                height=300,
                xaxis=dict(tickmode='array', tickvals=list(range(1,13)), 
                           ticktext=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Identify peak and trough months
            overall_seasonal = filtered_data.group_by(["month"]).agg([
                pl.col("value").mean().alias("avg_value")
            ]).sort("month")
            
            peak_month = overall_seasonal.filter(pl.col("avg_value") == overall_seasonal["avg_value"].max())["month"].item()
            trough_month = overall_seasonal.filter(pl.col("avg_value") == overall_seasonal["avg_value"].min())["month"].item()
            
            month_names = ['January', 'February', 'March', 'April', 'May', 'June', 
                          'July', 'August', 'September', 'October', 'November', 'December']
            
            st.markdown(f"""
            - **Peak inventory month**: {month_names[peak_month-1]}
            - **Lowest inventory month**: {month_names[trough_month-1]}
            - Seasonal patterns affect storage requirements and trading strategies
            """)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Additional insights row
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            st.markdown("##### Regional Distribution Analysis")
            
            # Latest distribution
            latest_period = filtered_data["date"].max()
            latest_distribution = filtered_data.filter(pl.col("date") == latest_period)
            
            if len(latest_distribution) > 0:
                latest_dist_pd = latest_distribution.to_pandas()
                
                fig = px.pie(
                    latest_dist_pd, 
                    values='value', 
                    names='area-name',
                    title=f"Current Crude Oil Distribution (as of {latest_period.date()})",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                # Calculate region with largest share
                largest_region = latest_dist_pd.loc[latest_dist_pd['value'].idxmax()]['area-name']
                largest_share = latest_dist_pd.loc[latest_dist_pd['value'].idxmax()]['value'] / latest_dist_pd['value'].sum() * 100
                
                st.markdown(f"""
                - **Largest inventory share**: {largest_region} ({largest_share:.1f}%)
                - Regional distribution affects pricing, logistics, and refining capacity utilization
                """)
            else:
                st.write("No data available for the latest period")
            
                            st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                st.markdown("##### Simulation Impact Analysis")
                
                # Calculate key metrics from simulation
                capacity_utilization = (final_inventory / max_capacity) * 100
                days_of_supply = final_inventory / (adj_refining * 7)  # Convert weekly to daily
                
                # Create metrics gauge charts
                fig = make_subplots(rows=2, cols=1, specs=[[{"type": "indicator"}], [{"type": "indicator"}]])
                
                fig.add_trace(
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=capacity_utilization,
                        title={"text": "Storage Utilization"},
                        delta={"reference": storage_capacity, "valueformat": ".1f"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 50], "color": "lightgreen"},
                                {"range": [50, 75], "color": "lightyellow"},
                                {"range": [75, 90], "color": "orange"},
                                {"range": [90, 100], "color": "red"}
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 95
                            }
                        }
                    ),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Indicator(
                        mode="gauge+number+delta",
                        value=days_of_supply,
                        title={"text": "Days of Supply"},
                        delta={"reference": 30, "valueformat": ".1f"},
                        gauge={
                            "axis": {"range": [0, 60]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 15], "color": "red"},
                                {"range": [15, 25], "color": "orange"},
                                {"range": [25, 35], "color": "lightyellow"},
                                {"range": [35, 60], "color": "lightgreen"}
                            ],
                            "threshold": {
                                "line": {"color": "green", "width": 4},
                                "thickness": 0.75,
                                "value": 30
                            }
                        }
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(height=450, margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Risk assessment
            st.markdown("#### Risk Assessment")
            
            # Define risk thresholds
            risk_factors = []
            
            # Check capacity risk
            if capacity_utilization > 90:
                risk_factors.append({
                    "risk": "Storage Capacity Constraint",
                    "level": "High",
                    "impact": "Potential forced production curtailment or discounted selling",
                    "mitigation": "Secure additional storage or accelerate downstream throughput"
                })
            elif capacity_utilization > 80:
                risk_factors.append({
                    "risk": "Storage Capacity Constraint",
                    "level": "Medium",
                    "impact": "Reduced operational flexibility and potential pricing pressure",
                    "mitigation": "Optimize inventory management and review storage contracts"
                })
            
            # Check supply risk
            if days_of_supply < 20:
                risk_factors.append({
                    "risk": "Supply Shortage",
                    "level": "High",
                    "impact": "Potential refinery slowdowns and higher input costs",
                    "mitigation": "Secure additional supply sources or reduce refinery throughput"
                })
            elif days_of_supply < 25:
                risk_factors.append({
                    "risk": "Supply Shortage",
                    "level": "Medium",
                    "impact": "Reduced operational flexibility and potential spot purchases",
                    "mitigation": "Review supply contracts and increase safety stocks"
                })
            
            # Check inventory change risk
            if abs(pct_change) > 15:
                risk_direction = "build-up" if pct_change > 0 else "drawdown"
                risk_factors.append({
                    "risk": f"Rapid Inventory {risk_direction.capitalize()}",
                    "level": "High",
                    "impact": f"Significant {'working capital increase' if pct_change > 0 else 'supply risk'} and potential market disruption",
                    "mitigation": f"{'Review production plans and storage strategy' if pct_change > 0 else 'Secure additional supply sources'}"
                })
            elif abs(pct_change) > 10:
                risk_direction = "build-up" if pct_change > 0 else "drawdown"
                risk_factors.append({
                    "risk": f"Moderate Inventory {risk_direction.capitalize()}",
                    "level": "Medium",
                    "impact": f"{'Increased working capital requirements' if pct_change > 0 else 'Tightening supply conditions'}",
                    "mitigation": f"{'Optimize cash conversion cycle' if pct_change > 0 else 'Review contingency supply options'}"
                })
            
            # Check refinery utilization risk
            if refinery_utilization < 75:
                risk_factors.append({
                    "risk": "Low Refinery Utilization",
                    "level": "Medium",
                    "impact": "Reduced throughput efficiency and higher unit costs",
                    "mitigation": "Evaluate temporary shutdowns or maintenance acceleration"
                })
            
            # If no risks identified, add a positive assessment
            if not risk_factors:
                risk_factors.append({
                    "risk": "Balanced Operations",
                    "level": "Low",
                    "impact": "Stable inventory levels and operational conditions",
                    "mitigation": "Continue regular monitoring and optimization"
                })
            
            # Display risk matrix
            if risk_factors:
                risk_df = pd.DataFrame(risk_factors)
                
                # Color-code risk levels
                def color_risk_level(val):
                    if val == 'High':
                        return 'background-color: #FFCCCC'
                    elif val == 'Medium':
                        return 'background-color: #FFFFCC'
                    else:
                        return 'background-color: #CCFFCC'
                
                # Apply styling
                styled_risk_df = risk_df.style.applymap(color_risk_level, subset=['level'])
                
                st.dataframe(styled_risk_df, hide_index=True, height=35+len(risk_factors)*35)
            
            # Summary and recommendations
            st.markdown("#### Digital Twin Insights")
            
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            
            # Overall direction
            direction = "increase" if pct_change > 0 else "decrease"
            
            st.markdown(f"""
            Based on the digital twin simulation over {sim_duration} weeks, the crude oil inventory in {selected_pad} is projected to **{direction} by {abs(pct_change):.1f}%** ({abs(net_change):.1f} thousand barrels) from the current level of {latest_value:.1f} thousand barrels.
            
            **Key Business Implications:**
            
            1. **Supply Chain Impact**: 
               - Projected storage utilization of {capacity_utilization:.1f}% {' (approaching capacity constraints)' if capacity_utilization > 75 else ''}
               - Estimated {days_of_supply:.1f} days of supply {' (below target levels)' if days_of_supply < 30 else ''}
            
            2. **Financial Implications**:
               - Working capital {' increase ' if pct_change > 0 else ' release '} of approximately ${abs(net_change) * 70 / 1000:.1f}M (assuming $70/bbl)
               - {'Potential storage cost increase' if pct_change > 0 else 'Potential lower unit storage costs'}
            
            3. **Operational Recommendations**:
            """)
            
            # Generate tailored recommendations based on simulation results
            recommendations = []
            
            if capacity_utilization > 85:
                recommendations.append("Evaluate additional storage options or strategic sales to prevent capacity constraints")
            
            if days_of_supply < 25:
                recommendations.append("Secure additional supply sources to maintain operational flexibility")
            elif days_of_supply > 40:
                recommendations.append("Consider optimizing working capital by reducing excess inventory")
            
            if refinery_utilization < 80:
                recommendations.append("Analyze refinery operations to improve utilization and throughput efficiency")
            
            if abs(pct_change) > 10:
                if pct_change > 0:
                    recommendations.append("Review cash flow projections to account for increased inventory working capital")
                else:
                    recommendations.append("Monitor inventory levels closely to ensure operational continuity")
            
            # If no specific recommendations, add a general one
            if not recommendations:
                recommendations.append("Maintain current operational strategy as inventory levels remain within optimal ranges")
            
            # Display recommendations
            for idx, rec in enumerate(recommendations):
                st.markdown(f"   - {rec}")
            
            st.markdown('</div>', unsafe_allow_html=True)

    #------------------------------------------------#
    # TAB 4: Business Impact
    #------------------------------------------------#
    with tab4:
        st.subheader("Business Impact & Executive Dashboard")
        st.markdown("""
        This section translates inventory dynamics into actionable business insights and financial metrics,
        demonstrating the strategic value of digital twin technology for decision-making.
        """)
        
        # Financial Impact Calculator
        st.markdown("#### Financial Impact Calculator")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            crude_price = st.number_input(
                "Current Crude Oil Price ($/bbl)",
                min_value=20.0,
                max_value=150.0,
                value=75.0,
                step=1.0
            )
            
            storage_cost = st.number_input(
                "Monthly Storage Cost ($/bbl)",
                min_value=0.1,
                max_value=2.0,
                value=0.35,
                step=0.05
            )
            
        with col2:
            carrying_cost = st.number_input(
                "Annual Inventory Carrying Cost (%)",
                min_value=5.0,
                max_value=25.0,
                value=12.0,
                step=0.5
            ) / 100  # Convert to decimal
            
            refining_margin = st.number_input(
                "Refining Margin ($/bbl)",
                min_value=1.0,
                max_value=30.0,
                value=9.5,
                step=0.5
            )
            
        with col3:
            price_volatility = st.number_input(
                "Expected Price Volatility (%)",
                min_value=5.0,
                max_value=50.0,
                value=15.0,
                step=1.0
            ) / 100  # Convert to decimal
            
            hedging_cost = st.number_input(
                "Hedging Cost ($/bbl)",
                min_value=0.1,
                max_value=5.0,
                value=1.2,
                step=0.1
            )
        
        # Select PAD district for analysis
        selected_pad_fin = st.selectbox(
            "Select PAD District for Analysis:",
            options=df_regional["area-name"].unique().sort(),
            index=list(df_regional["area-name"].unique().sort()).index("U.S.") if "U.S." in df_regional["area-name"].unique() else 0,
            key="financial_pad"
        )
        
        # Get data for selected PAD
        pad_fin_data = df_regional.filter(pl.col("area-name") == selected_pad_fin).sort("date")
        pad_fin_pd = pad_fin_data.to_pandas()
        
        if len(pad_fin_pd) > 0:
            # Get current inventory level
            current_inventory = pad_fin_pd['value'].iloc[-1]
            
            # Calculate financial metrics
            inventory_value = current_inventory * crude_price / 1000  # Convert to millions
            annual_carrying_cost = inventory_value * carrying_cost
            monthly_storage_cost = current_inventory * storage_cost / 1000  # Convert to millions
            
            # Calculate optimal inventory
            # Simple EOQ (Economic Order Quantity) model adapted for crude oil
            # Assumptions: demand is refinery throughput, ordering cost varies with price volatility
            avg_monthly_change = pad_fin_pd['value'].diff().abs().mean() * 4  # Estimate monthly throughput
            
            ordering_cost_factor = crude_price * price_volatility * 100  # Scale factor for ordering cost
            optimal_inventory = (2 * avg_monthly_change * ordering_cost_factor / (carrying_cost * crude_price)) ** 0.5
            
            # Calculate safety stock (simplified)
            volatility = pad_fin_pd['value'].rolling(window=12).std().iloc[-1] if len(pad_fin_pd) >= 12 else pad_fin_pd['value'].std()
            safety_factor = 1.96  # ~95% service level
            lead_time_weeks = 4  # Assumed lead time for new supplies
            safety_stock = safety_factor * volatility * (lead_time_weeks/52)**0.5
            
            # Calculate financial impact of inventory optimization
            current_days_supply = current_inventory / (avg_monthly_change / 30)
            optimal_days_supply = optimal_inventory / (avg_monthly_change / 30)
            target_inventory = optimal_inventory + safety_stock
            
            inventory_gap = current_inventory - target_inventory
            value_gap = inventory_gap * crude_price / 1000  # Convert to millions
            annual_cost_gap = value_gap * carrying_cost
            
            # Display financial metrics
            st.markdown("#### Current Inventory Financial Profile")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Inventory Value", f"${inventory_value:.1f}M")
                st.markdown('</div>', unsafe_allow_html=True)
                
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Annual Carrying Cost", f"${annual_carrying_cost:.1f}M")
                st.markdown('</div>', unsafe_allow_html=True)
                
            with col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Monthly Storage Cost", f"${monthly_storage_cost:.1f}M")
                st.markdown('</div>', unsafe_allow_html=True)
                
            with col4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Days of Supply", f"{current_days_supply:.1f} days")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Inventory optimization
            st.markdown("#### Inventory Optimization Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure()
                
                # Add current, optimal, and safety stock levels
                categories = ['Current Inventory', 'Optimal Inventory', 'Safety Stock', 'Target (Optimal + Safety)']
                values = [current_inventory, optimal_inventory, safety_stock, target_inventory]
                
                fig.add_trace(go.Bar(
                    x=categories,
                    y=values,
                    marker_color=['royalblue', 'green', 'orange', 'red']
                ))
                
                fig.update_layout(
                    title="Inventory Level Comparison",
                    xaxis_title="Inventory Component",
                    yaxis_title="Stock Level (Thousand Barrels)",
                    height=400,
                    template="plotly_white"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                # Create optimization insight card
                st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                st.markdown("##### Inventory Optimization Opportunity")
                
                # Determine if current inventory is above or below optimal
                if inventory_gap > 0:
                    optimization_direction = "reduction"
                    action_verb = "Release"
                else:
                    optimization_direction = "increase"
                    action_verb = "Invest"
                
                st.markdown(f"""
                Analysis indicates an inventory {optimization_direction} opportunity of **{abs(inventory_gap):,.0f} thousand barrels** ({abs(inventory_gap/current_inventory)*100:.1f}% of current level).
                
                **Financial Impact:**
                - {action_verb} **${abs(value_gap):.1f}M** in working capital
                - **${abs(annual_cost_gap):.1f}M** annual carrying cost {optimization_direction}
                - **${abs(monthly_storage_cost * inventory_gap/current_inventory):.2f}M** monthly storage cost {optimization_direction}
                
                **Operational Impact:**
                - Current days of supply: **{current_days_supply:.1f} days**
                - Optimal days of supply: **{optimal_days_supply:.1f} days**
                - Safety stock coverage: **{safety_stock/(avg_monthly_change/30):.1f} days**
                """)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Hedging and risk management
            st.markdown("#### Risk Management Strategy")
            
            # Calculate price risk exposure
            price_risk_exposure = current_inventory * crude_price * price_volatility / 1000  # Convert to millions
            
            # Calculate hedging costs
            full_hedge_cost = current_inventory * hedging_cost / 1000  # Convert to millions
            optimal_hedge_ratio = 0.75  # Simplification - typically 60-80% for crude oil
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Create price risk visualization
                fig = go.Figure()
                
                # Create price scenarios
                prices = [crude_price * (1 - 2*price_volatility), 
                         crude_price * (1 - price_volatility),
                         crude_price,
                         crude_price * (1 + price_volatility),
                         crude_price * (1 + 2*price_volatility)]
                
                scenarios = ['Severe Decline', 'Moderate Decline', 'Current Price', 'Moderate Increase', 'Significant Increase']
                
                # Calculate value at different price points
                values = [current_inventory * p / 1000 for p in prices]  # Convert to millions
                
                # Calculate hedged values (simplified)
                hedged_values = [
                    current_inventory * (optimal_hedge_ratio * crude_price + (1-optimal_hedge_ratio) * p) / 1000
                    for p in prices
                ]
                
                # Add traces
                fig.add_trace(go.Scatter(
                    x=scenarios,
                    y=values,
                    mode='lines+markers',
                    name='Unhedged Value',
                    line=dict(color='red')
                ))
                
                fig.add_trace(go.Scatter(
                    x=scenarios,
                    y=hedged_values,
                    mode='lines+markers',
                    name='Hedged Value',
                    line=dict(color='green')
                ))
                
                fig.update_layout(
                    title="Inventory Value at Different Price Scenarios",
                    xaxis_title="Price Scenario",
                    yaxis_title="Inventory Value ($M)",
                    height=400,
                    template="plotly_white"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            with col2:
                st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                st.markdown("##### Price Risk Exposure Analysis")
                
                st.markdown(f"""
                **Current Price Risk Exposure: ${price_risk_exposure:.1f}M**
                
                This represents the potential inventory value fluctuation within one standard deviation of price movement.
                
                **Hedging Strategy Options:**
                - **Full Hedge:** Protect entire inventory at a cost of ${full_hedge_cost:.2f}M
                - **Optimal Hedge ({optimal_hedge_ratio*100:.0f}%):** Balance protection and upside at ${full_hedge_cost*optimal_hedge_ratio:.2f}M
                - **Minimal Hedge (50%):** Basic protection at ${full_hedge_cost*0.5:.2f}M
                
                **Risk-Return Tradeoffs:**
                - Higher hedge ratio reduces downside risk but limits upside potential
                - Lower hedge ratio reduces costs but increases value volatility
                - Optimal strategy depends on market outlook and risk tolerance
                """)
                
                # Create hedge cost vs. protection visualization
                hedge_ratios = [0, 0.25, 0.5, 0.75, 1.0]
                hedge_costs = [current_inventory * hedging_cost * ratio / 1000 for ratio in hedge_ratios]
                downside_protection = [price_risk_exposure * ratio for ratio in hedge_ratios]
                
                fig = px.scatter(
                    x=hedge_costs,
                    y=downside_protection,
                    labels={
                        "x": "Hedging Cost ($M)",
                        "y": "Downside Protection ($M)"
                    },
                    title="Hedging Cost vs. Downside Protection",
                )
                
                # Add line
                fig.add_trace(
                    go.Scatter(
                        x=hedge_costs,
                        y=downside_protection,
                        mode='lines+markers',
                        line=dict(color='green'),
                        showlegend=False
                    )
                )
                
                # Add annotations for hedge ratios
                for i, ratio in enumerate(hedge_ratios):
                    fig.add_annotation(
                        x=hedge_costs[i],
                        y=downside_protection[i],
                        text=f"{ratio*100:.0f}%",
                        showarrow=False,
                        yshift=10
                    )
                
                fig.update_layout(height=300)
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Executive summary dashboard
            st.markdown("#### Digital Twin: Executive Summary")
            
            st.markdown('<div class="insight-card">', unsafe_allow_html=True)
            
            # Calculate additional executive metrics
            inventory_turnover = (avg_monthly_change * 12) / current_inventory
            cash_conversion_days = 365 / inventory_turnover
            working_capital_efficiency = refining_margin * inventory_turnover
            
            # Determine capital efficiency status
            if inventory_gap > 0:
                capital_opportunity = abs(value_gap)
                efficiency_message = f"**Opportunity to release ${capital_opportunity:.1f}M in working capital** through inventory optimization"
            else:
                capital_opportunity = 0
                efficiency_message = "Current inventory levels are below optimal target, indicating potential supply risk"
            
            st.markdown(f"""
            ## Crude Oil Inventory Management: Strategic Dashboard
            
            **Financial Overview:**
            - Total inventory value: **${inventory_value:.1f}M**
            - Annual carrying cost: **${annual_carrying_cost:.1f}M** ({carrying_cost*100:.1f}% of inventory value)
            - Inventory turnover: **{inventory_turnover:.2f}x per year**
            - Cash conversion cycle (inventory days): **{cash_conversion_days:.1f} days**
            
            **Working Capital Efficiency:**
            - {efficiency_message}
            - Capital efficiency (margin × turnover): **${working_capital_efficiency:.2f} per barrel**
            
            **Risk Management:**
            - Price risk exposure: **±${price_risk_exposure:.1f}M**
            - Optimal hedging strategy: **{optimal_hedge_ratio*100:.0f}%** coverage at **${full_hedge_cost*optimal_hedge_ratio:.2f}M** cost
            
            **Strategic Recommendations:**
            1. **Inventory Optimization**: {inventory_gap>0 and f"Reduce inventory by {abs(inventory_gap):,.0f} thousand barrels to release capital" or f"Increase inventory by {abs(inventory_gap):,.0f} thousand barrels to optimize supply security"}
            2. **Risk Management**: Implement {optimal_hedge_ratio*100:.0f}% hedging strategy to balance price protection with upside potential
            3. **Operational Excellence**: {current_days_supply>optimal_days_supply+5 and "Focus on reducing days of supply through improved forecasting and scheduling" or "Maintain current operational parameters which are within optimal range"}
            """)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        else:
            st.error(f"No data available for the selected PAD district: {selected_pad_fin}")

else:
    st.error("Failed to load data. Please check your connection and try again.")

            
            latest_year_data = filtered_data.filter(pl.col("year") == latest_year)
            prev_year_data = filtered_data.filter(pl.col("year") == prev_year)
            
            if len(latest_year_data) > 0 and len(prev_year_data) > 0:
                # Aggregate by month
                latest_monthly = latest_year_data.group_by(["month", "area-name"]).agg([
                    pl.col("value").mean().alias("curr_year")
                ])
                
                prev_monthly = prev_year_data.group_by(["month", "area-name"]).agg([
                    pl.col("value").mean().alias("prev_year")
                ])
                
                # Join the data
                yoy_comparison = latest_monthly.join(
                    prev_monthly, 
                    on=["month", "area-name"],
                    how="left"
                )
                
                # Calculate YoY change
                yoy_comparison = yoy_comparison.with_columns([
                    ((pl.col("curr_year") - pl.col("prev_year")) / pl.col("prev_year") * 100).alias("yoy_change")
                ])
                
                yoy_pd = yoy_comparison.to_pandas()
                
                # Create heatmap of YoY changes
                yoy_pivot = yoy_pd.pivot_table(
                    values="yoy_change", 
                    index="area-name", 
                    columns="month",
                    fill_value=0
                )
                
                # Add month names as column labels
                yoy_pivot.columns = [month_names[m-1] for m in yoy_pivot.columns]
                
                fig = px.imshow(
                    yoy_pivot,
                    labels=dict(x="Month", y="PAD District", color="YoY Change (%)"),
                    title=f"Year-over-Year Change ({prev_year} to {latest_year})",
                    color_continuous_scale="RdBu_r",
                    color_continuous_midpoint=0,
                    aspect="auto"
                )
                
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
                
                # Find biggest increase and decrease
                max_increase = yoy_pd.loc[yoy_pd['yoy_change'].idxmax()]
                max_decrease = yoy_pd.loc[yoy_pd['yoy_change'].idxmin()]
                
                st.markdown(f"""
                - **Largest increase**: {max_increase['area-name']} in {month_names[max_increase['month']-1]} (+{max_increase['yoy_change']:.1f}%)
                - **Largest decrease**: {max_decrease['area-name']} in {month_names[max_decrease['month']-1]} ({max_decrease['yoy_change']:.1f}%)
                - Year-over-year changes indicate shifts in supply-demand dynamics
                """)
            else:
                st.write("Insufficient data for year-over-year comparison")
            
            st.markdown('</div>', unsafe_allow_html=True)

    #------------------------------------------------#
    # TAB 2: Advanced Analytics
    #------------------------------------------------#
    with tab2:
        st.subheader("Advanced Analytics & Trend Detection")
        
        # Correlation Analysis
        st.markdown("#### Regional Correlation Analysis")
        st.markdown("Understanding how inventory levels correlate across regions provides insights into supply chain interconnections and market dynamics.")
        
        # Prepare correlation data
        pivoted_regional = df_regional.pivot(
            values="value",
            index="date",
            columns="area-name"
        ).to_pandas()
        
        # Calculate correlation matrix
        corr_matrix = pivoted_regional.corr().round(2)
        
        # Display correlation heatmap
        fig = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale="Blues",
            labels=dict(x="Region", y="Region", color="Correlation"),
            title="Interregional Inventory Correlation Matrix"
        )
        
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        # Find strongest correlations
        corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if i != j:
                    corr_pairs.append({
                        'region1': corr_matrix.columns[i],
                        'region2': corr_matrix.columns[j],
                        'correlation': corr_matrix.iloc[i, j]
                    })
        
        corr_pairs_df = pd.DataFrame(corr_pairs)
        top_correlations = corr_pairs_df.sort_values('correlation', ascending=False).head(3)
        bottom_correlations = corr_pairs_df.sort_values('correlation').head(3)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Strongest Regional Correlations")
            st.dataframe(top_correlations, hide_index=True)
            st.markdown("""
            *Strong positive correlations indicate regions that tend to build or draw inventory in tandem, suggesting similar market drivers or connected supply chains.*
            """)
            
        with col2:
            st.markdown("##### Weakest Regional Correlations")
            st.dataframe(bottom_correlations, hide_index=True)
            st.markdown("""
            *Weak correlations highlight regions with independent inventory behaviors, which may present hedging or arbitrage opportunities.*
            """)
        
        # Trend Analysis
        st.markdown("#### Trend Analysis & Anomaly Detection")
        
        # Select region for detailed analysis
        selected_region = st.selectbox(
            "Select Region for Detailed Analysis:",
            options=df_regional["area-name"].unique(),
            index=list(df_regional["area-name"].unique()).index("U.S.") if "U.S." in df_regional["area-name"].unique() else 0
        )
        
        # Filter data for the selected region
        region_data = df_regional.filter(pl.col("area-name") == selected_region).sort("date")
        region_pd = region_data.to_pandas()
        
        # Calculate moving averages and bands
        region_pd['MA_14'] = region_pd['value'].rolling(window=14).mean()
        region_pd['MA_52'] = region_pd['value'].rolling(window=52).mean()
        region_pd['std_52'] = region_pd['value'].rolling(window=52).std()
        region_pd['upper_band'] = region_pd['MA_52'] + 2 * region_pd['std_52']
        region_pd['lower_band'] = region_pd['MA_52'] - 2 * region_pd['std_52']
        
        # Identify anomalies (outside 2 standard deviations)
        region_pd['anomaly'] = (region_pd['value'] > region_pd['upper_band']) | (region_pd['value'] < region_pd['lower_band'])
        anomalies = region_pd[region_pd['anomaly']]
        
        # Create figure with subplots
        fig = make_subplots(rows=2, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.1,
                           subplot_titles=(f"{selected_region} Crude Oil Stock Trend Analysis", 
                                          "Weekly Rate of Change (%)"),
                           row_heights=[0.7, 0.3])
        
        # Add main stock level trace
        fig.add_trace(
            go.Scatter(
                x=region_pd['date'], 
                y=region_pd['value'],
                mode='lines',
                name='Stock Level',
                line=dict(color='royalblue')
            ),
            row=1, col=1
        )
        
        # Add moving averages
        fig.add_trace(
            go.Scatter(
                x=region_pd['date'], 
                y=region_pd['MA_14'],
                mode='lines',
                name='14-Week MA',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=region_pd['date'], 
                y=region_pd['MA_52'],
                mode='lines',
                name='52-Week MA',
                line=dict(color='green', width=1.5)
            ),
            row=1, col=1
        )
        
        # Add bands
        fig.add_trace(
            go.Scatter(
                x=region_pd['date'], 
                y=region_pd['upper_band'],
                mode='lines',
                name='Upper Band (+2σ)',
                line=dict(color='rgba(255,0,0,0.3)', width=1, dash='dash')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=region_pd['date'], 
                y=region_pd['lower_band'],
                mode='lines',
                name='Lower Band (-2σ)',
                line=dict(color='rgba(255,0,0,0.3)', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(0,176,246,0.1)'
            ),
            row=1, col=1
        )
        
        # Add anomalies
        fig.add_trace(
            go.Scatter(
                x=anomalies['date'], 
                y=anomalies['value'],
                mode='markers',
                name='Anomalies',
                marker=dict(size=8, color='red', symbol='circle')
            ),
            row=1, col=1
        )
        
        # Calculate weekly percentage change
        region_pd['pct_change'] = region_pd['value'].pct_change() * 100
        
        # Add percentage change
        fig.add_trace(
            go.Bar(
                x=region_pd['date'], 
                y=region_pd['pct_change'],
                name='Weekly % Change',
                marker_color=region_pd['pct_change'].apply(lambda x: 'red' if x < 0 else 'green')
            ),
            row=2, col=1
        )
        
        # Add zero line
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="black", row=2, col=1)
        
        # Update layout
        fig.update_layout(
            height=700,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            template="plotly_white"
        )
        
        # Update yaxis labels
        fig.update_yaxes(title_text="Stock Level (Thousand Barrels)", row=1, col=1)
        fig.update_yaxes(title_text="% Change", row=2, col=1)
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display anomaly statistics
        if len(anomalies) > 0:
            st.markdown(f"##### Detected {len(anomalies)} anomalies ({len(anomalies)/len(region_pd)*100:.1f}% of data points)")
            
            # List top anomalies
            top_anomalies = anomalies.sort_values(by='value', ascending=False).head(5)
            bottom_anomalies = anomalies.sort_values(by='value').head(5)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Top High Anomalies**")
                st.dataframe(top_anomalies[['date', 'value']], hide_index=True)
                
            with col2:
                st.markdown("**Top Low Anomalies**")
                st.dataframe(bottom_anomalies[['date', 'value']], hide_index=True)
                
        else:
            st.markdown("No anomalies detected in the selected timeframe.")
        
        # Decomposition Analysis
        st.markdown("#### Seasonal Decomposition")
        
        # Check if we have enough data for decomposition (at least 2 years)
        if len(region_pd) >= 104:  # 2 years of weekly data
            try:
                from statsmodels.tsa.seasonal import seasonal_decompose
                
                # Resample to monthly for clearer seasonal patterns
                monthly_data = region_pd.set_index('date')['value'].resample('M').mean()
                
                # Perform decomposition
                decomposition = seasonal_decompose(monthly_data, model='additive', period=12)
                
                # Create figure with subplots
                fig = make_subplots(rows=4, cols=1, 
                                  shared_xaxes=True,
                                  vertical_spacing=0.03,
                                  subplot_titles=("Observed", "Trend", "Seasonal", "Residual"),
                                  row_heights=[0.25, 0.25, 0.25, 0.25])
                
                # Add traces
                fig.add_trace(
                    go.Scatter(x=decomposition.observed.index, y=decomposition.observed, mode='lines', name='Observed'),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=decomposition.trend.index, y=decomposition.trend, mode='lines', name='Trend', line=dict(color='green')),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=decomposition.seasonal.index, y=decomposition.seasonal, mode='lines', name='Seasonal', line=dict(color='orange')),
                    row=3, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=decomposition.resid.index, y=decomposition.resid, mode='lines', name='Residual', line=dict(color='red')),
                    row=4, col=1
                )
                
                # Update layout
                fig.update_layout(
                    height=800,
                    showlegend=False,
                    template="plotly_white"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Extract insights from decomposition
                trend_direction = "increasing" if decomposition.trend.iloc[-12:].mean() > decomposition.trend.iloc[-24:-12].mean() else "decreasing"
                seasonal_magnitude = decomposition.seasonal.abs().mean()
                residual_volatility = decomposition.resid.std()
                
                st.markdown(f"""
                ##### Decomposition Insights
                
                - **Trend Component**: The long-term trend is {trend_direction} with an average rate of {(decomposition.trend.pct_change(12).mean() * 100):.2f}% per year
                - **Seasonal Component**: Average seasonal impact is ±{seasonal_magnitude:.2f} thousand barrels
                - **Residual Volatility**: Standard deviation of {residual_volatility:.2f} thousand barrels, representing unexplained market movements
                """)
                
            except Exception as e:
                st.error(f"Error performing decomposition: {e}")
        else:
            st.warning("Insufficient data for seasonal decomposition. At least 2 years of data required.")
        
        # Predictive analytics section
        st.markdown("#### Predictive Analytics")
        st.markdown("Forecasting future inventory levels using historical patterns and trends")
        
        horizon = st.slider("Forecast Horizon (Weeks)", min_value=4, max_value=52, value=12)
        
        try:
            from sklearn.linear_model import LinearRegression
            from sklearn.ensemble import RandomForestRegressor
            
            # Prepare features for prediction
            region_pd['trend'] = np.arange(len(region_pd))
            region_pd['month'] = region_pd['date'].dt.month
            region_pd['week'] = region_pd['date'].dt.isocalendar().week
            
            # Create lags
            for lag in [1, 2, 4, 8, 12]:
                region_pd[f'lag_{lag}'] = region_pd['value'].shift(lag)
            
            # Create rolling features
            region_pd['rolling_mean_4'] = region_pd['value'].rolling(window=4).mean()
            region_pd['rolling_mean_12'] = region_pd['value'].rolling(window=12).mean()
            region_pd['rolling_std_12'] = region_pd['value'].rolling(window=12).std()
            
            # Drop rows with NaN values
            model_data = region_pd.dropna()
            
            # Split data into train and test sets
            train_size = len(model_data) - horizon
            train_data = model_data.iloc[:train_size]
            test_data = model_data.iloc[train_size:]
            
            # Define features
            features = ['trend', 'month', 'week', 'lag_1', 'lag_2', 'lag_4', 'lag_8', 'lag_12', 
                       'rolling_mean_4', 'rolling_mean_12', 'rolling_std_12']
            
            # Train Linear Regression model
            lr_model = LinearRegression()
            lr_model.fit(train_data[features], train_data['value'])
            
            # Train Random Forest model
            rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
            rf_model.fit(train_data[features], train_data['value'])
            
            # Make predictions
            lr_pred = lr_model.predict(test_data[features])
            rf_pred = rf_model.predict(test_data[features])
            
            # Calculate errors
            lr_mae = np.mean(np.abs(lr_pred - test_data['value']))
            rf_mae = np.mean(np.abs(rf_pred - test_data['value']))
            
            # Create future dates for forecasting
            last_date = region_pd['date'].max()
            future_dates = [last_date + timedelta(days=7*i) for i in range(1, horizon+1)]
            
            # Create future features
            future_data = pd.DataFrame({
                'date': future_dates,
                'trend': np.arange(len(region_pd), len(region_pd) + horizon),
                'month': [d.month for d in future_dates],
                'week': [d.isocalendar()[1] for d in future_dates]
            })
            
            # Recursively generate predictions
            future_values_lr = []
            future_values_rf = []
            
            # Make a copy of the last rows for recursive forecasting
            recent_data = region_pd.iloc[-horizon:].copy()
            
            for i in range(horizon):
                # Update features based on previous predictions
                if i == 0:
                    future_row = {
                        'lag_1': recent_data['value'].iloc[-1],
                        'lag_2': recent_data['value'].iloc[-2],
                        'lag_4': recent_data['value'].iloc[-4],
                        'lag_8': recent_data['value'].iloc[-8],
                        'lag_12': recent_data['value'].iloc[-12] if len(recent_data) >= 12 else recent_data['value'].mean(),
                        'rolling_mean_4': recent_data['value'].iloc[-4:].mean(),
                        'rolling_mean_12': recent_data['value'].iloc[-12:].mean() if len(recent_data) >= 12 else recent_data['value'].mean(),
                        'rolling_std_12': recent_data['value'].iloc[-12:].std() if len(recent_data) >= 12 else recent_data['value'].std()
                    }
                else:
                    # Use previously predicted values
                    predicted_vals = future_values_lr if lr_mae < rf_mae else future_values_rf
                    all_recent_values = list(recent_data['value'].iloc[-(horizon-i):]) + predicted_vals
                    
                    future_row = {
                        'lag_1': all_recent_values[-1],
                        'lag_2': all_recent_values[-2] if len(all_recent_values) >= 2 else recent_data['value'].iloc[-1],
                        'lag_4': all_recent_values[-4] if len(all_recent_values) >= 4 else recent_data['value'].iloc[-1],
                        'lag_8': all_recent_values[-8] if len(all_recent_values) >= 8 else recent_data['value'].iloc[-1],
                        'lag_12': all_recent_values[-12] if len(all_recent_values) >= 12 else recent_data['value'].iloc[-1],
                        'rolling_mean_4': np.mean(all_recent_values[-4:]),
                        'rolling_mean_12': np.mean(all_recent_values[-12:]) if len(all_recent_values) >= 12 else np.mean(all_recent_values),
                        'rolling_std_12': np.std(all_recent_values[-12:]) if len(all_recent_values) >= 12 else np.std(all_recent_values)
                    }
                
                # Combine with other features
                future_row.update({
                    'trend': future_data['trend'].iloc[i],
                    'month': future_data['month'].iloc[i],
                    'week': future_data['week'].iloc[i]
                })
                
                # Make predictions
                lr_pred = lr_model.predict([list(future_row.values())])[0]
                rf_pred = rf_model.predict([list(future_row.values())])[0]
                
                future_values_lr.append(lr_pred)
                future_values_rf.append(rf_pred)
            
            # Create forecast dataframe
            forecast_df = pd.DataFrame({
                'date': future_dates,
                'Linear Regression': future_values_lr,
                'Random Forest': future_values_rf
            })
            
            # Plot actual vs predicted
            fig = go.Figure()
            
            # Add historical data
            fig.add_trace(
                go.Scatter(
                    x=region_pd['date'],
                    y=region_pd['value'],
                    mode='lines',
                    name='Historical',
                    line=dict(color='blue')
                )
            )
            
            # Add test predictions
            fig.add_trace(
                go.Scatter(
                    x=test_data['date'],
                    y=lr_pred,
                    mode='lines',
                    name='Linear Regression (Test)',
                    line=dict(color='green', dash='dash')
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=test_data['date'],
                    y=rf_pred,
                    mode='lines',
                    name='Random Forest (Test)',
                    line=dict(color='red', dash='dash')
                )
            )
            
            # Add future predictions
            fig.add_trace(
                go.Scatter(
                    x=forecast_df['date'],
                    y=forecast_df['Linear Regression'],
                    mode='lines',
                    name='Linear Regression (Forecast)',
                    line=dict(color='green')
                )
            )
            
            fig.add_trace(
                go.Scatter(
                    x=forecast_df['date'],
                    y=forecast_df['Random Forest'],
                    mode='lines',
                    name='Random Forest (Forecast)',
                    line=dict(color='red')
                )
            )
            
            # Add vertical line to mark forecast start
            fig.add_vline(
                x=region_pd['date'].max(),
                line_width=1,
                line_dash="dash",
                line_color="black",
                annotation_text="Forecast Start",
                annotation_position="top right"
            )
            
            # Update layout
            fig.update_layout(
                height=500,
                title=f"{selected_region} Crude Oil Stock Forecast for Next {horizon} Weeks",
                xaxis_title="Date",
                yaxis_title="Stock Level (Thousand Barrels)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display forecast metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### Forecast Accuracy Metrics")
                metrics_df = pd.DataFrame({
                    'Model': ['Linear Regression', 'Random Forest'],
                    'MAE': [lr_mae, rf_mae],
                    'MAE (%)': [lr_mae / test_data['value'].mean() * 100, rf_mae / test_data['value'].mean() * 100]
                })
                
                st.dataframe(metrics_df.round(2), hide_index=True)
                
                best_model = "Linear Regression" if lr_mae < rf_mae else "Random Forest"
                st.markdown(f"**Best performing model: {best_model}**")
                
            with col2:
                st.markdown("##### End of Period Forecast")
                
                # Get last actual value
                last_actual = region_pd['value'].iloc[-1]
                
                # Get forecasted values for end of period
                lr_end = forecast_df['Linear Regression'].iloc[-1]
                rf_end = forecast_df['Random Forest'].iloc[-1]
                
                # Calculate change
                lr_change = (lr_end - last_actual) / last_actual * 100
                rf_change = (rf_end - last_actual) / last_actual * 100
                
                forecast_end_df = pd.DataFrame({
                    'Model': ['Linear Regression', 'Random Forest'],
                    'End Value': [lr_end, rf_end],
                    'Change (%)': [lr_change, rf_change]
                })
                
                st.dataframe(forecast_end_df.round(2), hide_index=True)
                
                # Forecast direction
                preferred_forecast = lr_end if lr_mae < rf_mae else rf_end
                preferred_change = lr_change if lr_mae < rf_mae else rf_change
                direction = "increase" if preferred_change > 0 else "decrease"
                
                st.markdown(f"**Forecast direction: {direction} of {abs(preferred_change):.1f}% over {horizon} weeks**")
                
        except Exception as e:
            st.error(f"Error in predictive analytics: {e}")

    #------------------------------------------------#
    # TAB 3: Digital Twin Simulation
    #------------------------------------------------#
    with tab3:
        st.subheader("Digital Twin: Inventory Dynamics Simulation")
        st.markdown("""
        This digital twin simulates crude oil inventory dynamics across the supply chain, allowing you to model different scenarios 
        and understand their business impact.
        """)
        
        # Digital Twin Parameters
        st.markdown("#### Simulation Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_pad = st.selectbox(
                "Select PAD District:",
                options=df_regional["area-name"].unique().sort(),
                index=0
            )
            
            production_change = st.slider(
                "Production Rate Change (%)",
                min_value=-20,
                max_value=20,
                value=0,
                step=1
            )
            
        with col2:
            refinery_utilization = st.slider(
                "Refinery Utilization (%)",
                min_value=70,
                max_value=100,
                value=85,
                step=1
            )
            
            import_change = st.slider(
                "Import Volume Change (%)",
                min_value=-30,
                max_value=30,
                value=0,
                step=1
            )
            
        with col3:
            export_change = st.slider(
                "Export Volume Change (%)",
                min_value=-30,
                max_value=30,
                value=0,
                step=1
            )
            
            storage_capacity = st.slider(
                "Storage Capacity Utilization (%)",
                min_value=40,
                max_value=95,
                value=70,
                step=1
            )
        
        # Simulation timeframe
        sim_duration = st.slider(
            "Simulation Duration (Weeks)",
            min_value=4,
            max_value=52,
            value=12,
            step=4
        )
        
        # Get historical data for selected PAD
        pad_data = df_regional.filter(pl.col("area-name") == selected_pad).sort("date")
        pad_data_pd = pad_data.to_pandas()
        
        # Get latest value for baseline
        if len(pad_data_pd) > 0:
            latest_value = pad_data_pd['value'].iloc[-1]
            avg_weekly_change = pad_data_pd['value'].diff().mean()
            
            # Define default parameters for simulation (can be customized further)
            base_production = latest_value * 0.04  # Assume weekly production is 4% of inventory
            base_refining = latest_value * 0.05    # Assume weekly refining is 5% of inventory
            base_imports = latest_value * 0.03     # Assume weekly imports are 3% of inventory
            base_exports = latest_value * 0.02     # Assume weekly exports are 2% of inventory
            
            # Adjust parameters based on user inputs
            adj_production = base_production * (1 + production_change/100)
            adj_refining = base_refining * (refinery_utilization/85)  # Normalized to 85% baseline
            adj_imports = base_imports * (1 + import_change/100)
            adj_exports = base_exports * (1 + export_change/100)
            
            # Calculate max storage capacity
            max_capacity = latest_value / (storage_capacity/100)
            
            # Run simulation
            sim_dates = [pad_data_pd['date'].iloc[-1] + timedelta(days=7*i) for i in range(1, sim_duration+1)]
            sim_inventory = [latest_value]
            
            for i in range(sim_duration):
                # Calculate weekly balance
                weekly_production = adj_production
                weekly_refining = min(adj_refining, sim_inventory[-1] * 0.15)  # Can't refine more than 15% of inventory
                weekly_imports = adj_imports
                weekly_exports = min(adj_exports, sim_inventory[-1] * 0.1)  # Can't export more than 10% of inventory
                
                # Net change
                net_change = weekly_production + weekly_imports - weekly_refining - weekly_exports
                
                # New inventory level
                new_inventory = min(sim_inventory[-1] + net_change, max_capacity)  # Cap at max capacity
                sim_inventory.append(new_inventory)
            
            # Remove the first value (which is the last actual value)
            sim_inventory = sim_inventory[1:]
            
            # Create simulation dataframe
            sim_df = pd.DataFrame({
                'date': sim_dates,
                'inventory': sim_inventory
            })
            
            # Create historical + simulation plot
            fig = go.Figure()
            
            # Add historical data
            fig.add_trace(
                go.Scatter(
                    x=pad_data_pd['date'].iloc[-52:],  # Show last year
                    y=pad_data_pd['value'].iloc[-52:],
                    mode='lines',
                    name='Historical',
                    line=dict(color='blue')
                )
            )
            
            # Add simulation
            fig.add_trace(
                go.Scatter(
                    x=sim_df['date'],
                    y=sim_df['inventory'],
                    mode='lines',
                    name='Simulation',
                    line=dict(color='red')
                )
            )
            
            # Add capacity line
            fig.add_trace(
                go.Scatter(
                    x=list(pad_data_pd['date'].iloc[-52:]) + list(sim_df['date']),
                    y=[max_capacity] * (52 + len(sim_df)),
                    mode='lines',
                    name='Storage Capacity',
                    line=dict(color='gray', dash='dash')
                )
            )
            
            # Add vertical line at simulation start
            fig.add_vline(
                x=pad_data_pd['date'].iloc[-1],
                line_width=1,
                line_dash="dash",
                line_color="black",
                annotation_text="Simulation Start",
                annotation_position="top right"
            )
            
            # Update layout
            fig.update_layout(
                height=500,
                title=f"Digital Twin Simulation: {selected_pad} Crude Oil Inventory",
                xaxis_title="Date",
                yaxis_title="Stock Level (Thousand Barrels)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                template="plotly_white"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Calculate key simulation metrics
            final_inventory = sim_inventory[-1]
            net_change = final_inventory - latest_value
            pct_change = (net_change / latest_value) * 100
            
            # Display simulation insights
            st.markdown("#### Simulation Results")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="insight-card">', unsafe_allow_html=True)
                st.markdown("##### Inventory Balance Sheet")
                
                # Create weekly average flow data
                flow_data = pd.DataFrame({
                    'Component': ['Production', 'Imports', 'Refining', 'Exports', 'Net Change'],
                    'Weekly Rate (K Barrels)': [adj_production, adj_imports, -adj_refining, -adj_exports, adj_production + adj_imports - adj_refining - adj_exports],
                    'Share of Throughput (%)': [
                        adj_production / (adj_production + adj_imports) * 100,
                        adj_imports / (adj_production + adj_imports) * 100,
                        adj_refining / (adj_refining + adj_exports) * 100,
                        adj_exports / (adj_refining + adj_exports) * 100,
                        0  # Placeholder, not relevant for net change
                    ]
                })
                
                # Display flow data
                st.dataframe(flow_data.iloc[:4].round(1), hide_index=True)
                
                # Display net balance
                st.markdown(f"""
                **Weekly Net Balance: {flow_data['Weekly Rate (K Barrels)'].iloc[4]:,.1f} thousand barrels**
                
                This simulation models the crude oil balance incorporating:
                - Production rates influenced by drilling activity and well productivity
                - Refinery utilization reflecting maintenance and market demand
                - Import/export dynamics adjusted for trade conditions
                - Storage capacity constraints
                ""