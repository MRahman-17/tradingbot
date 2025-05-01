# Quantum Trading System

A sophisticated trading system that integrates quantum computing algorithms with traditional technical analysis to make advanced market predictions and automated trading decisions.

## System Overview

This project implements a complete automated trading system that leverages quantum computing technology alongside classical analysis methods. The system features multiple components that work together:

- A core trading engine that makes buy/sell decisions
- Market sentiment analysis from financial news
- Comprehensive monitoring and reporting
- Self-improvement mechanisms to enhance performance over time
- Halal compliance verification for Islamic finance compatibility

## Key Components

### Core Trading Scripts

- **trading_bot.py**: The main trading engine that integrates quantum and classical analysis to make trading decisions. Implements feature encoding in quantum circuits for market prediction while accounting for quantum error rates.

- **main.py**: System initialization and coordination. Responsible for starting all components and managing the overall system lifecycle.

- **platform_adapters/**: Directory containing platform-specific adapters for connecting to different trading platforms. Uses a factory pattern to abstract away platform-specific details.

### Financial News Analysis

- **financial_news_module.py**: Collects and analyzes financial news, fear & greed indices, and social media sentiment to provide market sentiment analysis for making more informed trading decisions.

- **news_trading_integration.py**: Integrates news sentiment analysis with the core trading bot and quantum components, providing a weighted signal that combines technical, quantum, and news-based factors.

- **trading_bot_news_integration.py**: Helper utilities to patch the trading bot with news integration capabilities.

### Monitoring & Reporting

- **monitor_bot.py**: Monitors system performance, checks API health, and generates comprehensive performance reports. Includes specialized quantum system monitoring capabilities.

- **verify_system.py**: Verification script to check if all dependencies and authentication are working correctly before starting the system.

- **utils.py**: Utility functions for heartbeat monitoring and activity logging.

### Self-Improvement

- **improvement_bot.py**: Continuously debugs and improves the trading system by monitoring code quality, optimizing machine learning models, and managing system snapshots. Includes specialized quantum circuit optimization.

## Quantum Computing Integration

This system leverages quantum computing for market prediction in several innovative ways:

1. **Quantum Feature Mapping**: Classical market data is encoded into quantum states using amplitude encoding techniques
2. **Quantum Circuit Optimization**: Circuits are periodically optimized to reduce error rates and improve prediction accuracy
3. **Error Rate Management**: The system monitors quantum device error rates and dynamically adjusts its reliance on quantum vs. classical signals
4. **Quantum Portfolio Optimization**: Uses quantum algorithms to optimize portfolio allocation across multiple assets

## Installation

1. Clone this repository
2. Install required dependencies:
   ```
   pip install numpy pandas matplotlib cryptography requests schedule joblib scikit-learn
   ```
3. Optional quantum components:
   ```
   pip install pennylane qiskit qiskit-aer
   ```
4. Create required directories:
   ```
   mkdir -p logs models data config platform_adapters security/encryption legal/compliance_reports
   ```

## Configuration

Before running the system, configure the following files:

1. **config/config.json**: Main configuration file with parameters for trading strategy and quantum settings
2. **config/secrets.env**: Environment variables for API credentials (see template in main.py)

## Usage

Start the complete system:

```
python main.py
```

Run individual components for testing:

```
python trading_bot.py       # Run only the trading bot
python monitor_bot.py       # Run only the monitoring component
python improvement_bot.py   # Run only the self-improvement component
```

Verify system setup:

```
python verify_system.py
```

## Architecture Diagram

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  Trading Bot  │◄────┤    Main.py    │────►│  Monitor Bot  │
└───────┬───────┘     └───────────────┘     └───────┬───────┘
        │                      ▲                    │
        │                      │                    │
        ▼                      │                    ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ News Analysis │     │ Improvement   │     │  Performance  │
│    Module     │     │     Bot       │     │    Reports    │
└───────────────┘     └───────────────┘     └───────────────┘
```

## Performance Metrics

The system tracks and reports on several key performance metrics:

- Win rate and profit/loss statistics
- Maximum drawdown
- Quantum prediction accuracy
- API health and system status
- Trading signal quality by source (quantum vs. classical)

All metrics are available in the `data/performance/` directory.

## Legal & Compliance

The system includes built-in compliance checks for:

- Halal investment compliance using the Zoya API
- Minimum holding periods to avoid pattern day trading restrictions
- Automatic system backups and audit trails

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
