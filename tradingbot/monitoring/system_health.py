import logging
import os
import json
import time
import psutil
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading

logger = logging.getLogger(__name__)


class SystemMonitor:
    """Monitor system health and resources"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize system monitor with configuration

        Args:
            config: System monitoring configuration
        """
        self.config = config
        self.health_history = []
        self.last_check = 0

        # Create necessary directories
        os.makedirs("data/system_health", exist_ok=True)

        # Start background monitoring thread if enabled
        if self.config.get("background_monitoring", True):
            self.exit_flag = False
            self.monitor_thread = threading.Thread(target=self.background_monitoring_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Background system monitoring started")

        logger.info("System monitor initialized")

    def background_monitoring_loop(self) -> None:
        """Background monitoring loop"""
        check_interval = self.config.get("check_interval", 300)  # 5 minutes

        while not self.exit_flag:
            try:
                self.check_system_health()
            except Exception as e:
                logger.error(f"Error in background health check: {e}")

            # Sleep for the specified interval
            time.sleep(check_interval)

    def check_system_health(self) -> Dict[str, Any]:
        """Check overall system health

        Returns:
            System health data
        """
        try:
            # Calculate time since last check
            now = time.time()
            time_since_last = now - self.last_check
            self.last_check = now

            # Get system information
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Get network information (simplified)
            network_io = psutil.net_io_counters()

            # Get process information
            process = psutil.Process()
            process_cpu = process.cpu_percent(interval=1)
            process_memory = process.memory_info().rss / (1024 * 1024)  # MB

            # Check file system
            log_dir_size = self.get_directory_size("logs")
            data_dir_size = self.get_directory_size("data")

            # Collect health data
            health_data = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "platform": platform.platform(),
                    "python_version": platform.python_version()
                },
                "process": {
                    "cpu_percent": process_cpu,
                    "memory_mb": process_memory,
                    "runtime": self.get_process_runtime()
                },
                "storage": {
                    "log_dir_mb": log_dir_size,
                    "data_dir_mb": data_dir_size
                },
                "time_since_last_check": time_since_last
            }

            # Check for issues
            issues = []

            if cpu_percent > 90:
                issues.append("High CPU usage")

            if memory.percent > 90:
                issues.append("High memory usage")

            if disk.percent > 90:
                issues.append("Low disk space")

            if process_cpu > 80:
                issues.append("High process CPU usage")

            if process_memory > 1000:  # More than 1GB
                issues.append("High process memory usage")

            if log_dir_size > 500:  # More than 500MB
                issues.append("Large log directory")

            health_data["issues"] = issues
            health_data["status"] = "warning" if issues else "ok"

            # Add to history
            self.health_history.append(health_data)

            # Keep history size reasonable
            if len(self.health_history) > 1000:
                self.health_history = self.health_history[-1000:]

            # Save latest health data
            with open("data/system_health/latest.json", 'w') as f:
                json.dump(health_data, f, indent=4)

            # Periodically save full history
            if len(self.health_history) % 10 == 0:
                with open("data/system_health/history.json", 'w') as f:
                    json.dump(self.health_history, f, indent=4)

            # Log health status
            if issues:
                logger.warning(f"System health check found issues: {', '.join(issues)}")
            else:
                logger.info("System health check: OK")

            return health_data
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def get_directory_size(self, path: str) -> float:
        """Get directory size in MB

        Args:
            path: Directory path

        Returns:
            Directory size in MB
        """
        total_size = 0
        if os.path.exists(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)

        return total_size / (1024 * 1024)  # Convert to MB

    def get_process_runtime(self) -> float:
        """Get process runtime in seconds

        Returns:
            Process runtime in seconds
        """
        try:
            process = psutil.Process()
            return time.time() - process.create_time()
        except:
            return 0

    def check_api_health(self) -> Dict[str, Any]:
        """Check health of external APIs

        Returns:
            API health status
        """
        try:
            # This is a placeholder - in a real implementation we would check
            # each API that the system depends on
            api_status = {
                "timestamp": datetime.now().isoformat(),
                "apis": {
                    "webull": self.check_api("webull"),
                    "alphavantage": self.check_api("alphavantage"),
                    "newsapi": self.check_api("newsapi"),
                    "zoya": self.check_api("zoya")
                }
            }

            # Save API status
            with open("data/system_health/api_status.json", 'w') as f:
                json.dump(api_status, f, indent=4)

            return api_status
        except Exception as e:
            logger.error(f"Error checking API health: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def check_api(self, api_name: str) -> Dict[str, Any]:
        """Check health of a single API

        Args:
            api_name: API name

        Returns:
            API health status
        """
        # Simulate API check - in a real implementation we would make actual API calls
        import random

        # 80% chance of success
        if random.random() < 0.8:
            return {
                "status": "ok",
                "response_time": random.uniform(0.1, 0.5)
            }
        else:
            return {
                "status": "error",
                "message": "Simulated API error"
            }

    def cleanup_old_logs(self) -> int:
        """Clean up old log files

        Returns:
            Number of files deleted
        """
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                return 0

            # Get retention period from config (default 30 days)
            retention_days = self.config.get("log_retention_days", 30)
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            files_deleted = 0

            for filename in os.listdir(log_dir):
                file_path = os.path.join(log_dir, filename)

                # Skip directories
                if os.path.isdir(file_path):
                    continue

                # Check file modification time
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if mod_time < cutoff_date:
                    os.remove(file_path)
                    files_deleted += 1

            if files_deleted > 0:
                logger.info(f"Cleaned up {files_deleted} old log files")

            return files_deleted
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            return 0