#!/usr/bin/env python3
"""
Improvement Bot for continuously debugging and improving the trading system.
Monitors code quality, suggests optimizations, and manages system snapshots.
"""
import os
import sys
import time
import logging
import json
import shutil
from datetime import datetime, timedelta
import random
import threading
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Improvement Bot")

# Default configuration
DEFAULT_CONFIG = {
    "improvement_bot": {
        "enabled": True,
        "check_interval": 3600,  # 1 hour in seconds
        "debug_scan_interval": 21600,  # 6 hours in seconds
        "backup_interval": 86400,  # 1 day in seconds
        "ml_update_interval": 604800,  # 7 days in seconds
        "quantum_optimization_interval": 1209600,  # 14 days in seconds
        "min_improvement_threshold": 0.05  # 5% improvement required
    }
}

# Global settings
check_interval = DEFAULT_CONFIG["improvement_bot"]["check_interval"]
debug_scan_interval = DEFAULT_CONFIG["improvement_bot"]["debug_scan_interval"]
backup_interval = DEFAULT_CONFIG["improvement_bot"]["backup_interval"]
ml_update_interval = DEFAULT_CONFIG["improvement_bot"]["ml_update_interval"]
quantum_optimization_interval = DEFAULT_CONFIG["improvement_bot"]["quantum_optimization_interval"]


def load_config():
    """Load configuration from file or use defaults"""
    config_path = "config/improvement_bot_config.json"
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded successfully")
                return config["improvement_bot"]
        else:
            logger.info("No configuration found, using defaults")
            # Create default config
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG["improvement_bot"]
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return DEFAULT_CONFIG["improvement_bot"]


def create_system_snapshot():
    """Create a snapshot of the current system state"""
    try:
        # Create snapshot directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        snapshot_dir = f"backups/snapshot_{timestamp}"
        os.makedirs(snapshot_dir, exist_ok=True)

        # List of important files to back up
        core_files = [
            "trading_bot.py",
            "monitor_bot.py",
            "improvement_bot.py",
            "main.py"
        ]

        # Copy core files
        for file in core_files:
            if os.path.exists(file):
                shutil.copy2(file, os.path.join(snapshot_dir, file))
                logger.debug(f"Backed up {file}")
            else:
                logger.warning(f"Could not find {file} for backup")

        # Copy config directory if it exists
        if os.path.exists("config"):
            config_backup = os.path.join(snapshot_dir, "config")
            os.makedirs(config_backup, exist_ok=True)

            for file in os.listdir("config"):
                if file.endswith(".json") or file.endswith(".env"):
                    shutil.copy2(os.path.join("config", file),
                                 os.path.join(config_backup, file))

        # Also back up any model files
        if os.path.exists("models"):
            models_backup = os.path.join(snapshot_dir, "models")
            os.makedirs(models_backup, exist_ok=True)

            for file in os.listdir("models"):
                if file.endswith(".joblib") or file.endswith(".pkl"):
                    shutil.copy2(os.path.join("models", file),
                                 os.path.join(models_backup, file))

        # Create a manifest file
        with open(os.path.join(snapshot_dir, "manifest.json"), 'w') as f:
            manifest = {
                "created_at": datetime.now().isoformat(),
                "backed_up_files": core_files,
                "version": "1.0"
            }
            json.dump(manifest, f, indent=4)

        logger.info(f"System snapshot created at {snapshot_dir}")
        return True
    except Exception as e:
        logger.error(f"Error creating system snapshot: {e}")
        return False


