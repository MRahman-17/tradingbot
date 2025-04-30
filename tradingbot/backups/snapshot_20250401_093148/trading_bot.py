#!/usr/bin/env python3
"""
Enhanced Trading Bot with Quantum Computing Market Analysis
Integrates quantum computing for market prediction while accounting for error rates
"""
import os
import sys
import time
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime
import random
import requests
from cryptography.fernet import Fernet
import signal
import threading


def check_halal_compliance(symbol):
    """
    Check if a stock is halal compliant using the Zoya API with GraphQL

    Args:
        symbol (str): Stock symbol to check (e.g., 'AAPL')

    Returns:
        bool: True if stock is compliant, False if not
    """
    try:
        api_key = os.environ.get("ZOYA_API_KEY")
        if not api_key:
            logger.error("Zoya API key not found in environment variables")
            return False

        # Zoya API endpoint for GraphQL
        url = "https://api.zoya.finance/graphql"

        # GraphQL query
        query = """
        query getReport {
          basicCompliance {
            report(symbol: "%s") {
              exchange
              name
              reportDate
              status
              symbol
            }
          }
        }
        """ % symbol

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Prepare the GraphQL request
        request_data = {
            "query": query
        }

        response = requests.post(url, headers=headers, json=request_data)

        if response.status_code == 200:
            data = response.json()

            # Extract compliance status from GraphQL response
            try:
                status = data.get("data", {}).get("basicCompliance", {}).get("report", {}).get("status")

                logger.info(f"Zoya API compliance check for {symbol}: {status}")

                # Return True if compliant, False otherwise
                return status == "COMPLIANT"
            except (KeyError, TypeError) as e:
                logger.error(f"Error parsing Zoya API response: {e}")
                logger.debug(f"Response data: {data}")
                return False
        else:
            logger.error(f"Error calling Zoya API: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error checking halal compliance: {e}")
        return False


# For testing purposes only, you could add this temporary mock implementation
# while you resolve API issues
def mock_check_halal_compliance(symbol):
    """
    Mock function to check halal compliance for testing without API

    Args:
        symbol (str): Stock symbol to check

    Returns:
        bool: Hardcoded compliance status
    """
    # Define known compliant stocks (customize this list as needed)
    compliant_stocks = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "V", "ADBE"]

    is_compliant = symbol in compliant_stocks
    logger.info(f"Mock halal compliance check for {symbol}: {'COMPLIANT' if is_compliant else 'NON_COMPLIANT'}")

    return is_compliant


# To use the mock version temporarily, replace the call to check_halal_compliance
# with mock_check_halal_compliance in your make_trading_decision function:
#
# if config.get("trading_bot", {}).get("halal_compliance", True):
#     is_halal = mock_check_halal_compliance(symbol)
#     if not is_halal:
#         logger.info(f"{symbol} is not halal compliant, skipping")
#         return

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Quantum Trading Bot")

# Quantum computing libraries - add more verbose output
QUANTUM_AVAILABLE = False  # Default to False
try:
    logger.info("Attempting to import quantum libraries...")
    import pennylane as qml
    import qiskit
    from qiskit import QuantumCircuit
    from qiskit_aer import Aer  # Separate import for Aer
    from qiskit_aer import AerSimulator

    QUANTUM_AVAILABLE = True
    logger.info(f"Quantum libraries successfully imported: PennyLane {qml.__version__}, Qiskit {qiskit.__version__}")
except ImportError as e:
    logger.warning(f"Quantum libraries not available: {str(e)}. Will use classical analysis only.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Quantum Trading Bot")

# Default configuration
DEFAULT_CONFIG = {
    "trading_bot": {
        "enabled": True,
        "symbols": ["AAPL", "MSFT", "NVDA"],
        "max_drawdown": 0.05,
        "kelly_fraction": 0.02,
        "quantity": 1,
        "min_hold_period": 172800,  # 48 hours in seconds
        "sleep_time": 60,
        "halal_compliance": True
    },
    "quantum_config": {
        "enabled": True,
        "error_threshold": 0.15,  # Maximum acceptable error rate
        "min_confidence": 0.65,  # Minimum confidence to consider quantum signals
        "device": "default.qubit",  # Use simulator by default
        "shots": 1000,  # Number of quantum measurements
        "use_error_mitigation": True,
        "fallback_to_classical": True
    },
    "platform": {
        "name": "mock",  # Using mock platform for testing
        "use_paper_trading": True
    }
}

# Trading parameters
symbols = DEFAULT_CONFIG["trading_bot"]["symbols"]
sleep_time = DEFAULT_CONFIG["trading_bot"]["sleep_time"]

# Global variables
platform_adapter = None
trade_history = {"positions": {}, "trades": []}
quantum_error_history = []
quantum_prediction_history = []


