import pandas as pd
from typing import List, Dict, Any, Optional

def filter_by_subpart(
    data: pd.DataFrame,
    selected_subparts: Optional[List[str]] = None
) -> pd.DataFrame:
    """Filter data by selected subparts (categories).
    
    Args:
        data: DataFrame containing emissions data
        selected_subparts: List of selected subpart codes
        
    Returns:
        Filtered DataFrame containing only matching subparts
    
    Raises:
        KeyError: If neither 'SUBPARTS' nor 'SUBPART' column is found in the data
    """
    # Return all data if no subparts are selected
    if not selected_subparts:
        return data
        
    # Determine which subpart column name is present
    if 'SUBPARTS' in data.columns:
        subpart_col = 'SUBPARTS'
    elif 'SUBPART' in data.columns:
        subpart_col = 'SUBPART'
    else:
        raise KeyError("No subpart column found in data. Expected 'SUBPARTS' or 'SUBPART'.")
    
    # Get valid codes from both mappings and existing data
    from .subpart_mappings import get_valid_subpart_codes
    
    # Get valid codes from both mappings and existing data
    valid_subparts = get_valid_subpart_codes(selected_subparts)
    
    # Handle comma-separated subpart codes
    def has_matching_subpart(subparts_str):
        if pd.isna(subparts_str):
            return False
        facility_subparts = [s.strip() for s in str(subparts_str).split(',')]
        return any(subpart in valid_subparts for subpart in facility_subparts)
    
    # If no valid subparts found, return all data
    if not valid_subparts:
        return data
        
    return data[data[subpart_col].apply(has_matching_subpart)]

