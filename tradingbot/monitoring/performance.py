import logging
import os
import json
import time
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """Track and analyze trading performance"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize performance tracker with configuration

        Args:
            config: Performance tracking configuration
        """
        self.config = config
        self.metrics_history = []
        self.load_metrics_history()

        # Create necessary directories
        os.makedirs("data/performance/charts", exist_ok=True)

        logger.info("Performance tracker initialized")

    def load_metrics_history(self) -> None:
        """Load metrics history from file"""
        metrics_path = "data/performance/metrics.json"
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, 'r') as f:
                    self.metrics_history = json.load(f)
                logger.info(f"Loaded {len(self.metrics_history)} metrics records")
            except Exception as e:
                logger.error(f"Error loading metrics history: {e}")

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update metrics with new data

        Args:
            metrics: New metrics data
        """
        # Add to history
        self.metrics_history.append(metrics)

        # Generate charts
        self.generate_performance_charts()

        # Send alerts if performance deteriorates
        self.check_performance_alerts(metrics)

    def generate_performance_charts(self) -> None:
        """Generate performance charts"""
        try:
            if not self.metrics_history:
                logger.warning("No metrics history to generate charts")
                return

            # Convert to DataFrame
            df = pd.DataFrame(self.metrics_history)
            df['date'] = pd.to_datetime(df['date'])

            # Set date as index for easier plotting
            df.set_index('date', inplace=True)

            # Plot win rate over time
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['win_rate'] * 100, 'b-', linewidth=2)
            plt.grid(True, alpha=0.3)
            plt.title('Win Rate Over Time')
            plt.xlabel('Date')
            plt.ylabel('Win Rate (%)')
            plt.tight_layout()
            plt.savefig(os.path.join('data', 'performance', 'charts', 'win_rate.png'))
            plt.close()

            # Plot total profit over time
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['total_profit'], 'g-', linewidth=2)
            plt.grid(True, alpha=0.3)
            plt.title('Total Profit Over Time')
            plt.xlabel('Date')
            plt.ylabel('Profit ($)')
            plt.tight_layout()
            plt.savefig(os.path.join('data', 'performance', 'charts', 'total_profit.png'))
            plt.close()

            # Plot average profit percentage
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['avg_profit_pct'], 'r-', linewidth=2)
            plt.grid(True, alpha=0.3)
            plt.title('Average Profit Percentage Over Time')
            plt.xlabel('Date')
            plt.ylabel('Avg Profit (%)')
            plt.tight_layout()
            plt.savefig(os.path.join('data', 'performance', 'charts', 'avg_profit_pct.png'))
            plt.close()

            # Plot maximum drawdown
            plt.figure(figsize=(12, 6))
            plt.plot(df.index, df['max_drawdown'], 'r-', linewidth=2)
            plt.grid(True, alpha=0.3)
            plt.title('Maximum Drawdown Over Time')
            plt.xlabel('Date')
            plt.ylabel('Max Drawdown (%)')
            plt.tight_layout()
            plt.savefig(os.path.join('data', 'performance', 'charts', 'max_drawdown.png'))
            plt.close()

            # Plot quantum accuracy if available
            if 'quantum_accuracy' in df.columns:
                # Drop NaN values
                df_quantum = df.dropna(subset=['quantum_accuracy'])

                if not df_quantum.empty:
                    plt.figure(figsize=(12, 6))
                    plt.plot(df_quantum.index, df_quantum['quantum_accuracy'] * 100, 'purple', linewidth=2)
                    plt.axhline(y=50, color='r', linestyle='--', alpha=0.5)  # Random chance line
                    plt.grid(True, alpha=0.3)
                    plt.title('Quantum Prediction Accuracy Over Time')
                    plt.xlabel('Date')
                    plt.ylabel('Accuracy (%)')
                    plt.tight_layout()
                    plt.savefig(os.path.join('data', 'performance', 'charts', 'quantum_accuracy.png'))
                    plt.close()

            logger.info("Performance charts generated")
        except Exception as e:
            logger.error(f"Error generating performance charts: {e}")

    def check_performance_alerts(self, metrics: Dict[str, Any]) -> None:
        """Check for performance issues and send alerts

        Args:
            metrics: Latest performance metrics
        """
        try:
            # Check win rate
            win_rate = metrics.get('win_rate', 0)
            if win_rate < 0.4:
                logger.warning(f"Low win rate alert: {win_rate:.2f}")
                self.send_alert("Low Win Rate", f"Current win rate is {win_rate:.2f}, below threshold of 0.4")

            # Check drawdown
            max_drawdown = metrics.get('max_drawdown', 0)
            if max_drawdown > 15:
                logger.warning(f"High drawdown alert: {max_drawdown:.2f}%")
                self.send_alert("High Drawdown",
                                f"Current maximum drawdown is {max_drawdown:.2f}%, above threshold of 15%")

            # Check performance trend if we have enough history
            if len(self.metrics_history) >= 3:
                # Get last three records
                recent = self.metrics_history[-3:]

                # Check if win rate is consistently declining
                win_rates = [r.get('win_rate', 0) for r in recent]
                if win_rates[0] > win_rates[1] > win_rates[2]:
                    logger.warning("Declining win rate trend detected")
                    self.send_alert("Declining Performance",
                                    f"Win rate has declined consistently: {win_rates[0]:.2f} -> {win_rates[1]:.2f} -> {win_rates[2]:.2f}")

                # Check if profit is consistently declining
                profits = [r.get('avg_profit', 0) for r in recent]
                if profits[0] > profits[1] > profits[2]:
                    logger.warning("Declining profit trend detected")
                    self.send_alert("Declining Profit",
                                    f"Average profit has declined consistently: ${profits[0]:.2f} -> ${profits[1]:.2f} -> ${profits[2]:.2f}")
        except Exception as e:
            logger.error(f"Error checking performance alerts: {e}")

    def send_alert(self, title: str, message: str) -> None:
        """Send performance alert

        Args:
            title: Alert title
            message: Alert message
        """
        try:
            # Write alert to file
            os.makedirs("data/alerts", exist_ok=True)

            alert = {
                "timestamp": datetime.now().isoformat(),
                "title": title,
                "message": message,
                "level": "warning"
            }

            with open(f"data/alerts/performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
                json.dump(alert, f, indent=4)

            # Send email if configured
            alert_emails = self.config.get("alert_emails", [])
            if alert_emails:
                logger.info(f"Would send email alert to {', '.join(alert_emails)}")
                # In a real implementation, we would send emails here

            logger.warning(f"Performance alert: {title} - {message}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")