class MockAdapter:
    """Enhanced mock adapter for simulating trading with realistic market data"""

    def __init__(self):
        self.positions = {}
        self.prices = {
            "AAPL": 175.0,
            "MSFT": 350.0,
            "NVDA": 141.0
        }
        self.order_id = 1000
        self.market_data = {}
        logger.info("Mock adapter initialized")

        # Initialize with some simulated historical data
        self._initialize_market_data()

    def _initialize_market_data(self):
        """Create realistic simulated market data with trends and patterns"""
        for symbol in self.prices.keys():
            # Generate 90 days of realistic data
            days = 90
            base_price = self.prices[symbol]

            # Create time series with realistic properties
            # Start with random walk
            random_walk = np.random.normal(0, 0.015, days).cumsum()

            # Add trend component
            trend = np.linspace(0, 0.2, days) if symbol in ["AAPL", "MSFT"] else np.linspace(0, -0.1, days)

            # Add cyclical component (weekly pattern)
            cyclical = 0.02 * np.sin(np.linspace(0, 6 * np.pi, days))

            # Combine components
            price_series = base_price * (1 + random_walk + trend + cyclical)

            # Create more realistic volume
            volume = np.random.randint(1000000, 10000000, days)

            # Create dataframe with OHLCV data
            dates = pd.date_range(end=datetime.now(), periods=days)
            df = pd.DataFrame({
                'Date': dates,
                'Open': price_series * (1 - np.random.uniform(0, 0.01, days)),
                'High': price_series * (1 + np.random.uniform(0, 0.02, days)),
                'Low': price_series * (1 - np.random.uniform(0, 0.02, days)),
                'Close': price_series,
                'Volume': volume
            })

            # Set the current price to the last close
            self.prices[symbol] = float(df['Close'].iloc[-1])

            # Store the dataframe
            self.market_data[symbol] = df

    def get_price(self, symbol):
        """Get current price with some realistic movement"""
        if symbol not in self.prices:
            self.prices[symbol] = 100.0

        price = self.prices[symbol]
        # Add some random movement with momentum
        change = np.random.normal(0, 0.01)
        # Add momentum (prices tend to continue in the same direction)
        if len(self.market_data.get(symbol, [])) > 0:
            df = self.market_data[symbol]
            if len(df) >= 2:
                last_change = (df['Close'].iloc[-1] / df['Close'].iloc[-2]) - 1
                change = change + (last_change * 0.3)  # 30% momentum factor

        self.prices[symbol] = price * (1 + change)

        # Update the market data
        if symbol in self.market_data:
            new_row = pd.DataFrame({
                'Date': [datetime.now()],
                'Open': [price],
                'High': [price * (1 + max(0, change * 1.5))],
                'Low': [price * (1 + min(0, change * 1.5))],
                'Close': [self.prices[symbol]],
                'Volume': [np.random.randint(1000000, 5000000)]
            })
            self.market_data[symbol] = pd.concat([self.market_data[symbol], new_row])

        return self.prices[symbol]

    def get_positions(self):
        """Get current positions"""
        positions = []
        for symbol, details in self.positions.items():
            current_price = self.get_price(symbol)
            entry_price = details["entry_price"]
            quantity = details["quantity"]

            # Calculate P&L
            unrealized_pl = (current_price - entry_price) * quantity
            unrealized_pl_pct = (current_price / entry_price - 1) * 100

            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current_price,
                "unrealized_pl": unrealized_pl,
                "unrealized_pl_percent": unrealized_pl_pct
            })

        return positions

    def place_order(self, symbol, side, quantity):
        """Place a mock order"""
        self.order_id += 1
        current_price = self.get_price(symbol)

        if side.lower() == "buy":
            self.positions[symbol] = {
                "entry_price": current_price,
                "quantity": quantity
            }
            logger.info(f"BUY order for {quantity} shares of {symbol} at ${current_price:.2f}")
        elif side.lower() == "sell":
            if symbol in self.positions:
                del self.positions[symbol]
                logger.info(f"SELL order for {quantity} shares of {symbol} at ${current_price:.2f}")
            else:
                logger.warning(f"Cannot sell {symbol} - no position")
                return None

        return self.order_id

    def get_market_data(self, symbol, interval='1d', count=90):
        """Get historical market data for a symbol"""
        if symbol not in self.market_data:
            # Create random data if we don't have it
            self._initialize_market_data()

        df = self.market_data[symbol].copy()
        if len(df) > count:
            df = df.iloc[-count:]

        # Calculate common technical indicators
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_10'] = df['Close'].rolling(10).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['EMA_5'] = df['Close'].ewm(span=5).mean()
        df['EMA_10'] = df['Close'].ewm(span=10).mean()
        df['EMA_20'] = df['Close'].ewm(span=20).mean()

        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        df['MACD'] = df['EMA_12'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # Bollinger Bands
        df['BB_Middle'] = df['SMA_20']
        df['BB_Upper'] = df['BB_Middle'] + 2 * df['Close'].rolling(20).std()
        df['BB_Lower'] = df['BB_Middle'] - 2 * df['Close'].rolling(20).std()

        # Fill NaN values
        df = df.bfill()

        return df


def load_config():
    """Load configuration from file or use defaults"""
    config_path = "config/config.json"
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config
        else:
            logger.info("No configuration found, using defaults")
            # Create default config
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return DEFAULT_CONFIG


def load_trade_history():
    """Load trade history from file"""
    global trade_history
    try:
        if os.path.exists("data/trade_history.json"):
            with open("data/trade_history.json", "r") as f:
                trade_history = json.load(f)
                logger.info("Trade history loaded")
        else:
            logger.info("No trade history found, using empty")
    except Exception as e:
        logger.error(f"Error loading trade history: {e}")


def save_trade_history():
    """Save trade history to file"""
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/trade_history.json", "w") as f:
            json.dump(trade_history, f, indent=4)
            logger.info("Trade history saved")
    except Exception as e:
        logger.error(f"Error saving trade history: {e}")


def save_performance_metrics():
    """Save basic performance metrics"""
    try:
        trades = trade_history["trades"]
        if not trades:
            logger.info("No trades to analyze")
            return

        # Calculate metrics
        sell_trades = [t for t in trades if t["action"] == "SELL"]
        if not sell_trades:
            logger.info("No completed trades to analyze")
            return

        # Calculate performance metrics
        total_profit = sum(t.get("profit_loss", 0) for t in sell_trades)
        avg_profit = total_profit / len(sell_trades)
        avg_profit_pct = sum(t.get("profit_loss_pct", 0) for t in sell_trades) / len(sell_trades)

        winning_trades = sum(1 for t in sell_trades if t.get("profit_loss", 0) > 0)
        win_rate = winning_trades / len(sell_trades)

        # Calculate max drawdown
        equity_curve = []
        current_equity = 10000  # Start with $10,000
        for trade in trades:
            if trade["action"] == "SELL":
                current_equity += trade.get("profit_loss", 0)
            equity_curve.append(current_equity)

        if equity_curve:
            max_equity = equity_curve[0]
            max_drawdown = 0
            for equity in equity_curve:
                max_equity = max(max_equity, equity)
                drawdown = (max_equity - equity) / max_equity * 100
                max_drawdown = max(max_drawdown, drawdown)
        else:
            max_drawdown = 0

        # Include quantum metrics if available
        quantum_accuracy = None
        if quantum_prediction_history:
            correct_predictions = sum(1 for p in quantum_prediction_history if p["correct"])
            quantum_accuracy = correct_predictions / len(quantum_prediction_history)

        # Save metrics
        metrics = {
            "date": datetime.now().isoformat(),
            "total_trades": len(sell_trades),
            "winning_trades": winning_trades,
            "win_rate": win_rate,
            "total_profit": float(total_profit),
            "avg_profit": float(avg_profit),
            "avg_profit_pct": float(avg_profit_pct),
            "max_drawdown": float(max_drawdown),
            "quantum_accuracy": quantum_accuracy
        }

        # Create metrics file
        os.makedirs("data/performance", exist_ok=True)
        metrics_path = "data/performance/metrics.json"

        # Load existing or create new
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, "r") as f:
                    all_metrics = json.load(f)
            except:
                all_metrics = []
        else:
            all_metrics = []

        all_metrics.append(metrics)

        # Save metrics
        with open(metrics_path, "w") as f:
            json.dump(all_metrics, f, indent=4)

        logger.info(f"Performance metrics saved: {winning_trades}/{len(sell_trades)} winning trades")

        if quantum_accuracy is not None:
            logger.info(f"Quantum prediction accuracy: {quantum_accuracy:.2f}")

    except Exception as e:
        logger.error(f"Error saving performance metrics: {e}")


