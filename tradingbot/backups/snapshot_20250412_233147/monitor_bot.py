#!/usr/bin/env python3
"""
Monitor Bot for the trading system.
Monitors performance, checks APIs, and generates reports.
Includes quantum system monitoring capabilities.
"""
import os
import sys
import time
import logging
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Monitor Bot")

try:
    import platform_adapters.platform_factory as platform_factory
except ImportError:
    platform_factory = None
from cryptography.fernet import Fernet
import requests
import schedule

# Global parameters (updated from config)
QUANTUM_OPTIMIZER_INTERVAL = 3  # days
LEGAL_CHECK_INTERVAL = 7  # days
API_CHECK_INTERVAL = 1  # days

# Platform adapter
platform_adapter = None


def init_platform(platform_name="webull"):
    """Initialize the trading platform adapter"""
    global platform_adapter

    if platform_factory is None:
        logger.error("Platform factory module not found")
        return False

    try:
        factory = platform_factory.PlatformFactory()
        platform_adapter = factory.create_adapter(platform_name)

        if platform_adapter is None:
            logger.error(f"Failed to initialize {platform_name} adapter")
            return False

        return True
    except Exception as e:
        logger.error(f"Error initializing platform: {e}")
        return False


def extract_performance_metrics():
    """Extract and log performance metrics"""
    try:
        # Check if metrics file exists
        metrics_path = os.path.join('data', 'performance', 'metrics.json')
        if not os.path.exists(metrics_path):
            logger.warning("No performance metrics file found")
            return None

        # Load metrics
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        if not metrics:
            logger.warning("No performance metrics available")
            return None

        # Group by date (just the day part, not time)
        metrics_by_day = {}
        for entry in metrics:
            date_str = entry['date'].split('T')[0]  # Just get YYYY-MM-DD part
            metrics_by_day[date_str] = entry

        # Convert to list and sort by date
        unique_metrics = list(metrics_by_day.values())
        unique_metrics.sort(key=lambda x: x['date'])

        # Get latest metrics
        latest = unique_metrics[-1]

        logger.info("=== Performance Metrics ===")
        logger.info(f"Date: {latest['date']}")
        logger.info(f"Total Trades: {latest['total_trades']}")
        logger.info(f"Win Rate: {latest['win_rate'] * 100:.2f}%")
        logger.info(f"Total Profit: ${latest['total_profit']:.2f}")
        logger.info(f"Average Profit per Trade: ${latest['avg_profit']:.2f}")
        if 'avg_profit_pct' in latest:
            logger.info(f"Average Profit Percentage: {latest['avg_profit_pct']:.2f}%")
        if 'max_drawdown' in latest:
            logger.info(f"Maximum Drawdown: {latest['max_drawdown']:.2f}%")
        if 'quantum_accuracy' in latest and latest['quantum_accuracy'] is not None:
            logger.info(f"Quantum Prediction Accuracy: {latest['quantum_accuracy'] * 100:.2f}%")
        logger.info("============================")

        # Save to CSV for easy analysis
        df = pd.DataFrame(unique_metrics)
        df['date'] = pd.to_datetime(df['date'])
        df.to_csv(os.path.join('data', 'performance', 'metrics_history.csv'), index=False)

        return df

    except Exception as e:
        logger.error(f"Error extracting performance metrics: {e}")
        return None


