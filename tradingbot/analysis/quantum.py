import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class QuantumAnalyzer:
    """Quantum computing based analysis for trading signals"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize quantum analyzer with configuration

        Args:
            config: Quantum analysis configuration
        """
        self.config = config
        self.quantum_available = False
        self.device = None
        self.error_history = []
        self.prediction_history = []

        # Try to import quantum libraries
        try:
            import pennylane as qml
            self.qml = qml
            import qiskit
            self.qiskit = qiskit

            logger.info(f"Quantum libraries loaded successfully: PennyLane {qml.__version__}, " +
                        f"Qiskit {qiskit.__version__}")
            self.quantum_available = True

            # Initialize device
            self.initialize_quantum_device()
        except ImportError as e:
            logger.warning(f"Quantum libraries not available: {e}. Will use classical analysis only.")

    def initialize_quantum_device(self) -> bool:
        """Initialize the quantum device

        Returns:
            True if initialization succeeded, False otherwise
        """
        if not self.quantum_available:
            logger.warning("Cannot initialize quantum device - libraries not available")
            return False

        try:
            device_name = self.config.get("device", "default.qubit")
            shots = self.config.get("shots", 1000)

            logger.info(f"Initializing quantum device: {device_name} with {shots} shots")

            if device_name == "default.qubit":
                # Use PennyLane's default simulator
                self.device = self.qml.device(device_name, wires=5, shots=shots)
            elif "aer" in device_name:
                # Use Qiskit's simulator through PennyLane
                self.device = self.qml.device('qiskit.aer', wires=5, shots=shots)
            else:
                # Try to initialize requested device
                self.device = self.qml.device(device_name, wires=5, shots=shots)

            logger.info(f"Quantum device initialized: {device_name}")
            return True
        except Exception as e:
            logger.error(f"Error initializing quantum device: {e}")
            logger.info("Falling back to default simulator")

            try:
                self.device = self.qml.device("default.qubit", wires=5, shots=1000)
                return True
            except Exception as e2:
                logger.error(f"Error initializing fallback device: {e2}")
                self.quantum_available = False
                return False

    def estimate_error_rate(self) -> float:
        """Estimate the current error rate of the quantum device

        Returns:
            Estimated error rate (0-1)
        """
        if not self.quantum_available or self.device is None:
            return 1.0  # Maximum error

        try:
            # Define a simple circuit that should return a known result
            @self.qml.qnode(self.device)
            def test_circuit():
                self.qml.Hadamard(wires=0)
                self.qml.CNOT(wires=[0, 1])
                return self.qml.expval(self.qml.PauliZ(0)), self.qml.expval(self.qml.PauliZ(1))

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
            self.error_history.append({
                "timestamp": datetime.now().isoformat(),
                "error_rate": float(error_rate)
            })

            # Save error history to file
            import os
            import json
            os.makedirs("data/quantum", exist_ok=True)
            with open("data/quantum/error_history.json", "w") as f:
                json.dump(self.error_history, f, indent=4)

            return error_rate
        except Exception as e:
            logger.error(f"Error estimating quantum error rate: {e}")
            return 1.0  # Assume maximum error on failure

    def quantum_feature_map(self, x: np.ndarray, wires: List[int]) -> None:
        """Apply a quantum feature map to encode classical data into quantum state

        Args:
            x: Classical feature vector
            wires: Qubits to use
        """
        if not self.quantum_available:
            return

        # Normalize input features
        x_norm = x / np.linalg.norm(x)

        # Encode features into rotation angles
        for i, xi in enumerate(x_norm):
            self.qml.RY(xi * np.pi, wires=i % len(wires))

        # Entangle qubits
        for i in range(len(wires) - 1):
            self.qml.CNOT(wires=[wires[i], wires[i + 1]])

    def get_quantum_prediction(self, symbol: str, df: pd.DataFrame, news_data: Optional[Dict[str, Any]] = None) -> \
    Tuple[float, float]:
        """Generate trading prediction using quantum computing

        Args:
            symbol: Stock symbol
            df: Price dataframe with indicators
            news_data: Optional news sentiment data to enhance prediction

        Returns:
            Tuple of (trading signal, confidence)
        """
        if not self.quantum_available or self.device is None:
            logger.warning("Quantum prediction not available, falling back to classical")
            # Return a neutral signal with zero confidence
            return 0.5, 0.0

        # Check error rate
        error_rate = self.estimate_error_rate()
        error_threshold = self.config.get("error_threshold", 0.15)

        # If error rate is too high, don't use quantum prediction
        if error_rate > error_threshold:
            logger.warning(f"Quantum error rate too high: {error_rate:.4f} > {error_threshold:.4f}")
            # Return a neutral signal with zero confidence
            return 0.5, 0.0

        try:
            # Prepare features
            df_recent = df.tail(10).copy()  # Use last 10 days

            # Create feature vector
            features = []

            # Price changes (normalized)
            price_changes = df_recent['Close'].pct_change().fillna(0).values[-5:]
            features.extend((price_changes + 1) / 2)  # Scale to [0, 1]

            # RSI (normalized)
            rsi_values = df_recent['RSI'].values[-5:] / 100  # Scale to [0, 1]
            features.extend(rsi_values)

            # MA ratio (normalized)
            ma_ratio = ((df_recent['SMA_5'] / df_recent['SMA_20']).values[-5:] - 0.8) / 0.4
            features.extend(np.clip(ma_ratio, 0, 1))  # Clip to [0, 1]

            # Add news features if available
            if news_data:
                # News sentiment (scaled to 0-1)
                news_sentiment = (news_data.get("news_sentiment", 0) + 1) / 2
                features.append(news_sentiment)

                # Fear & greed (scaled to 0-1)
                fear_greed = news_data.get("fear_greed_score", 50) / 100
                features.append(fear_greed)

            # Limit features to number of qubits available
            features = np.array(features[:5])

            # Ensure features are in [0, 1]
            features = np.clip(features, 0, 1)

            # Define the quantum circuit for prediction
            @self.qml.qnode(self.device, diff_method="parameter-shift")
            def quantum_circuit(features, weights):
                # Encode features
                self.quantum_feature_map(features, wires=range(len(features)))

                # Variational layer
                for i in range(len(features)):
                    self.qml.Rot(weights[i, 0], weights[i, 1], weights[i, 2], wires=i)

                for i in range(len(features) - 1):
                    self.qml.CNOT(wires=[i, i + 1])

                # Final rotation
                self.qml.RY(weights[-1, 0], wires=0)

                # Return probability of measuring |1⟩ on first qubit
                return self.qml.expval(self.qml.PauliZ(0))

            # Use pre-trained weights or initialize random weights
            import os
            weights_file = f"models/quantum_weights_{symbol}.npy"
            if os.path.exists(weights_file):
                weights = np.load(weights_file)
            else:
                weights = np.random.uniform(low=-np.pi, high=np.pi, size=(len(features) + 1, 3))

                # Save weights
                os.makedirs("models", exist_ok=True)
                np.save(weights_file, weights)

            # Apply error mitigation if enabled
            use_error_mitigation = self.config.get("use_error_mitigation", True)

            if use_error_mitigation and error_rate > 0.05:
                # Simple error mitigation by running multiple times and taking average
                results = []
                for _ in range(5):
                    results.append(quantum_circuit(features, weights))

                # Average results
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

            # Check if confidence is too low
            min_confidence = self.config.get("min_confidence", 0.65)
            if confidence < min_confidence:
                logger.info(f"Quantum confidence ({confidence:.2f}) below threshold ({min_confidence:.2f})")

                # Return signal, but with reduced confidence
                return trading_signal, confidence

            logger.info(f"Quantum prediction for {symbol}: {trading_signal:.4f} (confidence: {confidence:.4f})")

            # Record prediction (will be evaluated later)
            self.prediction_history.append({
                "timestamp": datetime.now().isoformat(),
                "symbol": symbol,
                "signal": float(trading_signal),
                "confidence": float(confidence),
                "error_rate": float(error_rate),
                "features": features.tolist(),
                "correct": None  # Will be updated after we know the outcome
            })

            # Save prediction history
            import json
            with open("data/quantum/prediction_history.json", "w") as f:
                json.dump(self.prediction_history, f, indent=4)

            return trading_signal, confidence
        except Exception as e:
            logger.error(f"Error in quantum prediction: {e}")
            return 0.5, 0.0  # Neutral signal with zero confidence

    def update_prediction_accuracy(self, symbol: str, was_correct: bool, profit: float) -> None:
        """Update the accuracy of a previous prediction

        Args:
            symbol: Stock symbol
            was_correct: Whether the prediction was correct
            profit: Profit made (positive) or loss (negative)
        """
        if not self.prediction_history:
            return

        # Find the most recent prediction for this symbol
        for pred in reversed(self.prediction_history):
            if pred["symbol"] == symbol and pred["correct"] is None:
                # Update the prediction record
                pred["correct"] = was_correct
                pred["profit"] = float(profit)

                # Save updated prediction history
                import json
                with open("data/quantum/prediction_history.json", "w") as f:
                    json.dump(self.prediction_history, f, indent=4)

                # Log the result
                logger.info(
                    f"Updated prediction accuracy for {symbol}: {'correct' if was_correct else 'incorrect'}, profit: {profit:.2f}")
                return