def initialize_quantum_device(config):
    """Initialize the quantum device based on configuration"""
    if not QUANTUM_AVAILABLE:
        logger.warning("Quantum libraries not available. Cannot initialize quantum device.")
        return None

    try:
        device_name = config.get("quantum_config", {}).get("device", "default.qubit")
        shots = config.get("quantum_config", {}).get("shots", 1000)

        if device_name == "default.qubit":
            # Use PennyLane's default simulator
            dev = qml.device(device_name, wires=5, shots=shots)
            logger.info(f"Initialized PennyLane quantum device: {device_name}")
            return dev
        elif "aer" in device_name:
            # Use Qiskit's simulator through PennyLane
            dev = qml.device('qiskit.aer', wires=5, shots=shots)
            logger.info(f"Initialized Qiskit Aer simulator through PennyLane")
            return dev
        else:
            # Try to initialize requested device
            dev = qml.device(device_name, wires=5, shots=shots)
            logger.info(f"Initialized quantum device: {device_name}")
            return dev
    except Exception as e:
        logger.error(f"Error initializing quantum device: {e}")
        logger.info("Falling back to default simulator")
        try:
            return qml.device("default.qubit", wires=5, shots=1000)
        except:
            logger.error("Failed to initialize fallback device")
            return None


def calibrate_quantum_measurements(backend, num_qubits):
    """Calibrate quantum measurements to reduce readout errors - updated for new Qiskit API"""
    if not QUANTUM_AVAILABLE:
        return None

    try:
        # Create a simulator with noise model (simplified approach for newer Qiskit)
        simulator = AerSimulator()
        logger.info("Created AerSimulator for quantum measurements")
        return simulator  # Return the simulator as our "filter"
    except Exception as e:
        logger.error(f"Error calibrating quantum measurements: {e}")
        return None