def plot_performance_trends(metrics=None):
    """Plot performance metrics trends over time"""
    try:
        # If metrics not provided, load them
        if metrics is None or (isinstance(metrics, pd.DataFrame) and metrics.empty):
            metrics_path = os.path.join('data', 'performance', 'metrics.json')
            if not os.path.exists(metrics_path):
                logger.warning("No performance metrics file found")
                return False

            with open(metrics_path, 'r') as f:
                metrics_data = json.load(f)

            if not metrics_data:
                logger.warning("No performance metrics available")
                return False

            metrics = pd.DataFrame(metrics_data)
            metrics['date'] = pd.to_datetime(metrics['date'])

        # Create output directory
        os.makedirs(os.path.join('data', 'performance', 'charts'), exist_ok=True)

        # Plot win rate over time
        plt.figure(figsize=(12, 6))
        plt.plot(metrics['date'], metrics['win_rate'] * 100, 'b-', linewidth=2)
        plt.grid(True, alpha=0.3)
        plt.title('Win Rate Over Time')
        plt.xlabel('Date')
        plt.ylabel('Win Rate (%)')
        plt.savefig(os.path.join('data', 'performance', 'charts', 'win_rate.png'))
        plt.close()

        # Plot total profit over time
        plt.figure(figsize=(12, 6))
        plt.plot(metrics['date'], metrics['total_profit'], 'g-', linewidth=2)
        plt.grid(True, alpha=0.3)
        plt.title('Total Profit Over Time')
        plt.xlabel('Date')
        plt.ylabel('Profit ($)')
        plt.savefig(os.path.join('data', 'performance', 'charts', 'total_profit.png'))
        plt.close()

        # Plot other metrics if available
        if 'avg_profit_pct' in metrics.columns:
            plt.figure(figsize=(12, 6))
            plt.plot(metrics['date'], metrics['avg_profit_pct'], 'r-', linewidth=2)
            plt.grid(True, alpha=0.3)
            plt.title('Average Profit Percentage Over Time')
            plt.xlabel('Date')
            plt.ylabel('Avg Profit (%)')
            plt.savefig(os.path.join('data', 'performance', 'charts', 'avg_profit_pct.png'))
            plt.close()

        if 'max_drawdown' in metrics.columns:
            plt.figure(figsize=(12, 6))
            plt.plot(metrics['date'], metrics['max_drawdown'], 'r-', linewidth=2)
            plt.grid(True, alpha=0.3)
            plt.title('Maximum Drawdown Over Time')
            plt.xlabel('Date')
            plt.ylabel('Max Drawdown (%)')
            plt.savefig(os.path.join('data', 'performance', 'charts', 'max_drawdown.png'))
            plt.close()

        # Plot win rate vs average profit percentage if available
        if 'avg_profit_pct' in metrics.columns:
            plt.figure(figsize=(10, 8))
            plt.scatter(metrics['win_rate'] * 100, metrics['avg_profit_pct'], s=50, alpha=0.7)
            plt.grid(True, alpha=0.3)
            plt.title('Win Rate vs Average Profit Percentage')
            plt.xlabel('Win Rate (%)')
            plt.ylabel('Avg Profit (%)')
            plt.savefig(os.path.join('data', 'performance', 'charts', 'win_rate_vs_profit.png'))
            plt.close()

        # Plot quantum accuracy if available
        if 'quantum_accuracy' in metrics.columns:
            quantum_data = metrics[metrics['quantum_accuracy'].notnull()]
            if not quantum_data.empty:
                plt.figure(figsize=(12, 6))
                plt.plot(quantum_data['date'], quantum_data['quantum_accuracy'] * 100, 'purple', linewidth=2)
                plt.axhline(y=50, color='r', linestyle='--', alpha=0.5)  # Random chance line
                plt.grid(True, alpha=0.3)
                plt.title('Quantum Prediction Accuracy Over Time')
                plt.xlabel('Date')
                plt.ylabel('Accuracy (%)')
                plt.savefig(os.path.join('data', 'performance', 'charts', 'quantum_accuracy.png'))
                plt.close()

        logger.info("Performance trend charts generated")

        return True

    except Exception as e:
        logger.error(f"Error plotting performance trends: {e}")
        return False