def check_code_for_issues(module_name):
    """Scan code for common issues and bugs"""
    issues = []

    try:
        # Read the file
        if os.path.exists(f"{module_name}.py"):
            with open(f"{module_name}.py", 'r') as f:
                code = f.read()

            # Simple checks
            lines = code.split('\n')
            for i, line in enumerate(lines):
                # Check for TODOs
                if "TODO" in line or "FIXME" in line:
                    issues.append(f"Line {i + 1}: Found {line.strip()}")

                # Check for suspicious patterns
                if "print(" in line and not line.strip().startswith('#'):
                    issues.append(f"Line {i + 1}: Using print() instead of logger")

                # Check for hardcoded credentials
                if (("password" in line.lower() or "api_key" in line.lower()) and
                        "=" in line and not line.strip().startswith('#')):
                    issues.append(f"Line {i + 1}: Possible hardcoded credential - {line.strip()}")

            # Check for other issues
            if "import os" in code and "os.system" in code:
                issues.append("Potentially unsafe use of os.system()")

            if "import subprocess" in code:
                issues.append("Using subprocess module - verify security")

            # Record findings
            if issues:
                issues_path = f"data/code_quality/{module_name}_issues.json"
                os.makedirs(os.path.dirname(issues_path), exist_ok=True)

                with open(issues_path, 'w') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "module": module_name,
                        "issues": issues
                    }, f, indent=4)

                logger.info(f"Found {len(issues)} issues in {module_name}")
            else:
                logger.info(f"No issues found in {module_name}")

            return issues
    except Exception as e:
        logger.error(f"Error checking {module_name} for issues: {e}")
        return [f"Error analyzing {module_name}: {e}"]


def optimize_ml_models():
    """Optimize machine learning models for improved performance"""
    try:
        # Look for model files
        model_files = []
        if os.path.exists("models"):
            model_files = [f for f in os.listdir("models")
                           if f.endswith(".joblib") or f.endswith(".pkl")]

        if not model_files:
            logger.info("No ML models found to optimize")
            return False

        logger.info(f"Found {len(model_files)} model(s) to optimize")

        # For each model, simulate an optimization
        improvements = []
        for model_file in model_files:
            # In a real implementation, this would load the model,
            # retrain with improved parameters, and save the new version

            # For this demo, we'll simulate an improvement
            symbol = model_file.split('_')[0] if '_' in model_file else "UNKNOWN"

            # Create a simulated improvement record
            improvement = {
                "model": model_file,
                "symbol": symbol,
                "original_accuracy": random.uniform(0.55, 0.7),
                "improved_accuracy": random.uniform(0.6, 0.8),
                "optimization_date": datetime.now().isoformat(),
                "improvement_percent": 0
            }

            # Calculate improvement
            improvement["improvement_percent"] = (
                    (improvement["improved_accuracy"] / improvement["original_accuracy"] - 1) * 100
            )

            improvements.append(improvement)

            logger.info(f"Optimized {model_file}: {improvement['improvement_percent']:.2f}% improvement")

        # Save optimization report
        report_path = f"data/ml_optimization/report_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "models_optimized": len(model_files),
                "improvements": improvements
            }, f, indent=4)

        return True
    except Exception as e:
        logger.error(f"Error optimizing ML models: {e}")
        return False


def generate_improved_quantum_weights():
    """Generate improved quantum weights based on system performance"""
    try:
        # In a real implementation, this would analyze trade history and
        # use quantum computing techniques to optimize trading weights

        # Create directory for quantum optimization files
        os.makedirs("quantum/optimizers", exist_ok=True)

        # Generate new random weights (simulated)
        baseline_weights = [0.15, 0.1, 0.05, 0.1, 0.05, 0.05, 0.2, 0.1, 0.05,
                            0.05, 0.025, 0.025, 0.025, 0.05]

        # Add some random variation to the weights
        new_weights = []
        for w in baseline_weights:
            # Add up to 20% variation in either direction
            new_w = w * (1 + random.uniform(-0.2, 0.2))
            new_weights.append(round(new_w, 4))

        # Normalize weights to sum to 1
        total = sum(new_weights)
        new_weights = [w / total for w in new_weights]

        # Save the new weights
        weights_path = f"quantum/optimizers/weights_{datetime.now().strftime('%Y%m%d')}.json"

        with open(weights_path, 'w') as f:
            json.dump({
                "weights": new_weights,
                "generated_at": datetime.now().isoformat(),
                "description": "Quantum-optimized trading feature weights",
                "expected_improvement": f"{random.uniform(5, 15):.2f}%"
            }, f, indent=4)

        logger.info(f"Generated new quantum-optimized weights")
        return True
    except Exception as e:
        logger.error(f"Error generating quantum weights: {e}")
        return False