def estimate_quantum_error_rate(dev):
    """Estimate the current error rate of the quantum device"""
    if not QUANTUM_AVAILABLE or dev is None:
        return 1.0  # Maximum error if quantum not available

    try:
        # Define a simple circuit that should return a known result
        @qml.qnode(dev)
        def test_circuit():
            qml.Hadamard(wires=0)
            qml.CNOT(wires=[0, 1])
            return qml.expval(qml.PauliZ(0)), qml.expval(qml.PauliZ(1))

        # Run the circuit multiple times
        results = []
        for _ in range(10):
            results.append(test_circuit())

        # Calculate the error rate based on deviation from expected values
        # For this circuit, we expect the expectation values to be close to 0
        errors = [abs(r[0]) + abs(r[0] + r[1]) for r in results]
        error_rate = sum(errors) / len(errors) / 2  # Normalize to [0, 1]

        # Log the error rate
        logger.info(f"Quantum device error rate: {error_rate:.4f}")

        # Save to error history
        quantum_error_history.append({
            "timestamp": datetime.now().isoformat(),
            "error_rate": float(error_rate)
        })

        # Save error history to file
        os.makedirs("data/quantum", exist_ok=True)
        with open("data/quantum/error_history.json", "w") as f:
            json.dump(quantum_error_history, f, indent=4)

        return error_rate
    except Exception as e:
        logger.error(f"Error estimating quantum error rate: {e}")
        return 1.0  # Assume maximum error on failure


def quantum_feature_map(x, wires):
    """Apply a quantum feature map to encode classical data into quantum state"""
    # Normalize input features
    x_norm = x / np.linalg.norm(x)

    # Encode features into rotation angles
    for i, xi in enumerate(x_norm):
        qml.RY(xi * np.pi, wires=i % len(wires))

    # Entangle qubits
    for i in range(len(wires) - 1):
        qml.CNOT(wires=[wires[i], wires[i + 1]])


def classical_decision(historical_data):
    """Make a trading decision using classical methods"""
    # Extract features from the data
    df = historical_data.copy()

    # Check for trend based on moving averages
    last_row = df.iloc[-1]

    # Uptrend conditions
    uptrend = (
            last_row['SMA_5'] > last_row['SMA_20'] and
            last_row['Close'] > last_row['SMA_10'] and
            last_row['RSI'] > 50 and last_row['RSI'] < 70
    )

    # Downtrend conditions
    downtrend = (
            last_row['SMA_5'] < last_row['SMA_20'] and
            last_row['Close'] < last_row['SMA_10'] and
            last_row['RSI'] < 50 and last_row['RSI'] > 30
    )

    # Determine signal
    if uptrend:
        signal = random.uniform(0.7, 0.9)  # Strong buy signal
    elif downtrend:
        signal = random.uniform(0.1, 0.3)  # Strong sell signal
    else:
        signal = random.uniform(0.4, 0.6)  # Neutral

    return signal