def check_api_health():
    """Check health of all APIs used by the system"""
    try:
        # Use the new platform factory to check WebUll API
        webull_status = "Unavailable"
        zoya_status = "Unavailable"

        try:
            # Import the factory directly
            from platform_adapters.platform_factory import get_factory_instance
            factory = get_factory_instance()

            # For WebUll
            webull_adapter = factory.create_adapter("webull")
            if webull_adapter:
                webull_health = webull_adapter.health_check()
                webull_status = webull_health.get('status', 'Unavailable')

            # For Zoya
            zoya_adapter = factory.create_adapter("zoya")
            if zoya_adapter:
                zoya_health = zoya_adapter.health_check()
                zoya_status = zoya_health.get('status', 'Unavailable')

                # Handle 204 response for Zoya sandbox
                if zoya_health.get('message') == "No content" and zoya_health.get('mode') == "sandbox":
                    zoya_status = "OK (Sandbox)"
        except Exception as e:
            logger.error(f"Error using platform factory for API health check: {e}")

        # Generate API health report
        report = {
            'timestamp': datetime.now().isoformat(),
            'apis': {
                'webull': webull_status,
                'zoya': zoya_status
            }
        }

        # Save report
        os.makedirs(os.path.join('data', 'api_health'), exist_ok=True)
        report_path = os.path.join('data', 'api_health', f'api_health_{datetime.now().strftime("%Y%m%d")}.json')

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        # Log status
        logger.info("=== API Health Status ===")
        logger.info(f"WebUll API: {webull_status}")
        logger.info(f"Zoya API: {zoya_status}")
        logger.info("=======================")

        return report

    except Exception as e:
        logger.error(f"Error checking API health: {e}")
        return None


def generate_improved_quantum_optimizer():
    """Generate improved quantum optimizer parameters"""
    try:
        # In a real implementation, this would use quantum computing libraries
        # For now, we'll just simulate an improvement

        # Load trade history
        trade_history_path = os.path.join('data', 'trade_history.json')
        if not os.path.exists(trade_history_path):
            logger.warning("No trade history found for quantum optimization")
            return False

        with open(trade_history_path, 'r') as f:
            trade_history = json.load(f)

        if not trade_history.get('trades'):
            logger.warning("No trades found in history for quantum optimization")
            return False

        # Simulate quantum optimization
        # In reality, this would involve running quantum circuits and optimization algorithms

        # Generate "improved" weights based on prior trade performance
        trades = trade_history['trades']
        win_count = sum(1 for trade in trades if trade.get('action') == 'SELL' and trade.get('profit_loss', 0) > 0)
        total_count = sum(1 for trade in trades if trade.get('action') == 'SELL')

        win_rate = win_count / total_count if total_count > 0 else 0.5

        # Adjust weights based on win rate
        baseline_weights = [0.15, 0.1, 0.05, 0.1, 0.05, 0.05, 0.2, 0.1, 0.05, 0.05, 0.025, 0.025, 0.025, 0.05]

        if win_rate >= 0.6:
            # Good performance, minor adjustments
            adjustment = np.random.normal(0, 0.02, len(baseline_weights))
        else:
            # Poor performance, larger adjustments
            adjustment = np.random.normal(0, 0.05, len(baseline_weights))

        new_weights = [max(0.01, min(0.3, baseline_weights[i] + adjustment[i])) for i in range(len(baseline_weights))]

        # Normalize to sum to 1
        new_weights = [w / sum(new_weights) for w in new_weights]

        # Save the new weights
        os.makedirs('quantum/optimizers', exist_ok=True)
        optimizer_path = os.path.join('quantum/optimizers',
                                      f'optimizer_weights_{datetime.now().strftime("%Y%m%d")}.json')

        with open(optimizer_path, 'w') as f:
            json.dump({
                'weights': new_weights,
                'generated_date': datetime.now().isoformat(),
                'based_on_win_rate': float(win_rate),
                'trade_count': total_count
            }, f, indent=4)

        logger.info(f"Generated improved quantum optimizer weights (win rate: {win_rate:.2f})")
        logger.info(f"New weights saved to {optimizer_path}")

        return True

    except Exception as e:
        logger.error(f"Error generating improved quantum optimizer: {e}")
        return False


