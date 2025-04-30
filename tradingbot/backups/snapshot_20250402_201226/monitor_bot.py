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
        logger.info("============================")

        # Check for quantum metrics
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
