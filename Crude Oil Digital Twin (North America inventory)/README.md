# Crude Oil Digital Twin Application

A sophisticated digital twin application for monitoring, analyzing, and simulating crude oil inventory across different PADD (Petroleum Administration for Defense Districts) regions. This application provides real-time visualization, trend analysis, and scenario-based simulations for better decision-making in crude oil inventory management.

## Features

### Real-time Monitoring
- Live inventory tracking across PADD regions
- Current WTI crude oil price integration
- Weekly data frequency updates
- Interactive metrics dashboard

### Advanced Visualization
- Multi-region inventory trend analysis
- Price-inventory correlation plots
- Interactive PADD region selector with map
- Risk gauge visualization for inventory levels

### Scenario Simulation
- Customizable simulation duration (4-52 weeks)
- Multiple scenario options:
  - Production Cut Scenario
  - Demand Spike Scenario
  - Strategic Reserve Release
- Daily consumption rate adjustment
- Risk assessment and impact analysis

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv venv_streamlit
source venv_streamlit/bin/activate  # On Windows: .\venv_streamlit\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run app_crude_odt_trae_13Mar_v2.py
```

2. Select PADD Region:
   - Use the sidebar to choose a specific PADD region
   - View the PADD region map for reference

3. Configure Simulation Parameters:
   - Adjust simulation duration
   - Set daily consumption rate
   - Toggle different scenario options

4. Analyze Results:
   - Monitor inventory trends
   - Review risk assessments
   - Evaluate scenario impacts

## Technical Architecture

### Module Structure

- **data_handler_v3.py**: Data processing and management
- **simulation_v3.py**: Scenario simulation engine
- **visualization_v4.py**: Data visualization and UI components

### Key Components

1. **Data Handling**
   - Historical data processing
   - Real-time data integration
   - Data validation and error handling

2. **Simulation Engine**
   - Scenario-based modeling
   - Risk calculation
   - Impact assessment

3. **Visualization Layer**
   - Interactive plots using Plotly
   - Streamlit UI components
   - Real-time metric updates

## Error Handling

The application implements comprehensive error handling through decorators and try-except blocks to ensure robust operation and meaningful error messages.

## Dependencies

- streamlit
- plotly
- pandas
- numpy
- python-dotenv

## Best Practices

1. **Data Refresh**: Update data regularly for accurate analysis
2. **Scenario Testing**: Test multiple scenarios for comprehensive analysis
3. **Risk Monitoring**: Regularly check risk indicators
4. **Parameter Adjustment**: Fine-tune simulation parameters based on market conditions

## Support

For issues and feature requests, please create an issue in the repository.

## License

This project is proprietary and confidential. All rights reserved.