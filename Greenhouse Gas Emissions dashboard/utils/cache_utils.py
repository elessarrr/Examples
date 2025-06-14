from functools import lru_cache
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple

@lru_cache(maxsize=128)
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
    
    # Load data - replace with your actual data loading logic
    try:
        import os
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'emissions_data.xlsx')
        print(f"[DEBUG] get_cached_data - Loading data from: {data_path}")
        
        # Read all sheets from the Excel file
        xl = pd.ExcelFile(data_path)
        print(f"[DEBUG] get_cached_data - Available sheets: {xl.sheet_names}")
        
        # Read and combine all sheets
        raw_data = pd.concat([pd.read_excel(xl, sheet_name=sheet) for sheet in xl.sheet_names])
        print(f"[DEBUG] get_cached_data - Initial data loaded with {len(raw_data)} rows")
        print(f"[DEBUG] get_cached_data - Columns: {raw_data.columns.tolist()}")
        
        # Verify and print unique years in the data
        if 'REPORTING YEAR' in raw_data.columns:
            available_years = sorted(raw_data['REPORTING YEAR'].unique())
            print(f"[DEBUG] get_cached_data - Available years in data: {available_years}")
            
            # Only override year_range if not provided
            if not years:
                years = [min(available_years), max(available_years)]
                print(f"[DEBUG] get_cached_data - Using full year range: {years}")
        
        print(f"[DEBUG] get_cached_data - Sample data:\n{raw_data.head(2)}")
        
        # Convert category filter to list
        categories = list(category_filter) if category_filter else None
        
        # Call filter_and_aggregate_data with the processed filters
        result = filter_and_aggregate_data(
            raw_data=raw_data,
            selected_states=states,
            year_range=years,
            selected_companies=companies,
            selected_subparts=categories
        )
        
        print(f"[DEBUG] get_cached_data - Filtered data points: {len(result.get('main_chart_data', []))}")
        print(f"[DEBUG] get_cached_data - Sample filtered data:\n{result['main_chart_data'][:2] if result['main_chart_data'] else 'No data'}")
        return result
        
    except Exception as e:
        print(f"[ERROR] get_cached_data - Error loading or processing data: {str(e)}")
        return {'main_chart_data': []}

def clear_data_cache():
    """Clear the cached data when needed (e.g., after data updates)"""
    get_cached_data.cache_clear()