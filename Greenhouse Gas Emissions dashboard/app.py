# Context:
# This is the main application file that creates a Dash web application for visualizing greenhouse gas emissions data.
# It provides an interactive dashboard with filters for year range, states, and categories, and displays two main
# visualizations side by side: a time series graph showing state emissions trends and a donut chart showing
# emissions breakdown by subpart.

import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import pandas as pd
from components.state_graph import create_state_emissions_graph
from components.subpart_graph import create_subpart_breakdown
from utils.cache_utils import get_cached_data, clear_data_cache

# Initialize the Dash app
app = dash.Dash(__name__)

# Define the app layout
app.layout = html.Div([
    # Header
    html.H1('Greenhouse Gas Emissions Dashboard', className='dashboard-header'),
    
    # Main container
    html.Div([
        # Sidebar with filters
        html.Div([
            html.H3('Filters', className='filters-header'),
            
            # Year range filter
            html.Label('Reporting Year Range'),
            # Get initial data to determine year range
            dcc.RangeSlider(
                id='year-range-slider',
                min=2010,  # Starting year based on data
                max=2023,  # Latest year based on data
                step=1,
                value=[2010, 2023],  # Default to full range
                marks={str(year): str(year) for year in range(2010, 2024, 2)}  # Show every other year for better readability
            ),
            
            # State selection
            html.Label('Select States'),
            dcc.Dropdown(
                id='state-dropdown',
                options=[],  # Will be populated from data
                multi=True,
                placeholder='Select states...',
                value=[]  # Initialize with an empty list to prevent None
            ),
            
            # Category selection
            html.Label('Category'),
            dcc.Dropdown(
                id='category-dropdown',
                options=[],  # Will be populated from data
                placeholder='Select category...',
                value=None  # Initialize with None for single selection
            )
        ], className='filters-container'),
        
        # Main content area with charts - State emissions chart takes up more space (75%)
        # while subpart breakdown is positioned to the right (25%)
        html.Div([
            # State emissions chart - wider for better visibility of time series data
            html.Div([
                create_state_emissions_graph(app)
            ], className='chart-container', style={'width': '100%', 'display': 'inline-block'}),
            
            # Subpart breakdown chart - positioned to the right
            html.Div([
                html.Div(id='subpart-breakdown-container')
            ], className='chart-container', style={'width': '100%', 'display': 'inline-block'})
        ], className='charts-container')
    ], className='main-container')
], className='dashboard-container')

# Callback to update subpart breakdown
@app.callback(
    Output('subpart-breakdown-container', 'children'),
    [Input('year-range-slider', 'value'),
     Input('state-dropdown', 'value'),
     Input('category-dropdown', 'value')]
)
def update_subpart_breakdown(year_range, selected_states, selected_category):
    # Log the input parameters for debugging
    print(f"[DEBUG] update_subpart_breakdown - year_range: {year_range}, selected_states: {selected_states}, selected_category: {selected_category}")

    # Ensure selected_states is a list, even if None is passed initially
    if selected_states is None:
        selected_states = []

    if not year_range:
        print("[DEBUG] update_subpart_breakdown - Missing year_range, returning placeholder.")
        return html.Div('Please select a year range to view breakdown')
    
    try:
        # Get data using the cached function
        data = get_cached_data(
            state_filter=tuple(selected_states) if selected_states else None,
            year_range=tuple(year_range) if year_range else None,
            category_filter=tuple([selected_category]) if selected_category else None
        )
        print(f"[DEBUG] update_subpart_breakdown - Data retrieved from cache with {len(data.get('main_chart_data', []))} data points")
        
        # Use cached data retrieval
        cache_result = get_cached_data(
            state_filter=tuple(selected_states) if selected_states else None,
            year_range=tuple(year_range) if year_range else None,
            category_filter=tuple([selected_category]) if selected_category else None
        )
        data = cache_result['main_chart_data']
        print(f"[DEBUG] update_subpart_breakdown - Data retrieved from cache. Data points: {len(data)}")
        if data:
            print(f"[DEBUG] update_subpart_breakdown - Sample data: {data[:2]}")
        return create_subpart_breakdown(data, selected_states, year_range, selected_category)
    except Exception as e:
        print(f"[ERROR] update_subpart_breakdown - Error loading breakdown: {str(e)}")
        return html.Div(f'Error loading breakdown: {str(e)}')

# Clear cache on app startup
clear_data_cache()

# Callback to populate dropdowns
@app.callback(
    [
        Output('state-dropdown', 'options'),
        Output('category-dropdown', 'options')
    ],
    [Input('year-range-slider', 'value')]
)
def update_dropdown_options(year_range):
    # Log the input parameter for debugging
    print(f"[DEBUG] update_dropdown_options - year_range: {year_range}")

    try:
        # Read raw data for unique values
        raw_data = pd.read_excel('data/emissions_data.xlsx')
        
        # Get unique states and categories from raw data
        states = sorted(raw_data['STATE'].unique())
        categories = sorted(raw_data['SUBPARTS'].unique())
        
        # Create dropdown options
        state_options = [{'label': state, 'value': state} for state in states]
        category_options = [{'label': cat, 'value': cat} for cat in categories]
        
        print(f"[DEBUG] update_dropdown_options - States found: {len(state_options)}")
        print(f"[DEBUG] update_dropdown_options - Categories found: {len(category_options)}")
        
        return state_options, category_options
    except Exception as e:
        print(f"[ERROR] update_dropdown_options - Error updating dropdown options: {str(e)}")
        return [], []

# Add logging to the update_graph callback in create_state_emissions_graph
# This part is within components/state_graph.py, but I'm showing how it would look conceptually.
# You would need to apply this change in components/state_graph.py directly.

# In components/state_graph.py, inside the update_graph callback:
# @app.callback(
#     Output('state-emissions-graph', 'figure'),
#     [
#         Input('year-range-slider', 'value'),
#         Input('state-dropdown', 'value'),
#         Input('category-dropdown', 'value')
#     ]
# )
# def update_graph(year_range, selected_states, category):
#     print(f"[DEBUG] update_state_graph - Year Range: {year_range}, States: {selected_states}, Category: {category}")
#     # ... existing code ...

# Run the app
if __name__ == '__main__':
    app.run(debug=True)