from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Optional, Dict, Any, Union, Tuple
from utils.cache_utils import get_cached_data, get_cached_layout
from dash.exceptions import PreventUpdate
import time

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

def create_subpart_breakdown(app):
    """
    Creates a Plotly donut chart showing emissions breakdown by subpart.
    
    Args:
        app: The Dash application instance for registering callbacks
    
    Returns:
        A Dash component containing the donut chart with loading state
    """
    # Store for tracking last update timestamp
    last_update_store = dcc.Store(id='subpart-last-update-timestamp', data=0)
    
    @app.callback(
        Output('subpart-breakdown-graph', 'figure'),
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value'),
            Input('category-dropdown', 'value')
        ],
        [
            State('subpart-last-update-timestamp', 'data')
        ]
    )
    def update_subpart_graph(year_range, selected_states, selected_category, last_update):
        # Get current timestamp
        current_time = time.time()
        
        # Allow initial load or if sufficient time has passed (1 second debounce)
        if last_update and current_time - last_update < 1.0:
            raise PreventUpdate
            
        try:
            # Get data using the cached function
            cache_result = get_cached_data(
                state_filter=tuple(selected_states) if selected_states else None,
                year_range=tuple(year_range) if year_range else None,
                category_filter=tuple([selected_category]) if selected_category else None
            )
            data = cache_result['main_chart_data']
            
            if not data or len(data) == 0:
                return go.Figure().add_annotation(
                    text='No data available for breakdown chart',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
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
                return go.Figure().add_annotation(
                    text='No subpart data available',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
            
            # Apply category filter if provided
            if selected_category:
                df = df[df['subparts'] == selected_category]
                if len(df) == 0:
                    return go.Figure().add_annotation(
                        text=f'No data available for category: {selected_category}',
                        xref='paper',
                        yref='paper',
                        x=0.5,
                        y=0.5,
                        showarrow=False
                    )
            
            if 'value' not in df.columns:
                return go.Figure().add_annotation(
                    text='No emissions data available',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
            
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

            # Get cached layout configuration
            layout = get_cached_layout('subpart')
            
            # Update layout with chart-specific settings
            layout.update({
                'title': title,
                'showlegend': False,  # Hide legend for cleaner look
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white'
            })
            
            fig.update_layout(layout)
            return fig
            
        except Exception as e:
            print(f"Error creating figure: {str(e)}")
            return go.Figure().add_annotation(
                text='Error creating chart. Please try again.',
                xref='paper',
                yref='paper',
                x=0.5,
                y=0.5,
                showarrow=False
            )
    
    # Return the component structure
    return html.Div([
        dcc.Loading(
            id="loading-subpart-graph",
            type="default",
            children=[
                dcc.Graph(
                    id='subpart-breakdown-graph',
                    config={'displayModeBar': True, 'scrollZoom': False}
                )
            ]
        ),
        last_update_store
    ])