def quantum_prediction(symbol, historical_data, quantum_device, error_rate, config):
    """Generate trading prediction using quantum computing"""
    if not QUANTUM_AVAILABLE or quantum_device is None:
        logger.warning("Quantum libraries or device not available. Using classical method.")
        return classical_decision(historical_data), 0.0, 1.0

    min_confidence = config.get("quantum_config", {}).get("min_confidence", 0.65)
    use_error_mitigation = config.get("quantum_config", {}).get("use_error_mitigation", True)

    try:
        # Prepare features
        df = historical_data.tail(10).copy()  # Use last 10 days

        # Create feature vector (normalize each feature)
        features = np.array([
            (df['Close'].pct_change().fillna(0).values[-5:] + 1) / 2,  # Price changes
            (df['RSI'].values[-5:] / 100),  # RSI scaled to [0, 1]
            ((df['SMA_5'] / df['SMA_20']).values[-5:] - 0.8) / 0.4,  # MA ratio normalized
        ]).flatten()

        # Limit features to number of qubits available and ensure in [0, 1]
        features = features[:5]
        features = np.clip(features, 0, 1)

        # Define the quantum circuit for prediction
        @qml.qnode(quantum_device, diff_method="parameter-shift")
        def quantum_circuit(features, weights):
            # Encode features
            quantum_feature_map(features, wires=range(len(features)))

            # Variational layer
            for i in range(len(features)):
                qml.Rot(weights[i, 0], weights[i, 1], weights[i, 2], wires=i)

            for i in range(len(features) - 1):
                qml.CNOT(wires=[i, i + 1])

            # Final rotation
            qml.RY(weights[-1, 0], wires=0)

            # Return probability of measuring |1⟩ on first qubit
            return qml.expval(qml.PauliZ(0))

        # Initialize random weights if not pre-trained
        weights_file = f"models/quantum_weights_{symbol}.npy"
        if os.path.exists(weights_file):
            weights = np.load(weights_file)
        else:
            weights = np.random.uniform(low=-np.pi, high=np.pi, size=(len(features) + 1, 3))

        # Apply error mitigation if enabled
        if use_error_mitigation and error_rate > 0.05:
            # Simple error mitigation by running multiple times and taking average
            results = []
            for _ in range(5):
                results.append(quantum_circuit(features, weights))

            # Average results and apply error correction factor
            raw_result = sum(results) / len(results)

            # Apply error correction factor (linear correction)
            # For high error rates, pull result toward 0 (neutral)
            corrected_result = raw_result * (1 - error_rate)
        else:
            # Single run without error mitigation
            raw_result = quantum_circuit(features, weights)
            corrected_result = raw_result

        # Convert from (-1, 1) range to (0, 1) for trading signal
        trading_signal = (1 - corrected_result) / 2

        # Calculate confidence based on error rate
        confidence = max(0, 1 - error_rate)

        # Adjust confidence if signal is near 0.5 (uncertain)
        if abs(trading_signal - 0.5) < 0.1:
            confidence *= 0.8

        # Fallback to classical if confidence is too low
        if confidence < min_confidence:
            logger.info(f"Quantum confidence ({confidence:.2f}) below threshold. Using classical method.")
            classical_signal = classical_decision(historical_data)
            # Blend signals based on confidence
            blended_signal = (confidence * trading_signal +
                              (1 - confidence) * classical_signal)
            return blended_signal, confidence, error_rate

        logger.info(f"Quantum prediction for {symbol}: {trading_signal:.4f} (confidence: {confidence:.4f})")
        return trading_signal, confidence, error_rate

    except Exception as e:
        logger.error(f"Error in quantum prediction: {e}")
        logger.info("Falling back to classical method")
        return classical_decision(historical_data), 0.0, 1.0


def make_trading_decision(symbol, quantum_device, config):
    """Trading decision logic with quantum and classical integration"""
    # First check if the stock is halal compliant
    if config.get("trading_bot", {}).get("halal_compliance", True):
        is_halal = mock_check_halal_compliance(symbol)
        if not is_halal:
            logger.info(f"{symbol} is not halal compliant, skipping")
            return
    # Get historical data
    historical_data = platform_adapter.get_market_data(symbol)

    # Check if we have a position
    has_position = symbol in trade_history["positions"]

    # Get quantum configuration
    quantum_enabled = config.get("quantum_config", {}).get("enabled", True)
    error_threshold = config.get("quantum_config", {}).get("error_threshold", 0.15)
    fallback_to_classical = config.get("quantum_config", {}).get("fallback_to_classical", True)

    # Estimate current error rate of quantum device
    error_rate = estimate_quantum_error_rate(quantum_device) if quantum_enabled else 1.0

    signal = 0.5  # Neutral default
    signal_source = "classical"
    confidence = 0.0

    # Decide on analysis method based on error rate
    if quantum_enabled and error_rate <= error_threshold:
        # Use quantum prediction
        signal, confidence, actual_error = quantum_prediction(
            symbol, historical_data, quantum_device, error_rate, config
        )
        signal_source = "quantum"
    elif quantum_enabled and fallback_to_classical:
        # Fallback to classical due to high error rate
        logger.info(f"Quantum error rate ({error_rate:.4f}) above threshold. Using classical method.")
        signal = classical_decision(historical_data)
        signal_source = "classical (fallback)"
    else:
        # Use classical method only
        signal = classical_decision(historical_data)
        signal_source = "classical"

    # Log the decision
    logger.info(f"Trading signal for {symbol}: {signal:.4f} (source: {signal_source})")

    # Make trading decision based on signal
    if signal > 0.7 and not has_position:
        logger.info(f"BUY signal for {symbol} (score: {signal:.4f}, source: {signal_source})")
        execute_trade("BUY", symbol)
    elif signal < 0.3 and has_position:
        logger.info(f"SELL signal for {symbol} (score: {signal:.4f}, source: {signal_source})")
        execute_trade("SELL", symbol)
    else:
        logger.info(f"HOLD signal for {symbol} (score: {signal:.4f}, source: {signal_source})")

    # Record prediction for later accuracy assessment
    if signal_source.startswith("quantum"):
        quantum_prediction_history.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "error_rate": error_rate,
            "action": "BUY" if signal > 0.7 and not has_position else
            "SELL" if signal < 0.3 and has_position else "HOLD",
            "correct": None  # Will be updated later when we can evaluate
        })

        # Save prediction history
        os.makedirs("data/quantum", exist_ok=True)
        with open("data/quantum/prediction_history.json", "w") as f:
            json.dump(quantum_prediction_history, f, indent=4)


