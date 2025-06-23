# Enterprise Emissions Analytics Platform

A production-grade analytics platform that transforms greenhouse gas emissions data into actionable business intelligence. Built with modern data visualization technologies, this solution enables data-driven sustainability decisions across enterprise operations.

## Core Capabilities

- **Analytics Engine**: Processes and visualizes greenhouse gas emissions data
- **Interactive Visualization**: Custom-built dashboard components for emissions breakdown and trends
- **Data Processing**: Efficient data filtering and aggregation with caching
- **Compliance Support**: EPA subpart-based emissions tracking and reporting

## Technical Architecture

### Frontend
- **Framework**: Dash (React-based)
- **Data Visualization**: Plotly.js for interactive charts
- **Components**: Modular design with state and subpart breakdown graphs

### Backend
- **Data Processing**: Pandas with LRU caching and optimized aggregations
- **Storage Layer**: File-based data storage
- **State Management**: Dash callbacks with efficient data flow patterns

### DevOps
- **Containerization**: Docker with multi-stage builds
- **CI/CD**: Automated testing and deployment pipeline
- **Monitoring**: Integrated performance metrics and logging

## Performance Optimizations

- Implemented LRU caching for data queries with 128 entry cache size
- Optimized data processing with efficient Pandas operations
- Modular component architecture with separate state and subpart graphs

## Development

```bash
# Setup development environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Launch development server
python app.py
```

Access the development server at http://localhost:8050

### Feature Flag Configuration

Control enhanced features using environment variables:

```bash
# Enable enhanced subpart breakdown
export ENHANCED_SUBPART_BREAKDOWN=true

# Enable debug mode for development
export DEBUG_MODE=true

# Enable performance monitoring
export PERFORMANCE_MONITORING=true

# Run with enhanced features
python app.py
```

**Available Feature Flags:**
- `ENHANCED_SUBPART_BREAKDOWN` - Enable enhanced subpart breakdown with accurate percentages
- `DEBUG_MODE` - Enable debug logging and additional validation
- `SHOW_VALIDATION_WARNINGS` - Show data validation warnings in UI (default: true)
- `PERFORMANCE_MONITORING` - Enable performance monitoring and logging
- `STRICT_DATA_VALIDATION` - Enable strict data validation checks (default: true)

**Quick Start with Enhanced Features:**
```bash
ENHANCED_SUBPART_BREAKDOWN=true python app.py
```

## Project Structure

```
├── app.py                 # Application entry point
├── components/            # Reusable dashboard components
├── utils/                 # Data processing and optimization
├── assets/               # Static resources
└── tests/                # Comprehensive test suite
```

## Data Architecture

Optimized for enterprise-scale emissions data processing:
- Facility-level granularity
- Multi-dimensional analysis capabilities
- Real-time aggregation and filtering
- Automated data validation and cleaning

## Features

### Core Analytics
- Interactive state emissions time series visualization
- EPA subpart breakdown analysis with donut charts
- Multi-state and year range filtering capabilities
- Cached data processing for improved performance

### Enhanced Subpart Breakdown (Feature Flag Controlled)
- **Individual subpart representation** - Each color represents a single EPA subpart (no collections)
- **Accurate percentages** - Percentages sum to exactly 100% with proper rounding
- **Comma-separated subpart expansion** - Properly handles and expands comma-separated subpart values
- **Enhanced data validation** - Comprehensive data quality checks and error handling
- **Improved tooltips** - Detailed hover information with subpart definitions
- **Performance monitoring** - Optional performance tracking and validation warnings

### Feature Flag System
- **Safe deployment** - Gradual rollout capabilities with instant rollback
- **Environment-based configuration** - Control features via environment variables
- **Debug mode** - Enhanced logging and validation for development
- **Backward compatibility** - Seamless fallback to legacy components

## Deployment

### Production Deployment

```bash
# Build Docker image
docker build -t ghg-dashboard .

# Run with enhanced features enabled
docker run -p 8050:8050 \
  -e ENHANCED_SUBPART_BREAKDOWN=true \
  -e STRICT_DATA_VALIDATION=true \
  ghg-dashboard
```

### Gradual Rollout Strategy

1. **Stage 1**: Deploy with feature flags disabled (safe fallback)
2. **Stage 2**: Enable for 10% of users with monitoring
3. **Stage 3**: Gradually increase to 100% based on performance metrics
4. **Rollback**: Instantly disable via environment variables if issues arise

### Monitoring

- Enable `PERFORMANCE_MONITORING=true` for production metrics
- Monitor logs for validation warnings and errors
- Track percentage accuracy and data integrity
- Use `DEBUG_MODE=true` only in development environments

## Requirements

- Python 3.8+
- Dash 2.14.2+
- Pandas 2.1.4+
- Plotly 5.18.0+