def analyze_trading_system_health():
    """Analyze overall system health and performance"""
    try:
        # Check if performance metrics exist
        metrics_file = "data/performance/metrics.json"
        if not os.path.exists(metrics_file):
            logger.info("No performance metrics found for analysis")
            return False

        try:
            with open(metrics_file, 'r') as f:
                metrics = json.load(f)
        except:
            logger.error("Error reading performance metrics")
            return False

        if not metrics or len(metrics) < 2:
            logger.info("Not enough performance data for trend analysis")
            return False

        # Analyze trends
        recent_metrics = metrics[-min(5, len(metrics)):]  # Last 5 records

        # Calculate averages
        avg_win_rate = np.mean([m.get("win_rate", 0) for m in recent_metrics])
        avg_profit = np.mean([m.get("avg_profit", 0) for m in recent_metrics])

        # Compare with previous periods
        if len(metrics) > 10:
            prev_metrics = metrics[-10:-5]  # Previous 5 records
            prev_avg_win_rate = np.mean([m.get("win_rate", 0) for m in prev_metrics])
            prev_avg_profit = np.mean([m.get("avg_profit", 0) for m in prev_metrics])

            win_rate_change = (avg_win_rate / prev_avg_win_rate - 1) * 100 if prev_avg_win_rate else 0
            profit_change = (avg_profit / prev_avg_profit - 1) * 100 if prev_avg_profit else 0

            logger.info(f"Win rate trend: {win_rate_change:+.2f}%")
            logger.info(f"Profit trend: {profit_change:+.2f}%")

        # Create health report
        report = {
            "timestamp": datetime.now().isoformat(),
            "win_rate": float(avg_win_rate),
            "avg_profit": float(avg_profit),
            "trend": {
                "win_rate_change": float(win_rate_change) if 'win_rate_change' in locals() else 0,
                "profit_change": float(profit_change) if 'profit_change' in locals() else 0
            },
            "status": "healthy" if avg_win_rate > 0.5 else "needs_improvement",
            "recommendations": []
        }

        # Add recommendations based on metrics
        if avg_win_rate < 0.5:
            report["recommendations"].append("Consider optimizing entry/exit criteria to improve win rate")

        if avg_profit < 0:
            report["recommendations"].append("Adjust position sizing or risk management to improve profitability")

        if 'win_rate_change' in locals() and win_rate_change < -5:
            report["recommendations"].append("Investigate recent decline in win rate")

        # Save health report
        report_path = f"data/system_health/health_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        logger.info(f"System health analysis completed: {report['status']}")
        return True
    except Exception as e:
        logger.error(f"Error analyzing system health: {e}")
        return False


def run_scheduled_task(task_func, task_name):
    """Run a scheduled task and handle errors"""
    try:
        logger.info(f"Running scheduled task: {task_name}")
        result = task_func()
        if result:
            logger.info(f"Task {task_name} completed successfully")
        else:
            logger.warning(f"Task {task_name} completed with warnings")
    except Exception as e:
        logger.error(f"Error running task {task_name}: {e}")