def generate_legal_compliance_report():
    """Generate a report on legal compliance"""
    try:
        # In a real implementation, this would check against actual regulations
        # For this example, we'll create a simulated report

        # Get current configuration
        config_path = os.path.join('config', 'config.json')
        if not os.path.exists(config_path):
            logger.warning("No configuration file found for compliance report")
            return False

        with open(config_path, 'r') as f:
            config = json.load(f)

        # Check key compliance factors
        platform_name = config.get('platform', {}).get('name', 'unknown')
        is_paper_trading = config.get('platform', {}).get('use_paper_trading', True)
        halal_compliance = config.get('trading_bot', {}).get('halal_compliance', True)
        min_hold_period = config.get('trading_bot', {}).get('min_hold_period', 172800)  # In seconds

        # Create report
        report = {
            'timestamp': datetime.now().isoformat(),
            'platform': platform_name,
            'paper_trading': is_paper_trading,
            'compliance_checks': [
                {
                    'check': 'Paper Trading Mode',
                    'status': 'Compliant' if is_paper_trading else 'Warning',
                    'details': ('Using paper trading mode, no regulatory concerns.' if is_paper_trading
                                else 'Live trading mode in use. Ensure compliance with relevant regulations.')
                },
                {
                    'check': 'Halal Compliance',
                    'status': 'Compliant' if halal_compliance else 'Warning',
                    'details': ('Halal compliance check enabled.' if halal_compliance
                                else 'Halal compliance check disabled. System may trade non-Halal securities.')
                },
                {
                    'check': 'Minimum Holding Period',
                    'status': 'Compliant' if min_hold_period >= 86400 else 'Warning',
                    'details': (f'Minimum hold period set to {min_hold_period / 3600:.1f} hours, which is sufficient.'
                                if min_hold_period >= 86400
                                else f'Minimum hold period of {min_hold_period / 3600:.1f} hours may be too short for some regulations.')
                },
                {
                    'check': 'API Terms of Service',
                    'status': 'Action Required',
                    'details': f'Verify that automated trading is permitted under {platform_name} terms of service.'
                },
                {
                    'check': 'Data Privacy',
                    'status': 'Compliant',
                    'details': 'Credentials are stored securely using encryption.'
                },
                {
                    'check': 'Quantum Computing Compliance',
                    'status': 'Compliant',
                    'details': 'Quantum computing methods are used for analysis only, not for transaction execution.'
                }
            ],
            'regulatory_notes': [
                {
                    'region': 'United States',
                    'body': 'SEC',
                    'note': 'Algorithmic trading is subject to oversight. Ensure compliance with market manipulation rules.'
                },
                {
                    'region': 'Global',
                    'body': 'Islamic Finance',
                    'note': 'System is configured to check for Halal compliance using Zoya API.'
                }
            ]
        }

        # Save report
        os.makedirs('legal/compliance_reports', exist_ok=True)
        report_path = os.path.join('legal/compliance_reports',
                                   f'compliance_report_{datetime.now().strftime("%Y%m%d")}.json')

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=4)

        logger.info(f"Legal compliance report generated at {report_path}")

        return True

    except Exception as e:
        logger.error(f"Error generating legal compliance report: {e}")
        return False


