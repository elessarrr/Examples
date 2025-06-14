import pytest
import pandas as pd

@pytest.fixture
def sample_emissions_data():
    """Fixture to provide sample emissions data for testing"""
    return pd.DataFrame({
        'year': [2019, 2019, 2020, 2020],
        'state': ['CA', 'NY', 'CA', 'NY'],
        'SUBPART': ['C', 'D', 'C', 'D'],
        'EMISSIONS': [100, 200, 150, 250]
    })

@pytest.fixture
def mock_cache_data(sample_emissions_data):
    """Fixture to provide mock cache data"""
    return {
        'main_chart_data': sample_emissions_data.to_dict('records')
    }