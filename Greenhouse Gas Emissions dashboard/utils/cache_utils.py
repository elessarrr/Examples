# Context:
# This module implements caching strategies for the emissions dashboard to improve performance.
# It provides LRU (Least Recently Used) caching for data queries to reduce database/file access
# and computation overhead. The cache is optimized for common query patterns and sized based
# on typical data access patterns in the application.
# 
# The module now uses Parquet format for data storage, which provides:
# - Faster data loading (10-100x faster than Excel)
# - Column-based storage for efficient querying
# - Better compression for reduced memory usage
# - Native support for categorical data types

from functools import lru_cache
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from .data_preprocessor import DataPreprocessor

# Increased cache size to accommodate more unique filter combinations
# 512 entries can store ~2 hours of active user sessions with different filter combinations
# while keeping memory usage reasonable (estimated ~100MB for typical payload sizes)
@lru_cache(maxsize=512)
def get_cached_data(
    state_filter: Optional[Tuple[str, ...]] = None,
    year_range: Optional[Tuple[int, int]] = None,
    company_filter: Optional[Tuple[str, ...]] = None,
    category_filter: Optional[Tuple[str, ...]] = None
) -> Dict[str, Any]:
    """Cached version of data filtering and aggregation.
    
    Args:
        state_filter: Tuple of selected state codes (immutable for caching)
        year_range: Tuple of (start_year, end_year)
        company_filter: Tuple of selected company names
        category_filter: Tuple of selected subpart categories (immutable for caching)
    
    Returns:
        Dictionary containing cached aggregated data
    """
    from .aggregation import filter_and_aggregate_data
    
    # Convert tuple filters back to lists for the underlying function
    states = list(state_filter) if state_filter else None
    companies = list(company_filter) if company_filter else None
    years = list(year_range) if year_range else None
    
    # Load data from Parquet using the preprocessor
    try:
        preprocessor = DataPreprocessor()
        raw_data = preprocessor.load_data()
        
        # Set year range if not provided
        if not years and 'REPORTING YEAR' in raw_data.columns:
            years = [int(raw_data['REPORTING YEAR'].min()), int(raw_data['REPORTING YEAR'].max())]
        
        # Convert category filter to list
        categories = list(category_filter) if category_filter else None
        
        # Process data with filters
        result = filter_and_aggregate_data(
            raw_data=raw_data,
            selected_states=states,
            year_range=years,
            selected_companies=companies,
            selected_subparts=categories
        )
        
        return result
        
    except Exception as e:
        print(f"[ERROR] get_cached_data - Error loading or processing data: {str(e)}")
        return {'main_chart_data': []}

@lru_cache(maxsize=2)
def get_cached_layout(chart_type: str) -> Dict[str, Any]:
    """Get cached layout configuration for charts.
    
    Args:
        chart_type: Type of chart ('state' or 'subpart')
    
    Returns:
        Dictionary containing Plotly layout configuration
    """
    if chart_type == 'state':
        return {
            'title': 'State GHG Emissions Over Time',
            'height': 500,
            'margin': {'l': 50, 'r': 20, 't': 50, 'b': 50},
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5,
                'font': {'size': 10},
                'itemwidth': 30
            },
            'xaxis': {'title': 'Year'},
            'yaxis': {'title': 'Emissions (MT CO2e)'}
        }
    elif chart_type == 'subpart':
        return {
            'height': 500,
            'margin': {'l': 20, 'r': 20, 't': 50, 'b': 50},
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5,
                'font': {'size': 10},
                'itemwidth': 30
            },
            'showlegend': True
        }
    return {}

def clear_data_cache():
    """Clear all cached data when needed (e.g., after data updates)"""
    get_cached_data.cache_clear()
    get_cached_layout.cache_clear()