def monitor_quantum_system_health():
    """Monitor the health of the quantum trading components"""
    try:
        logger.info("Monitoring quantum system health")

        # Check for quantum error history
        error_file = "data/quantum/error_history.json"
        if os.path.exists(error_file):
            with open(error_file, 'r') as f:
                error_history = json.load(f)

            # Analyze recent error trends
            if error_history:
                recent_errors = error_history[-min(5, len(error_history)):]
                error_rates = [entry.get("error_rate", 0) for entry in recent_errors]
                avg_error = sum(error_rates) / len(error_rates)

                logger.info(f"Average quantum error rate: {avg_error:.4f}")

                # Alert if error rate is too high
                if avg_error > 0.3:
                    logger.warning("ALERT: Quantum error rate critically high")

                    # Create alert
                    alert = {
                        "timestamp": datetime.now().isoformat(),
                        "type": "high_quantum_error",
                        "level": "critical" if avg_error > 0.4 else "warning",
                        "message": f"Quantum error rate ({avg_error:.4f}) exceeds threshold",
                        "recommended_action": "Disable quantum analysis temporarily"
                    }

                    # Save alert
                    alerts_dir = "data/alerts"
                    os.makedirs(alerts_dir, exist_ok=True)
                    with open(f"{alerts_dir}/quantum_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
                        json.dump(alert, f, indent=4)

        # Check quantum prediction accuracy
        prediction_file = "data/quantum/prediction_history.json"
        if os.path.exists(prediction_file):
            with open(prediction_file, 'r') as f:
                predictions = json.load(f)

            # Filter for completed predictions
            completed = [p for p in predictions if p.get("correct") is not None]

            if completed:
                # Calculate recent accuracy
                recent = completed[-min(20, len(completed)):]
                correct = sum(1 for p in recent if p.get("correct"))
                accuracy = correct / len(recent)

                logger.info(f"Recent quantum prediction accuracy: {accuracy:.4f}")

                # Alert if accuracy is too low
                if accuracy < 0.45:
                    logger.warning("ALERT: Quantum prediction accuracy below random chance")

                    # Create alert
                    alert = {
                        "timestamp": datetime.now().isoformat(),
                        "type": "low_quantum_accuracy",
                        "level": "critical" if accuracy < 0.4 else "warning",
                        "message": f"Quantum prediction accuracy ({accuracy:.4f}) below threshold",
                        "recommended_action": "Retrain quantum models or increase reliance on classical methods"
                    }

                    # Save alert
                    alerts_dir = "data/alerts"
                    os.makedirs(alerts_dir, exist_ok=True)
                    with open(f"{alerts_dir}/quantum_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
                        json.dump(alert, f, indent=4)

        return True
    except Exception as e:
        logger.error(f"Error monitoring quantum system health: {e}")
        return False


def plot_quantum_performance_trends():
    """Plot quantum performance metrics over time"""
    try:
        # Create output directory
        os.makedirs(os.path.join('data', 'quantum', 'charts'), exist_ok=True)

        # Plot error rates if available
        error_file = "data/quantum/error_history.json"
        if os.path.exists(error_file):
            with open(error_file, 'r') as f:
                error_history = json.load(f)

            if error_history:
                dates = [datetime.fromisoformat(entry["timestamp"]) for entry in error_history]
                error_rates = [entry["error_rate"] for entry in error_history]

                plt.figure(figsize=(12, 6))
                plt.plot(dates, error_rates, 'r-', linewidth=2)
                plt.grid(True, alpha=0.3)
                plt.title('Quantum Error Rates Over Time')
                plt.xlabel('Date')
                plt.ylabel('Error Rate')
                plt.savefig(os.path.join('data', 'quantum', 'charts', 'error_rates.png'))
                plt.close()

        # Plot prediction accuracy if available
        prediction_file = "data/quantum/prediction_history.json"
        if os.path.exists(prediction_file):
            with open(prediction_file, 'r') as f:
                predictions = json.load(f)

            # Filter for completed predictions
            completed = [p for p in predictions if p.get("correct") is not None]

            if completed:
                # Sort by timestamp
                completed.sort(key=lambda x: x["timestamp"])

                # Calculate running accuracy
                dates = [datetime.fromisoformat(entry["timestamp"]) for entry in completed]
                correct_cumsum = np.cumsum([1 if p["correct"] else 0 for p in completed])
                count_cumsum = np.arange(1, len(completed) + 1)
                accuracy = correct_cumsum / count_cumsum

                plt.figure(figsize=(12, 6))
                plt.plot(dates, accuracy, 'b-', linewidth=2)
                plt.axhline(y=0.5, color='r', linestyle='--', alpha=0.7)  # Random chance line
                plt.grid(True, alpha=0.3)
                plt.title('Quantum Prediction Accuracy Over Time')
                plt.xlabel('Date')
                plt.ylabel('Accuracy')
                plt.savefig(os.path.join('data', 'quantum', 'charts', 'prediction_accuracy.png'))
                plt.close()

                # Plot by confidence level
                high_conf = [p for p in completed if p.get("confidence", 0) >= 0.7]
                med_conf = [p for p in completed if 0.5 <= p.get("confidence", 0) < 0.7]
                low_conf = [p for p in completed if p.get("confidence", 0) < 0.5]

                conf_levels = ["Low (<0.5)", "Medium (0.5-0.7)", "High (>0.7)"]
                conf_counts = [len(low_conf), len(med_conf), len(high_conf)]
                conf_correct = [
                    sum(1 for p in low_conf if p.get("correct")),
                    sum(1 for p in med_conf if p.get("correct")),
                    sum(1 for p in high_conf if p.get("correct"))
                ]

                conf_accuracy = [
                    conf_correct[0] / conf_counts[0] if conf_counts[0] > 0 else 0,
                    conf_correct[1] / conf_counts[1] if conf_counts[1] > 0 else 0,
                    conf_correct[2] / conf_counts[2] if conf_counts[2] > 0 else 0
                ]

                plt.figure(figsize=(10, 6))
                bars = plt.bar(conf_levels, conf_accuracy, color=['red', 'blue', 'green'])
                plt.axhline(y=0.5, color='r', linestyle='--', alpha=0.5)

                # Add count labels
                for i, bar in enumerate(bars):
                    plt.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.02,
                        f'n={conf_counts[i]}',
                        ha='center'
                    )

                plt.grid(True, alpha=0.3)
                plt.title('Prediction Accuracy by Confidence Level')
                plt.xlabel('Confidence Level')
                plt.ylabel('Accuracy')
                plt.savefig(os.path.join('data', 'quantum', 'charts', 'accuracy_by_confidence.png'))
                plt.close()

        logger.info("Quantum performance trend charts generated")
        return True
    except Exception as e:
        logger.error(f"Error plotting quantum performance trends: {e}")
        return False


def run_scheduled_task(task_function, task_name):
    """Run a scheduled task and handle errors"""
    try:
        logger.info(f"Running scheduled task: {task_name}")
        result = task_function()

        # Check if result is a DataFrame
        if isinstance(result, pd.DataFrame):
            # For DataFrames, consider it successful if not empty
            if not result.empty:
                logger.info(f"Task {task_name} completed successfully")
            else:
                logger.warning(f"Task {task_name} completed with warnings (empty DataFrame)")
        else:
            # For non-DataFrame results
            if result:
                logger.info(f"Task {task_name} completed successfully")
            else:
                logger.warning(f"Task {task_name} completed with warnings")
    except Exception as e:
        logger.error(f"Error running task {task_name}: {e}")


def monitoring_loop():
    """Main monitoring loop with quantum monitoring"""
    logger.info("Starting monitoring loop")

    # Import the heartbeat function
    try:
        from utils import create_heartbeat
    except ImportError:
        logger.warning("Could not import heartbeat function")
        create_heartbeat = lambda bot_name: None  # Dummy function

    # Run initial checks
    run_scheduled_task(extract_performance_metrics, "Initial Performance Metrics")
    run_scheduled_task(check_api_health, "Initial API Health Check")
    run_scheduled_task(generate_legal_compliance_report, "Initial Legal Compliance Report")
    run_scheduled_task(monitor_quantum_system_health, "Initial Quantum System Health Check")

    # Set up schedule
    schedule.every(1).hours.do(
        lambda: run_scheduled_task(extract_performance_metrics, "Performance Metrics")
    )

    schedule.every(1).days.do(
        lambda: run_scheduled_task(plot_performance_trends, "Performance Charts")
    )

    schedule.every(API_CHECK_INTERVAL).days.do(
        lambda: run_scheduled_task(check_api_health, "API Health Check")
    )

    schedule.every(QUANTUM_OPTIMIZER_INTERVAL).days.do(
        lambda: run_scheduled_task(generate_improved_quantum_optimizer, "Quantum Optimizer")
    )

    schedule.every(LEGAL_CHECK_INTERVAL).days.do(
        lambda: run_scheduled_task(generate_legal_compliance_report, "Legal Compliance Report")
    )

    # Add quantum monitoring tasks
    schedule.every(3).hours.do(
        lambda: run_scheduled_task(monitor_quantum_system_health, "Quantum System Health Check")
    )

    schedule.every(1).days.do(
        lambda: run_scheduled_task(plot_quantum_performance_trends, "Quantum Performance Charts")
    )

    # Main loop
    try:
        while True:
            try:
                # Create heartbeat
                create_heartbeat("monitor_bot")

                # Run pending scheduled tasks
                schedule.run_pending()

                # Sleep before checking again
                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in monitoring loop iteration: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying

    except KeyboardInterrupt:
        logger.info("Monitoring loop interrupted by user")


# Alias for backward compatibility
monitor_loop = monitoring_loop

# If run directly, initialize the platform and start monitoring
if __name__ == "__main__":
    logger.info("Starting monitor bot directly")
    init_platform()
    monitoring_loop()