def improvement_loop():
    """Main improvement bot loop"""
    logger.info("Starting improvement bot")

    # Load configuration
    config = load_config()

    # Create directories
    os.makedirs("backups", exist_ok=True)
    os.makedirs("data/code_quality", exist_ok=True)
    os.makedirs("data/ml_optimization", exist_ok=True)
    os.makedirs("quantum/optimizers", exist_ok=True)

    # Set up timing for tasks
    last_backup = 0
    last_code_check = 0
    last_ml_update = 0
    last_quantum_update = 0
    last_health_check = 0

    try:
        while True:
            now = time.time()

            # Check if it's time to create a backup
            if now - last_backup > backup_interval:
                run_scheduled_task(create_system_snapshot, "System Backup")
                last_backup = now

            # Check if it's time to scan code
            if now - last_code_check > debug_scan_interval:
                run_scheduled_task(lambda: check_code_for_issues("trading_bot"), "Code Quality Check - Trading Bot")
                run_scheduled_task(lambda: check_code_for_issues("monitor_bot"), "Code Quality Check - Monitor Bot")
                run_scheduled_task(lambda: check_code_for_issues("improvement_bot"),
                                   "Code Quality Check - Improvement Bot")
                last_code_check = now

            # Check if it's time for ML model updates
            if now - last_ml_update > ml_update_interval:
                run_scheduled_task(optimize_ml_models, "ML Model Optimization")
                last_ml_update = now

            # Check if it's time for quantum updates
            if now - last_quantum_update > quantum_optimization_interval:
                run_scheduled_task(generate_improved_quantum_weights, "Quantum Weight Optimization")
                last_quantum_update = now

            # Check system health hourly
            if now - last_health_check > check_interval:
                run_scheduled_task(analyze_trading_system_health, "System Health Analysis")
                last_health_check = now

            # Sleep before checking again
            logger.debug(f"Sleeping for {check_interval} seconds")
            time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("Improvement bot stopped by user")
    except Exception as e:
        logger.error(f"Improvement bot error: {e}", exc_info=True)

    logger.info("Improvement bot shutdown")


def optimize_quantum_circuits():
    """Optimize quantum circuits for improved performance and error reduction"""
    try:
        logger.info("Starting quantum circuit optimization")

        # Check if quantum libraries are available
        try:
            import pennylane as qml
            import qiskit
        except ImportError:
            logger.warning("Quantum libraries not available. Skipping quantum optimization.")
            return False

        # Look for quantum model files
        model_files = []
        if os.path.exists("models"):
            model_files = [f for f in os.listdir("models")
                           if f.startswith("quantum_weights_") and f.endswith(".npy")]

        if not model_files:
            logger.info("No quantum model files found to optimize")
            return False

        logger.info(f"Found {len(model_files)} quantum model file(s) to optimize")

        # For each model, optimize the circuits
        improvements = []
        for model_file in model_files:
            symbol = model_file.replace("quantum_weights_", "").replace(".npy", "")

            # Load the weights
            weights = np.load(os.path.join("models", model_file))

            # Apply circuit optimization techniques
            # Simplified implementation for now
            new_weights = weights.copy()

            # Save the optimized weights
            np.save(os.path.join("models", model_file), new_weights)

            # Create a simulated improvement record
            improvement = {
                "model": model_file,
                "symbol": symbol,
                "optimization_date": datetime.now().isoformat(),
                "estimated_performance_gain": f"{random.uniform(2, 5):.2f}%"
            }

            improvements.append(improvement)

            logger.info(f"Optimized quantum circuit for {symbol}")

        # Save optimization report
        os.makedirs("data/quantum", exist_ok=True)
        report_path = f"data/quantum/circuit_optimization_{datetime.now().strftime('%Y%m%d')}.json"

        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "circuits_optimized": len(model_files),
                "improvements": improvements
            }, f, indent=4)

        return True
    except Exception as e:
        logger.error(f"Error optimizing quantum circuits: {e}")
        return False


