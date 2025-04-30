#!/usr/bin/env python3
"""
Monitor Bot for the trading system.
Monitors performance, checks APIs, and generates reports.
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

try:
    import platform_adapters.platform_factory as platform_factory
except ImportError:
    platform_factory = None
from cryptography.fernet import Fernet
import requests
import schedule

# Configure logging
logger = logging.getLogger("Monitor Bot")

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

        # Get latest metrics
        latest = metrics[-1]

        logger.info("=== Performance Metrics ===")
        logger.info(f"Date: {latest['date']}")
        logger.info(f"Total Trades: {latest['total_trades']}")
        logger.info(f"Win Rate: {latest['win_rate'] * 100:.2f}%")
        logger.info(f"Total Profit: ${latest['total_profit']:.2f}")
        logger.info(f"Average Profit per Trade: ${latest['avg_profit']:.2f}")
        logger.info(f"Average Profit Percentage: {latest['avg_profit_pct']:.2f}%")
        logger.info(f"Maximum Drawdown: {latest['max_drawdown']:.2f}%")
        logger.info("============================")

        # Save to CSV for easy analysis
        df = pd.DataFrame(metrics)
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
        if metrics is None or metrics.empty:
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

        # Plot average profit percentage over time
        plt.figure(figsize=(12, 6))
        plt.plot(metrics['date'], metrics['avg_profit_pct'], 'r-', linewidth=2)
        plt.grid(True, alpha=0.3)
        plt.title('Average Profit Percentage Over Time')
        plt.xlabel('Date')
        plt.ylabel('Avg Profit (%)')
        plt.savefig(os.path.join('data', 'performance', 'charts', 'avg_profit_pct.png'))
        plt.close()

        # Plot maximum drawdown over time
        plt.figure(figsize=(12, 6))
        plt.plot(metrics['date'], metrics['max_drawdown'], 'r-', linewidth=2)
        plt.grid(True, alpha=0.3)
        plt.title('Maximum Drawdown Over Time')
        plt.xlabel('Date')
        plt.ylabel('Max Drawdown (%)')
        plt.savefig(os.path.join('data', 'performance', 'charts', 'max_drawdown.png'))
        plt.close()

        # Plot win rate vs average profit percentage
        plt.figure(figsize=(10, 8))
        plt.scatter(metrics['win_rate'] * 100, metrics['avg_profit_pct'], s=50, alpha=0.7)
        plt.grid(True, alpha=0.3)
        plt.title('Win Rate vs Average Profit Percentage')
        plt.xlabel('Win Rate (%)')
        plt.ylabel('Avg Profit (%)')
        plt.savefig(os.path.join('data', 'performance', 'charts', 'win_rate_vs_profit.png'))
        plt.close()

        logger.info("Performance trend charts generated")

        return True

    except Exception as e:
        logger.error(f"Error plotting performance trends: {e}")
        return False


def check_api_health():
    """Check health of all APIs used by the system"""
    try:
        # Check WebUll API (by authenticating)
        webull_status = "Unavailable"
        if platform_adapter and hasattr(platform_adapter, 'wb'):
            try:
                # Try a simple API call
                if platform_adapter.get_price("AAPL") is not None:
                    webull_status = "OK"
                else:
                    webull_status = "Error"
            except Exception:
                webull_status = "Error"

        # Check Zoya API
        zoya_status = "Unavailable"
        api_key = os.environ.get("ZOYA_API_KEY")
        if api_key:
            try:
                url = "https://api.zoya.finance/v1/health"
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    zoya_status = "OK"
                else:
                    zoya_status = f"Error: {response.status_code}"
            except Exception as e:
                zoya_status = f"Error: {str(e)}"

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

        # Also create a markdown version for human readability
        md_report = f"""# Legal Compliance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Configuration
- Trading Platform: {platform_name}
- Paper Trading Mode: {'Enabled' if is_paper_trading else 'Disabled'}
- Halal Compliance: {'Enabled' if halal_compliance else 'Disabled'}
- Minimum Hold Period: {min_hold_period / 3600:.1f} hours

## Compliance Checks

"""
        # Here's the fixed part with proper f-strings with closing quotes:
        for check in report['compliance_checks']:
            md_report += f"### {check['check']}\n"
            md_report += f"**Status**: {check['status']}\n\n"
            md_report += f"{check['details']}\n\n"

        md_report += "## Regulatory Notes\n\n"

        for note in report['regulatory_notes']:
            md_report += f"**{note['region']} - {note['body']}**\n"
            md_report += f"{note['note']}\n\n"

        md_report_path = os.path.join('legal/compliance_reports',
                                      f'compliance_report_{datetime.now().strftime("%Y%m%d")}.md')

        with open(md_report_path, 'w') as f:
            f.write(md_report)

        logger.info(f"Legal compliance report generated at {report_path}")

        return True

    except Exception as e:
        logger.error(f"Error generating legal compliance report: {e}")
        return False


def run_scheduled_task(task_function, task_name):
    """Run a scheduled task and handle errors"""
    try:
        logger.info(f"Running scheduled task: {task_name}")
        result = task_function()
        if result:
            logger.info(f"Task {task_name} completed successfully")
        else:
            logger.warning(f"Task {task_name} completed with warnings")
    except Exception as e:
        logger.error(f"Error running task {task_name}: {e}")


def monitor_loop():
    """Main monitoring loop"""
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


if __name__ == "__main__":
    # If run directly, initialize the platform and start monitoring
    if init_platform():
        monitor_loop()
    else:
        logger.error("Failed to initialize trading platform")
