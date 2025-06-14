# Context:
# This component creates a donut chart visualization showing the breakdown of greenhouse gas emissions
# by EPA subpart categories or by states within a selected subpart. It provides an interactive
# visualization with hover information showing emissions values and percentages, supporting filtering
# by states, year range, and subpart categories. The chart is designed to be displayed side-by-side
# with the state emissions graph for easy comparison.

from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd
from typing import List, Tuple, Dict, Any

def format_pie_labels(values: List[float], labels: List[str], threshold: float = 5.0) -> Tuple[List[str], str]:
    """Format pie chart labels based on percentage threshold.
    
    Args:
        values: Values for pie chart segments
        labels: Labels for segments
        threshold: Minimum percentage to show label (default: 5.0)
        
    Returns:
        Tuple containing:
            - List of formatted labels (empty string for values below threshold)
            - Hover template string
    """
    total = sum(values)
    percentages = [(v / total) * 100 for v in values]
    
    # Format labels based on threshold
    formatted_labels = [
        label if pct >= threshold else ""
        for label, pct in zip(labels, percentages)
    ]
    
    # Create hover template that always shows the label
    hover_template = (
        '<b>%{label}</b><br>' +
        'Emissions: %{value:,.0f} MT CO2e<br>' +
        'Percentage: %{percent:.1f}%<br>' +
        '%{customdata}<br>' +
        '<extra></extra>'
    )
    
    return formatted_labels, hover_template

def create_subpart_breakdown(data, selected_states=None, year_range=None, selected_category=None):
    """
    Creates a Plotly donut chart showing emissions breakdown by subpart.
    
    Args:
        data (list): List of dictionaries containing emissions data
        selected_states (list): List of selected state names
        year_range (list): [start_year, end_year] for filtering
        selected_category (str): Selected subpart category for filtering
    
    Returns:
        dash.dcc.Graph: A Dash Graph component containing the donut chart
    """
    if not data or len(data) == 0:
        return html.Div(
            "No data available for breakdown chart",
            className="text-center py-8"
        )

    # Convert to DataFrame for easier manipulation
    df = pd.DataFrame(data)
    
    # Apply filters if provided
    if selected_states and len(selected_states) > 0:
        df = df[df['state'].isin(selected_states)]
    
    if year_range:
        df = df[(df['year'].astype(int) >= year_range[0]) & 
                (df['year'].astype(int) <= year_range[1])]

    # Check for subpart column
    if 'subparts' not in df.columns:
        return html.Div("No subpart data available", className="text-center py-8")
    
    # Apply category filter if provided
    if selected_category:
        df = df[df['subparts'] == selected_category]
        if len(df) == 0:
            return html.Div(f"No data available for category: {selected_category}", className="text-center py-8")
    
    if 'value' not in df.columns:
        return html.Div("No emissions data available", className="text-center py-8")
    
    # Group by subpart
    if selected_category:
        # Group by state when category is selected
        group_data = df.groupby('state').agg({
            'value': 'sum'
        }).reset_index()
        
        group_data.columns = ['entity', 'emissions']
        title = f'Emissions for Subpart {selected_category} by State'
        label_prefix = ''
    else:
        # Group by subpart
        group_data = df.groupby('subparts').agg({
            'value': 'sum',
            'state': 'nunique'
        }).reset_index()
        
        group_data.columns = ['entity', 'emissions', 'stateCount']
        title = 'Emissions by Subpart'
        label_prefix = 'Subpart '
    
    group_data['emissions'] = group_data['emissions'].round(0)
    
    # Calculate percentages
    total_emissions = group_data['emissions'].sum()
    group_data['percentage'] = (group_data['emissions'] / total_emissions * 100).round(1)
    
    # Sort by emissions
    group_data = group_data.sort_values('emissions', ascending=False)

    # Create donut chart with hover-only labels for cleaner visualization
    if selected_category:
        labels = [row.entity for _, row in group_data.iterrows()]
        values = group_data['emissions'].tolist()
        percentages = [(v / sum(values)) * 100 for v in values]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,  # Keep original labels for hover text
            text=[''] * len(labels),  # Remove text labels for cleaner look
            textposition='none',  # Disable text display
            values=values,
            hole=0.5,
            hovertemplate=('<b>%{label}</b><br>' +
                          'Emissions: %{value:,.0f} MT CO2e<br>' +
                          'Percentage: %{percent:.1f}%<br>' +
                          '<extra></extra>'),
            customdata=[''] * len(labels)  # Empty customdata for states view
        )])
    else:
        labels = [f'{label_prefix}{row.entity}' for _, row in group_data.iterrows()]
        values = group_data['emissions'].tolist()
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,  # Keep original labels for hover text
            text=[''] * len(labels),  # Remove text labels for cleaner look
            textposition='none',  # Disable text display
            values=values,
            hole=0.5,
            hovertemplate=('<b>%{label}</b><br>' +
                          'Emissions: %{value:,.0f} MT CO2e<br>' +
                          'Percentage: %{percent:.1f}%<br>' +
                          'States: %{customdata}<br>' +
                          '<extra></extra>'),
            customdata=[f'{count}' for count in group_data['stateCount']]
        )])

    # Update layout - Remove duplicate title and adjust margins for side-by-side alignment
    fig.update_layout(
        title=title,  
        showlegend=False,
        legend=dict(
            orientation='h',     # Horizontal legend
            yanchor='top',      # Anchor to top
            y=-0.1,            # Position below the graph
            xanchor='center',   # Center horizontally
            x=0.5,             # Center position
            xref='container',   # Reference to container width        
            itemwidth=30        # Reduce width of legend items
        ),
        margin=dict(t=50, l=10, r=10, b=50),  # Reduced top margin since title is removed
        height=500  # Increase chart height for better visibility
    )

    # Create and return the Dash graph component
    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': True, 'scrollZoom': False}
    )