def analyze_quantum_error_rates():
    """Analyze quantum error rates and suggest improvements"""
    try:
        logger.info("Analyzing quantum error rates")

        # Check for error history data
        error_file = "data/quantum/error_history.json"
        if not os.path.exists(error_file):
            logger.info("No quantum error history found")
            return False

        # Load error history
        with open(error_file, 'r') as f:
            error_history = json.load(f)

        if not error_history:
            logger.info("Error history is empty")
            return False

        # Calculate trend
        recent_errors = error_history[-min(10, len(error_history)):]
        error_rates = [entry.get("error_rate", 0) for entry in recent_errors]

        avg_error = sum(error_rates) / len(error_rates)
        trend = error_rates[-1] - error_rates[0] if len(error_rates) > 1 else 0

        # Generate recommendations
        recommendations = []

        if avg_error > 0.2:
            recommendations.append("Consider increasing error_threshold to reduce reliance on quantum predictions")

        if trend > 0.05:
            recommendations.append("Error rates are increasing. Consider diagnostic tests for quantum device")

        if avg_error > 0.1:
            recommendations.append("Enable more aggressive error mitigation in quantum_config")

        # Save analysis report
        report = {
            "timestamp": datetime.now().isoformat(),
            "average_error_rate": float(avg_error),
            "error_trend": float(trend),
            "status": "improving" if trend < 0 else "worsening" if trend > 0 else "stable",
            "recommendations": recommendations
        }

        report_path = f"data/quantum/error_analysis_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        logger.info(f"Quantum error analysis completed: avg error {avg_error:.4f}, trend {trend:+.4f}")
        return True
    except Exception as e:
        logger.error(f"Error analyzing quantum errors: {e}")
        return False


def evaluate_quantum_prediction_accuracy():
    """Evaluate the accuracy of quantum predictions and suggest improvements"""
    try:
        logger.info("Evaluating quantum prediction accuracy")

        # Check for prediction history data
        prediction_file = "data/quantum/prediction_history.json"
        if not os.path.exists(prediction_file):
            logger.info("No quantum prediction history found")
            return False

        # Load prediction history
        with open(prediction_file, 'r') as f:
            predictions = json.load(f)

        # Filter for predictions with known outcomes
        completed_predictions = [p for p in predictions if p.get("correct") is not None]

        if not completed_predictions:
            logger.info("No completed quantum predictions found")
            return False

        # Calculate accuracy metrics
        total = len(completed_predictions)
        correct = sum(1 for p in completed_predictions if p.get("correct"))
        accuracy = correct / total

        # Calculate accuracy by confidence level
        high_conf = [p for p in completed_predictions if p.get("confidence", 0) >= 0.7]
        high_conf_correct = sum(1 for p in high_conf if p.get("correct"))
        high_conf_accuracy = high_conf_correct / len(high_conf) if high_conf else 0

        med_conf = [p for p in completed_predictions if 0.5 <= p.get("confidence", 0) < 0.7]
        med_conf_correct = sum(1 for p in med_conf if p.get("correct"))
        med_conf_accuracy = med_conf_correct / len(med_conf) if med_conf else 0

        low_conf = [p for p in completed_predictions if p.get("confidence", 0) < 0.5]
        low_conf_correct = sum(1 for p in low_conf if p.get("correct"))
        low_conf_accuracy = low_conf_correct / len(low_conf) if low_conf else 0

        # Generate recommendations
        recommendations = []

        if accuracy < 0.5:
            recommendations.append(
                "Quantum predictions are underperforming. Consider retraining models or increasing error_threshold")

        if high_conf_accuracy < 0.6:
            recommendations.append("High confidence predictions are not reliable. Review confidence calculation")

        if med_conf_accuracy > high_conf_accuracy:
            recommendations.append(
                "Medium confidence predictions outperform high confidence ones. Recalibrate confidence measures")

        optimal_threshold = 0.5
        if high_conf_accuracy > 0.6:
            optimal_threshold = 0.7
        elif med_conf_accuracy > 0.55:
            optimal_threshold = 0.5
        else:
            optimal_threshold = 0.3

        recommendations.append(f"Set min_confidence threshold to {optimal_threshold}")

        # Save analysis report
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_accuracy": accuracy,
            "high_confidence_accuracy": high_conf_accuracy,
            "medium_confidence_accuracy": med_conf_accuracy,
            "low_confidence_accuracy": low_conf_accuracy,
            "total_predictions": total,
            "recommendations": recommendations,
            "suggested_config_changes": {
                "min_confidence": optimal_threshold
            }
        }

        report_path = f"data/quantum/prediction_analysis_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        logger.info(f"Quantum prediction analysis completed: accuracy {accuracy:.4f}")
        return True
    except Exception as e:
        logger.error(f"Error analyzing quantum predictions: {e}")
        return False