def execute_trade(action, symbol):
    """Execute a trade"""
    global trade_history

    quantity = 1  # Fixed quantity for simplicity

    if action.upper() == "BUY":
        # Check if we already have a position
        if symbol in trade_history["positions"]:
            logger.info(f"Already have a position in {symbol}")
            return

        # Get current price
        current_price = platform_adapter.get_price(symbol)

        # Place order
        order_id = platform_adapter.place_order(symbol, "buy", quantity)

        if order_id:
            # Record the position
            trade_history["positions"][symbol] = {
                "entry_price": current_price,
                "quantity": quantity,
                "entry_time": time.time(),
                "order_id": order_id
            }

            # Record the trade
            trade_history["trades"].append({
                "symbol": symbol,
                "action": "BUY",
                "quantity": quantity,
                "price": current_price,
                "timestamp": datetime.now().isoformat(),
                "order_id": order_id
            })

            # Save trade history
            save_trade_history()

    elif action.upper() == "SELL":
        # Check if we have a position
        if symbol not in trade_history["positions"]:
            logger.info(f"No position in {symbol} to sell")
            return

        # Get position details
        position = trade_history["positions"][symbol]
        entry_price = position["entry_price"]
        quantity = position["quantity"]

        # Get current price
        current_price = platform_adapter.get_price(symbol)

        # Place order
        order_id = platform_adapter.place_order(symbol, "sell", quantity)

        if order_id:
            # Calculate profit/loss
            profit_loss = (current_price - entry_price) * quantity
            profit_loss_pct = (current_price / entry_price - 1) * 100

            # Record the trade
            trade_history["trades"].append({
                "symbol": symbol,
                "action": "SELL",
                "quantity": quantity,
                "price": current_price,
                "profit_loss": profit_loss,
                "profit_loss_pct": profit_loss_pct,
                "timestamp": datetime.now().isoformat(),
                "order_id": order_id
            })

            # Remove the position
            del trade_history["positions"][symbol]

            # Save trade history
            save_trade_history()

            logger.info(f"SELL completed: P&L ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")

            # Update quantum prediction accuracy if this trade was based on quantum prediction
            for pred in quantum_prediction_history:
                if (pred["symbol"] == symbol and pred["action"] in ["BUY", "SELL"] and
                        pred["correct"] is None):
                    # Mark prediction as correct if we made profit, incorrect if we lost money
                    pred["correct"] = profit_loss > 0
                    pred["actual_profit"] = float(profit_loss)
                    pred["actual_profit_pct"] = float(profit_loss_pct)

                    # Save updated prediction history
                    with open("data/quantum/prediction_history.json", "w") as f:
                        json.dump(quantum_prediction_history, f, indent=4)

                    # Log accuracy
                    logger.info(f"Quantum prediction was {'correct' if pred['correct'] else 'incorrect'} "
                                f"with confidence {pred['confidence']:.4f}")
                    break

        def update_quantum_model():
            """Update quantum model weights based on past predictions"""
            if not QUANTUM_AVAILABLE:
                return False

            try:
                # Need at least 10 predictions to update model
                if len(quantum_prediction_history) < 10:
                    logger.info("Not enough quantum predictions to update model")
                    return False

                # Group predictions by symbol
                by_symbol = {}
                for pred in quantum_prediction_history:
                    symbol = pred["symbol"]
                    if symbol not in by_symbol:
                        by_symbol[symbol] = []
                    by_symbol[symbol].append(pred)

                models_updated = 0

                # Update model for each symbol with enough data
                for symbol, predictions in by_symbol.items():
                    # Only consider completed predictions
                    completed = [p for p in predictions if p["correct"] is not None]
                    if len(completed) < 5:
                        continue

                    # Use most recent predictions for training
                    completed = sorted(completed, key=lambda x: x["timestamp"], reverse=True)[:20]

                    # Simple accuracy check
                    correct = sum(1 for p in completed if p["correct"])
                    accuracy = correct / len(completed)

                    logger.info(f"Quantum model accuracy for {symbol}: {accuracy:.4f} ({correct}/{len(completed)})")

                    # Only update if model is performing well
                    if accuracy > 0.55:
                        # Here we would normally implement more sophisticated quantum model training
                        # For this example, we'll just adjust weights slightly based on performance

                        weights_file = f"models/quantum_weights_{symbol}.npy"
                        if os.path.exists(weights_file):
                            weights = np.load(weights_file)

                            # Apply slight random adjustment to weights
                            adjustment = np.random.uniform(-0.1, 0.1, size=weights.shape)
                            weights += adjustment

                            # Save updated weights
                            os.makedirs("models", exist_ok=True)
                            np.save(weights_file, weights)

                            logger.info(f"Updated quantum model weights for {symbol}")
                            models_updated += 1

                return models_updated > 0

            except Exception as e:
                logger.error(f"Error updating quantum model: {e}")
                return False

        def quantum_portfolio_optimization(symbols, historical_returns, quantum_device, error_rate, config):
            """Optimize portfolio using quantum computing if error rate is acceptable"""
            if not QUANTUM_AVAILABLE or quantum_device is None:
                return None

            # Skip if error rate is too high
            if error_rate > config.get("quantum_config", {}).get("error_threshold", 0.15):
                logger.info(f"Quantum error rate too high for portfolio optimization: {error_rate:.4f}")
                return None

            try:
                # Number of assets
                num_assets = len(symbols)

                # Calculate covariance matrix and expected returns
                returns_matrix = np.array(historical_returns)
                cov_matrix = np.cov(returns_matrix, rowvar=False)
                exp_returns = np.mean(returns_matrix, axis=0)

                # Define the circuit for portfolio optimization
                @qml.qnode(quantum_device)
                def portfolio_circuit(params, gamma):
                    # Prepare qubits in superposition
                    for i in range(num_assets):
                        qml.Hadamard(wires=i)

                    # QAOA layers
                    # First the cost Hamiltonian (risk)
                    for i in range(num_assets):
                        for j in range(i + 1, num_assets):
                            # Apply ZZ interaction based on covariance
                            qml.IsingZZ(gamma * cov_matrix[i, j], wires=[i, j])

                    # Then the mixer Hamiltonian
                    for i in range(num_assets):
                        qml.RX(params[i], wires=i)

                    # Measure all qubits in Z basis
                    return [qml.expval(qml.PauliZ(i)) for i in range(num_assets)]

                # Initialize parameters
                params = np.random.uniform(0, np.pi, size=num_assets)
                gamma = 0.1  # Strength of the cost Hamiltonian

                # Run the circuit
                results = portfolio_circuit(params, gamma)

                # Convert to portfolio weights (from [-1,1] to [0,1])
                weights = [(r + 1) / 2 for r in results]

                # Normalize weights to sum to 1
                total = sum(weights)
                if total > 0:
                    weights = [w / total for w in weights]
                else:
                    # Equal weights if something went wrong
                    weights = [1.0 / num_assets] * num_assets

                portfolio = dict(zip(symbols, weights))

                logger.info(f"Quantum portfolio optimization complete: {portfolio}")
                return portfolio

            except Exception as e:
                logger.error(f"Error in quantum portfolio optimization: {e}")
                return None


