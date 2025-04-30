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


# Add this outside of any function, at the module level:
monitor_loop = monitoring_loop  # Alias for backward compatibility
