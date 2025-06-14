from dash import html, dcc
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from typing import Tuple, List, Dict, Optional
from utils.cache_utils import get_cached_data

def validate_state_data(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate the dataframe for state emissions plotting.
    
    Args:
        df: Input dataframe to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if data is valid
            - Error message if invalid, empty string if valid
    """
    if df is None or df.empty:
        return False, "No data available"
    
    required_columns = ['state', 'year', 'value']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    return True, ""

# Context:
# This file implements the state emissions graph component for the GHG emissions dashboard.
# It visualizes greenhouse gas emissions data over time for different states, allowing users to:
# - View emissions trends for multiple states simultaneously
# - Compare emissions between states using an interactive legend
# - See all states' data when no specific state is selected
# - Filter data by year range and categories
# - Display individual state data on hover for better data exploration
#
# The graph is designed to be clean and uncluttered, with state identification provided through
# the legend rather than callout labels, making it easier to focus on the data trends.

def prepare_state_plot_data(df: pd.DataFrame, selected_states: List[str]) -> pd.DataFrame:
    """Prepare data for state emissions plot.
    
    Args:
        df: Input dataframe with emissions data
        selected_states: List of selected state names. If empty, all states will be included.
        
    Returns:
        Processed dataframe ready for plotting, containing either all states or selected states
    """
    # Return data for all states if none are selected, otherwise filter for selected states
    states_data = df.copy() if not selected_states else df[df['state'].isin(selected_states)].copy()
    
    # Ensure numeric types
    states_data['year'] = pd.to_numeric(states_data['year'], errors='coerce')
    states_data['value'] = pd.to_numeric(states_data['value'], errors='coerce')
    
    # Drop any rows with NaN values after conversion
    states_data = states_data.dropna(subset=['year', 'value'])
    
    return states_data

def create_state_emissions_graph(app):
    """Creates and configures the state emissions graph component.
    
    Args:
        app: The Dash application instance for registering callbacks
        
    Returns:
        A Dash component representing the emissions graph with interactive controls
    """
    
    @app.callback(
        Output('state-emissions-graph', 'figure'),
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value'),
            Input('category-dropdown', 'value')
        ]
    )
    def update_graph(year_range, selected_states, category):
        try:
            # Input validation and defaults
            if not year_range or not isinstance(year_range, list) or len(year_range) != 2:
                year_range = [2010, 2023]  # Updated default range based on available data
            
            if not selected_states or not isinstance(selected_states, list):
                selected_states = []
            
            # Ensure year_range values are integers
            year_range = [int(year_range[0]), int(year_range[1])]
            
            print(f"[DEBUG] update_graph - Processing year range: {year_range}")
            
            print(f"[DEBUG] update_graph - Selected states: {selected_states}")
            
            # Use cached data retrieval with proper state filtering
            cache_result = get_cached_data(
                state_filter=None if not selected_states else tuple(selected_states),
                year_range=tuple(year_range)
            )
            
            print(f"[DEBUG] update_graph - Cache result data points: {len(cache_result.get('main_chart_data', []))}")
            if cache_result.get('main_chart_data'):
                print(f"[DEBUG] update_graph - Sample data point: {cache_result['main_chart_data'][0]}")
                print(f"[DEBUG] update_graph - Unique years in data: {sorted(set(d['year'] for d in cache_result['main_chart_data']))}")
                print(f"[DEBUG] update_graph - Unique states in data: {sorted(set(d['state'] for d in cache_result['main_chart_data']))}")
            
            if not isinstance(cache_result, dict) or 'main_chart_data' not in cache_result:
                raise ValueError("Invalid data format returned from cache")
                
            filtered_data = cache_result['main_chart_data']
            
            # Convert to DataFrame and validate
            states_data = pd.DataFrame(filtered_data)
            is_valid, error_message = validate_state_data(states_data)
            if not is_valid:
                raise ValueError(error_message)
            
            # Prepare data for plotting
            states_data = prepare_state_plot_data(states_data, selected_states)
            if states_data.empty:
                raise ValueError("No data available for selected states")
            
            # Create figure
            fig = go.Figure()
            
            # Add traces for each state
            colors = px.colors.qualitative.Set1
            
            # Get unique states from the data
            states_to_plot = selected_states if selected_states else sorted(states_data['state'].unique())
            
            if not states_data.empty:
                for idx, state in enumerate(states_to_plot):
                    state_data = states_data[states_data['state'] == state]
                    
                    if len(state_data) > 0:
                        try:
                            fig.add_trace(
                                go.Scatter(
                                    x=state_data['year'].astype(int),
                                    y=state_data['value'].astype(float),
                                    name=state,
                                    mode='lines+markers',
                                    line=dict(color=colors[idx % len(colors)]),
                                    hovertemplate=(
                                        '<b>%{x}</b><br>'
                                        'State: ' + state + '<br>'
                                        'GHG Emissions: %{y:,.2f}<br>'
                                        '<extra></extra>'
                                    )
                                )
                            )
                        except Exception as e:
                            print(f"Error adding trace for state {state}: {str(e)}")
                            continue
        
            # Update layout
            try:
                fig.update_layout(
                    title='State GHG Emissions Over Time',
                    xaxis=dict(
                        title='Year',
                        gridcolor='lightgray',
                        showgrid=True,
                        tickmode='linear',
                        range=[year_range[0], year_range[1]]
                    ),
                    yaxis=dict(
                        title='GHG Emissions (Metric Tons CO2e)',
                        gridcolor='lightgray',
                        showgrid=True
                    ),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    hovermode='closest',  # Show data only for the closest point/line
                    showlegend=True,
                    # Configure legend to be the primary state identifier
                    # Position it prominently but not overlapping with the graph
                    legend=dict(
                        yanchor='top',
                        y=0.99,
                        xanchor='right',
                        x=0.99,
                        bgcolor='rgba(255, 255, 255, 0.8)',
                        font=dict(size=12)
                    ),
                    margin=dict(l=60, r=50, t=50, b=50)
                )
                
                return fig
                
            except Exception as e:
                print(f"Error updating layout: {str(e)}")
                # Return a basic figure with error message
                return go.Figure().add_annotation(
                    text='Error loading emissions data. Please try again.',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
                
        except Exception as e:
            print(f"Error in update_graph: {str(e)}")
            # Return a basic figure with error message
            return go.Figure().add_annotation(
                text='Error updating graph. Please check your selections.',
                xref='paper',
                yref='paper',
                x=0.5,
                y=0.5,
                showarrow=False
            )
    
    # Return the graph component
    return html.Div(
        className='emissions-chart-container',
        children=[
            dcc.Graph(
                id='state-emissions-graph',
                config={
                    'displayModeBar': True,
                    'scrollZoom': True,
                    'responsive': True
                },
                style={'height': '500px'}
            )
        ]
    )