def filter_and_aggregate_data(
    raw_data: pd.DataFrame,
    selected_states: Optional[List[str]] = None,
    year_range: Optional[List[int]] = None,
    selected_companies: Optional[List[str]] = None,
    selected_subparts: Optional[List[str]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter and aggregate emissions data based on selected criteria.
    
    Args:
        raw_data: DataFrame containing the raw emissions data
        selected_states: List of selected state codes
        year_range: List containing [start_year, end_year]
        selected_companies: List of selected parent company names
        selected_subparts: List of selected subpart categories
        
    Returns:
        Dictionary containing:
            - main_chart_data: List of dicts with keys 'state', 'year', 'value', 'subparts'
            - parent_chart_data: List of dicts for parent company breakdown
    """
    try:
        if raw_data.empty:
            print("[DEBUG] filter_and_aggregate_data - Input data is empty")
            return {'main_chart_data': [], 'parent_chart_data': []}

        print(f"[DEBUG] filter_and_aggregate_data - Initial data shape: {raw_data.shape}")
        print(f"[DEBUG] filter_and_aggregate_data - Year range: {year_range}")
        
        # Ensure required columns exist
        required_columns = ['REPORTING YEAR', 'STATE', 'GHG QUANTITY (METRIC TONS CO2e)', 'SUBPARTS']
        missing_columns = [col for col in required_columns if col not in raw_data.columns]
        if missing_columns:
            print(f"[ERROR] filter_and_aggregate_data - Missing required columns: {missing_columns}")
            return {'main_chart_data': [], 'parent_chart_data': []}

        # Convert data types and handle missing values
        raw_data = raw_data.copy()
        raw_data['REPORTING YEAR'] = pd.to_numeric(raw_data['REPORTING YEAR'], errors='coerce')
        raw_data['GHG QUANTITY (METRIC TONS CO2e)'] = pd.to_numeric(raw_data['GHG QUANTITY (METRIC TONS CO2e)'], errors='coerce')
        
        # Drop rows with missing values in critical columns
        raw_data = raw_data.dropna(subset=['REPORTING YEAR', 'STATE', 'GHG QUANTITY (METRIC TONS CO2e)'])
        
        print(f"[DEBUG] filter_and_aggregate_data - Available years: {sorted(raw_data['REPORTING YEAR'].unique())}")
        print(f"[DEBUG] filter_and_aggregate_data - Available states: {sorted(raw_data['STATE'].unique())}")

        # Apply filters
        mask = pd.Series(True, index=raw_data.index)
        
        if year_range and len(year_range) == 2:
            mask &= (raw_data['REPORTING YEAR'] >= year_range[0]) & \
                    (raw_data['REPORTING YEAR'] <= year_range[1])
            print(f"[DEBUG] filter_and_aggregate_data - Data points after year filter: {mask.sum()}")
        
        if selected_states and len(selected_states) > 0:
            mask &= raw_data['STATE'].isin(selected_states)
            print(f"[DEBUG] filter_and_aggregate_data - Data points after state filter: {mask.sum()}")
        
        filtered_data = raw_data[mask]
        
        if filtered_data.empty:
            print("[DEBUG] filter_and_aggregate_data - No data after applying filters")
            return {'main_chart_data': [], 'parent_chart_data': []}
        
        # Group and aggregate data
        grouped_data = filtered_data.groupby(['STATE', 'REPORTING YEAR']).agg({
            'GHG QUANTITY (METRIC TONS CO2e)': 'sum',
            'SUBPARTS': lambda x: ','.join(sorted(set(','.join(str(s) for s in x).split(','))))
        }).reset_index()
        
        # Format data for output
        main_chart_data = [{
            'state': str(row['STATE']),
            'year': int(row['REPORTING YEAR']),
            'value': float(row['GHG QUANTITY (METRIC TONS CO2e)']),
            'subparts': str(row['SUBPARTS'])
        } for _, row in grouped_data.iterrows()]
        
        print(f"[DEBUG] filter_and_aggregate_data - Processed {len(main_chart_data)} data points")
        if main_chart_data:
            print(f"[DEBUG] filter_and_aggregate_data - Sample data point: {main_chart_data[0]}")
            print(f"[DEBUG] filter_and_aggregate_data - Years in processed data: {sorted(set(d['year'] for d in main_chart_data))}")
        
        return {
            'main_chart_data': main_chart_data,
            'parent_chart_data': []
        }
        
    except Exception as e:
        print(f"[ERROR] filter_and_aggregate_data - Error processing data: {str(e)}")
        return {'main_chart_data': [], 'parent_chart_data': []}
    
    # Format data for plotting
    main_chart_data = []
    for _, row in filtered_data.groupby(['STATE', 'REPORTING YEAR']).agg({
        'GHG QUANTITY (METRIC TONS CO2e)': 'sum',
        'SUBPARTS': lambda x: ','.join(sorted(set(','.join(x).split(','))))
    }).reset_index().iterrows():
        main_chart_data.append({
            'state': str(row['STATE']),
            'year': int(row['REPORTING YEAR']),
            'value': float(row['GHG QUANTITY (METRIC TONS CO2e)']),
            'subparts': str(row['SUBPARTS'])
        })
    
    print(f"[DEBUG] filter_and_aggregate_data - Processed {len(main_chart_data)} data points")
    if main_chart_data:
        print(f"[DEBUG] filter_and_aggregate_data - Sample data point: {main_chart_data[0]}")
    
    # Format parent company data (placeholder for now)
    parent_chart_data = []
    
    return {
        'main_chart_data': main_chart_data,
        'parent_chart_data': parent_chart_data
    }
    
    # Create main chart data with standardized column names
    main_chart_data = [
        {
            'state': row['STATE'],
            'year': int(row['REPORTING YEAR']),  # Ensure year is integer
            'value': float(row['GHG QUANTITY (METRIC TONS CO2e)']),  # Ensure value is float
            'subparts': row['SUBPARTS'] if 'SUBPARTS' in row else row.get('SUBPART', '')
        }
        for _, row in filtered_data.iterrows()
    ]
    
    print(f"[DEBUG] filter_and_aggregate_data - Processed {len(main_chart_data)} data points")
    print(f"[DEBUG] filter_and_aggregate_data - Sample processed data: {main_chart_data[:2] if main_chart_data else []}")
    
    return {
        'main_chart_data': main_chart_data,
        'parent_chart_data': []  # Placeholder for parent company data
    }
    print(f"[DEBUG] filter_and_aggregate_data - Data shape after basic filters: {filtered_data.shape}")
    
    # Apply subpart filtering
    filtered_data = filter_by_subpart(filtered_data, selected_subparts)  # New filter applied
    print(f"[DEBUG] filter_and_aggregate_data - Data shape after subpart filter: {filtered_data.shape}")

    # Aggregate data for main chart
    main_chart_data = (
        filtered_data
        .groupby(['STATE', 'REPORTING YEAR', 'SUBPARTS'])['GHG QUANTITY (METRIC TONS CO2e)']  # Added SUBPARTS
        .sum()
        .round()
        .reset_index()
        .rename(columns={
            'STATE': 'state',  # Match state graph component column names
            'REPORTING YEAR': 'year',
            'GHG QUANTITY (METRIC TONS CO2e)': 'value',
            'SUBPARTS': 'subparts'  # Lowercase for consistency
        })
        .sort_values('year')  # Sort by lowercase year column name
        .to_dict('records')
    )

    # Filter and process parent company data
    parent_mask = mask.copy()
    if selected_companies and len(selected_companies) > 0:
        # Assuming 'PARENT COMPANIES' contains comma-separated values
        parent_mask &= raw_data['PARENT COMPANIES'].apply(
            lambda x: any(company in str(x).split(',') for company in selected_companies)
        )

    parent_data = raw_data[parent_mask]
    
    # Apply subpart filtering to parent company data as well
    parent_data = filter_by_subpart(parent_data, selected_subparts)  # Apply same subpart filter

    # Process parent company data
    parent_chart_data = (
        parent_data
        .groupby(['PARENT COMPANIES', 'REPORTING YEAR'])['GHG QUANTITY (METRIC TONS CO2e)']
        .sum()
        .round()
        .reset_index()
        .rename(columns={
            'PARENT COMPANIES': 'company',
            'REPORTING YEAR': 'year',
            'GHG QUANTITY (METRIC TONS CO2e)': 'value'
        })
        .sort_values(['company', 'year'])
        .to_dict('records')
    )

    return {
        'main_chart_data': main_chart_data,
        'parent_chart_data': parent_chart_data
    }