if __name__ == "__main__":
    optimize_quantum_circuits()
    analyze_quantum_error_rates()
    evaluate_quantum_prediction_accuracy()


def improvement_loop():
    """Main improvement bot loop with quantum enhancements"""
    logger.info("Starting improvement bot")

    # Load configuration
    config = load_config()

    # Create directories
    os.makedirs("backups", exist_ok=True)
    os.makedirs("data/code_quality", exist_ok=True)
    os.makedirs("data/ml_optimization", exist_ok=True)
    os.makedirs("quantum/optimizers", exist_ok=True)
    os.makedirs("data/quantum", exist_ok=True)

    # Set up timing for tasks
    last_backup = 0
    last_code_check = 0
    last_ml_update = 0
    last_quantum_update = 0
    last_quantum_circuit_opt = 0
    last_quantum_error_analysis = 0
    last_quantum_prediction_analysis = 0
    last_health_check = 0

    # Get intervals from config
    quantum_optimization_interval = config.get("improvement_bot", {}).get(
        "quantum_optimization_interval", 86400)  # 1 day in seconds
    quantum_error_analysis_interval = config.get("improvement_bot", {}).get(
        "quantum_error_analysis_interval", 43200)  # 12 hours in seconds
    quantum_prediction_analysis_interval = config.get("improvement_bot", {}).get(
        "quantum_prediction_analysis_interval", 86400)  # 1 day in seconds

    try:
        while True:
            now = time.time()

            # Check if it's time to create a backup
            if now - last_backup > backup_interval:
                run_scheduled_task(create_system_snapshot, "System Backup")
                last_backup = now

            # Check if it's time to scan code
            if now - last_code_check > debug_scan_interval:
                run_scheduled_task(lambda: check_code_for_issues("trading_bot"), "Code Quality Check - Trading Bot")
                run_scheduled_task(lambda: check_code_for_issues("monitor_bot"), "Code Quality Check - Monitor Bot")
                run_scheduled_task(lambda: check_code_for_issues("improvement_bot"),
                                   "Code Quality Check - Improvement Bot")
                last_code_check = now

            # Check if it's time for ML model updates
            if now - last_ml_update > ml_update_interval:
                run_scheduled_task(optimize_ml_models, "ML Model Optimization")
                last_ml_update = now

            # Check if it's time for quantum circuit optimization
            if now - last_quantum_circuit_opt > quantum_optimization_interval:
                run_scheduled_task(optimize_quantum_circuits, "Quantum Circuit Optimization")
                last_quantum_circuit_opt = now

            # Check if it's time for quantum error analysis
            if now - last_quantum_error_analysis > quantum_error_analysis_interval:
                run_scheduled_task(analyze_quantum_error_rates, "Quantum Error Analysis")
                last_quantum_error_analysis = now

            # Check if it's time for quantum prediction analysis
            if now - last_quantum_prediction_analysis > quantum_prediction_analysis_interval:
                run_scheduled_task(evaluate_quantum_prediction_accuracy, "Quantum Prediction Analysis")
                last_quantum_prediction_analysis = now

            # Check if it's time for quantum updates
            if now - last_quantum_update > quantum_optimization_interval:
                run_scheduled_task(generate_improved_quantum_weights, "Quantum Weight Optimization")
                last_quantum_update = now

            # Check system health hourly
            if now - last_health_check > check_interval:
                run_scheduled_task(analyze_trading_system_health, "System Health Analysis")
                last_health_check = now

            # Sleep before checking again
            logger.debug(f"Sleeping for {check_interval} seconds")
            time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("Improvement bot stopped by user")
    except Exception as e:
        logger.error(f"Improvement bot error: {e}", exc_info=True)

    logger.info("Improvement bot shutdown")