def handle_exit(signum, frame):
    """Handle exit signals gracefully"""
    logger.info("Exit signal received. Shutting down...")

    # Save final metrics
    save_performance_metrics()

    # Final trade history save
    save_trade_history()

    # Log summary
    trades = trade_history["trades"]
    sell_trades = [t for t in trades if t["action"] == "SELL"]

    if sell_trades:
        total_profit = sum(t.get("profit_loss", 0) for t in sell_trades)
        win_count = sum(1 for t in sell_trades if t.get("profit_loss", 0) > 0)

        logger.info("=== Trading Summary ===")
        logger.info(f"Total trades closed: {len(sell_trades)}")
        logger.info(f"Win rate: {win_count / len(sell_trades):.2%}")
        logger.info(f"Total profit: ${total_profit:.2f}")
        logger.info("=====================")

    # Exit
    sys.exit(0)


def trading_loop():
    """Main trading loop with quantum integration"""
    logger.info("========== TRADING LOOP FUNCTION ENTERED ==========")

    # Load configuration
    config = load_config()

    # Load trade history
    load_trade_history()

    # Set up signal handling for graceful exit
    # signal.signal(signal.SIGINT, handle_exit)
    # signal.signal(signal.SIGTERM, handle_exit)

    # Initialize quantum device if enabled
    quantum_device = None
    if config.get("quantum_config", {}).get("enabled", True) and QUANTUM_AVAILABLE:
        quantum_device = initialize_quantum_device(config)

        if quantum_device is None:
            logger.warning("Failed to initialize quantum device. Using classical analysis only.")

    # Initialize platform adapter
    global platform_adapter
    platform_adapter = MockAdapter()

    # Create directories
    os.makedirs("data", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    os.makedirs("data/quantum", exist_ok=True)
    os.makedirs("data/performance", exist_ok=True)

    # Main loop
    update_model_counter = 0
    portfolio_opt_counter = 0

    try:
        while True:
            logger.info("Starting trading cycle")

            # Check if it's market hours (simplified)
            now = datetime.now()
            is_market_hours = (
                    0 <= now.weekday() <= 4 and  # Monday to Friday
                    9 <= now.hour < 16  # 9 AM to 4 PM
            )

            if is_market_hours:
                # Process each symbol
                for symbol in symbols:
                    try:
                        logger.info(f"Processing {symbol}")
                        make_trading_decision(symbol, quantum_device, config)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {e}")

                # Save performance metrics
                save_performance_metrics()

                # Update quantum model periodically
                update_model_counter += 1
                if update_model_counter >= 10:  # Every 10 cycles
                    update_model_counter = 0
                    try:
                        updated = update_quantum_model()
                        if updated:
                            logger.info("Quantum trading model updated")
                    except Exception as e:
                        logger.error(f"Error updating quantum model: {e}")

                # Perform portfolio optimization periodically
                portfolio_opt_counter += 1
                if portfolio_opt_counter >= 20:  # Every 20 cycles
                    portfolio_opt_counter = 0
                    try:
                        # Get historical returns for all symbols
                        historical_returns = []
                        for symbol in symbols:
                            data = platform_adapter.get_market_data(symbol)
                            returns = data['Close'].pct_change().dropna().values
                            historical_returns.append(returns)

                        # Transpose to have returns by date instead of by symbol
                        historical_returns = np.array(historical_returns).T

                        # Get error rate
                        error_rate = estimate_quantum_error_rate(quantum_device)

                        # Run portfolio optimization
                        optimal_portfolio = quantum_portfolio_optimization(
                            symbols, historical_returns, quantum_device, error_rate, config
                        )

                        if optimal_portfolio:
                            logger.info(f"Optimal portfolio weights: {optimal_portfolio}")

                            # Save portfolio allocation
                            os.makedirs("data/portfolios", exist_ok=True)
                            with open(f"data/portfolios/allocation_{datetime.now().strftime('%Y%m%d')}.json",
                                      "w") as f:
                                json.dump({
                                    "timestamp": datetime.now().isoformat(),
                                    "allocation": optimal_portfolio,
                                    "method": "quantum" if error_rate <= config.get("quantum_config", {}).get(
                                        "error_threshold", 0.15) else "classical"
                                }, f, indent=4)
                    except Exception as e:
                        logger.error(f"Error in portfolio optimization: {e}")
            else:
                logger.info("Market is closed, waiting...")

            # Sleep before next cycle
            logger.info(f"Sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        handle_exit(None, None)
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        handle_exit(None, None)

    logger.info("Trading bot shutdown")


def check_halal_compliance(symbol):
    """
    Check if a stock is halal compliant using the Zoya API

    Args:
        symbol (str): Stock symbol to check (e.g., 'AAPL')

    Returns:
        bool: True if stock is compliant, False if not
    """
    try:
        api_key = os.environ.get("ZOYA_API_KEY")
        if not api_key:
            logger.error("Zoya API key not found in environment variables")
            return False

        # Zoya API endpoint
        url = f"https://api.zoya.finance/stocks/{symbol}/compliance"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            # Check compliance status
            compliance_status = data.get("compliance_status")

            logger.info(f"Zoya API compliance check for {symbol}: {compliance_status}")

            # Return True if compliant, False otherwise
            return compliance_status == "compliant"
        else:
            logger.error(f"Error calling Zoya API: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error checking halal compliance: {e}")
        return False


def can_sell_stock(symbol, config):
    """Check if a stock can be sold based on minimum hold period"""
    if symbol not in trade_history["positions"]:
        return False

    position = trade_history["positions"][symbol]
    entry_time = position.get("entry_time", 0)
    current_time = time.time()

    # Get min hold period from config (default to 48 hours if not specified)
    min_hold_period = config.get("trading_bot", {}).get("min_hold_period", 172800)

    # Check if minimum hold period has passed
    time_held = current_time - entry_time
    can_sell = time_held >= min_hold_period

    if not can_sell:
        hours_left = (min_hold_period - time_held) / 3600
        logger.info(f"Cannot sell {symbol} yet - minimum hold period not met. {hours_left:.1f} hours remaining.")

    return can_sell


if __name__ == "__main__":
    logger.info("========== TRADING BOT SCRIPT STARTED ==========")
    try:
        logger.info("About to enter trading_loop function")
        trading_loop()
        logger.info("Trading bot execution completed")
    except Exception as e:
        logger.error(f"Critical error in trading bot: {e}", exc_info=True)
    trading_loop()
