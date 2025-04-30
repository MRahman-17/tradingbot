import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
import ta  # Technical Analysis library

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Technical analysis for trading signals"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize technical analyzer with configuration

        Args:
            config: Technical analysis configuration
        """
        self.config = config
        logger.info("Technical analyzer initialized")

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for a price dataframe

        Args:
            df: Price dataframe with OHLCV data

        Returns:
            DataFrame with added technical indicators
        """
        try:
            # Make sure all required columns exist
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"Missing required columns: {set(required_columns) - set(df.columns)}")
                return df

            # Create a copy to avoid modifying the original
            df_result = df.copy()

            # Moving Averages
            df_result['SMA_5'] = ta.trend.sma_indicator(df_result['Close'], window=5)
            df_result['SMA_10'] = ta.trend.sma_indicator(df_result['Close'], window=10)
            df_result['SMA_20'] = ta.trend.sma_indicator(df_result['Close'], window=20)
            df_result['SMA_50'] = ta.trend.sma_indicator(df_result['Close'], window=50)
            df_result['SMA_200'] = ta.trend.sma_indicator(df_result['Close'], window=200)

            df_result['EMA_5'] = ta.trend.ema_indicator(df_result['Close'], window=5)
            df_result['EMA_10'] = ta.trend.ema_indicator(df_result['Close'], window=10)
            df_result['EMA_20'] = ta.trend.ema_indicator(df_result['Close'], window=20)
            df_result['EMA_50'] = ta.trend.ema_indicator(df_result['Close'], window=50)
            df_result['EMA_200'] = ta.trend.ema_indicator(df_result['Close'], window=200)

            # RSI
            df_result['RSI'] = ta.momentum.rsi(df_result['Close'], window=14)

            # MACD
            macd = ta.trend.MACD(df_result['Close'], window_slow=26, window_fast=12, window_sign=9)
            df_result['MACD'] = macd.macd()
            df_result['MACD_Signal'] = macd.macd_signal()
            df_result['MACD_Hist'] = macd.macd_diff()

            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(df_result['Close'], window=20, window_dev=2)
            df_result['BB_Upper'] = bollinger.bollinger_hband()
            df_result['BB_Middle'] = bollinger.bollinger_mavg()
            df_result['BB_Lower'] = bollinger.bollinger_lband()
            df_result['BB_Width'] = (df_result['BB_Upper'] - df_result['BB_Lower']) / df_result['BB_Middle']

            # Stochastic Oscillator
            stoch = ta.momentum.StochasticOscillator(df_result['High'], df_result['Low'], df_result['Close'], window=14,
                                                     smooth_window=3)
            df_result['Stoch_K'] = stoch.stoch()
            df_result['Stoch_D'] = stoch.stoch_signal()

            # Average True Range (ATR)
            df_result['ATR'] = ta.volatility.average_true_range(df_result['High'], df_result['Low'], df_result['Close'],
                                                                window=14)

            # On-Balance Volume (OBV)
            df_result['OBV'] = ta.volume.on_balance_volume(df_result['Close'], df_result['Volume'])

            # Ichimoku Cloud
            ichimoku = ta.trend.IchimokuIndicator(df_result['High'], df_result['Low'])
            df_result['Ichimoku_Conversion'] = ichimoku.ichimoku_conversion_line()
            df_result['Ichimoku_Base'] = ichimoku.ichimoku_base_line()
            df_result['Ichimoku_A'] = ichimoku.ichimoku_a()
            df_result['Ichimoku_B'] = ichimoku.ichimoku_b()

            # Calculate crossovers
            df_result['SMA_5_10_Crossover'] = np.where(
                (df_result['SMA_5'].shift(1) <= df_result['SMA_10'].shift(1)) &
                (df_result['SMA_5'] > df_result['SMA_10']),
                1, np.where(
                    (df_result['SMA_5'].shift(1) >= df_result['SMA_10'].shift(1)) &
                    (df_result['SMA_5'] < df_result['SMA_10']),
                    -1, 0
                )
            )

            df_result['MACD_Crossover'] = np.where(
                (df_result['MACD'].shift(1) <= df_result['MACD_Signal'].shift(1)) &
                (df_result['MACD'] > df_result['MACD_Signal']),
                1, np.where(
                    (df_result['MACD'].shift(1) >= df_result['MACD_Signal'].shift(1)) &
                    (df_result['MACD'] < df_result['MACD_Signal']),
                    -1, 0
                )
            )

            # Price relative to moving averages
            df_result['Price_vs_SMA_50'] = df_result['Close'] / df_result['SMA_50'] - 1
            df_result['Price_vs_SMA_200'] = df_result['Close'] / df_result['SMA_200'] - 1

            # Fill NaN values
            df_result = df_result.fillna(method='bfill').fillna(method='ffill')

            return df_result
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return df

    def get_technical_signal(self, df: pd.DataFrame) -> float:
        """Calculate a consolidated technical signal from indicators

        Args:
            df: Price dataframe with calculated indicators

        Returns:
            Technical signal score (0-1)
        """
        try:
            if len(df) < 5:
                logger.warning("Not enough data for technical analysis")
                return 0.5  # Neutral

            # Get the most recent values
            latest = df.iloc[-1]

            # Initialize signal components
            trend_signal = 0
            momentum_signal = 0
            volatility_signal = 0
            volume_signal = 0
            pattern_signal = 0

            # Calculate trend signals
            trend_signals = []

            # Moving average relationships
            if latest['Close'] > latest['SMA_50']:
                trend_signals.append(0.6)  # Bullish
            else:
                trend_signals.append(0.4)  # Bearish

            if latest['Close'] > latest['SMA_200']:
                trend_signals.append(0.6)  # Bullish
            else:
                trend_signals.append(0.4)  # Bearish

            if latest['SMA_50'] > latest['SMA_200']:
                trend_signals.append(0.7)  # Strong bullish (golden cross condition)
            else:
                trend_signals.append(0.3)  # Strong bearish (death cross condition)

            # SMA crossovers
            if latest['SMA_5_10_Crossover'] == 1:
                trend_signals.append(0.7)  # Bullish crossover
            elif latest['SMA_5_10_Crossover'] == -1:
                trend_signals.append(0.3)  # Bearish crossover

            # Ichimoku Cloud
            if (latest['Close'] > latest['Ichimoku_A']) and (latest['Close'] > latest['Ichimoku_B']):
                trend_signals.append(0.7)  # Strong bullish
            elif (latest['Close'] < latest['Ichimoku_A']) and (latest['Close'] < latest['Ichimoku_B']):
                trend_signals.append(0.3)  # Strong bearish

            # Average the trend signals
            trend_signal = sum(trend_signals) / len(trend_signals) if trend_signals else 0.5

            # Calculate momentum signals
            momentum_signals = []

            # RSI
            if latest['RSI'] > 70:
                momentum_signals.append(0.3)  # Overbought
            elif latest['RSI'] < 30:
                momentum_signals.append(0.7)  # Oversold
            else:
                momentum_signals.append(0.5 + (latest['RSI'] - 50) / 100)  # Scale from 0.4 to 0.6

            # MACD
            if latest['MACD_Crossover'] == 1:
                momentum_signals.append(0.7)  # Bullish crossover
            elif latest['MACD_Crossover'] == -1:
                momentum_signals.append(0.3)  # Bearish crossover
            else:
                # Existing trend strength
                momentum_signals.append(0.5 + latest['MACD_Hist'] / abs(latest['MACD'] + 0.0001) / 2)

            # Stochastic
            if (latest['Stoch_K'] < 20) and (latest['Stoch_D'] < 20):
                momentum_signals.append(0.7)  # Oversold
            elif (latest['Stoch_K'] > 80) and (latest['Stoch_D'] > 80):
                momentum_signals.append(0.3)  # Overbought

            # Average the momentum signals
            momentum_signal = sum(momentum_signals) / len(momentum_signals) if momentum_signals else 0.5

            # Calculate volatility signals
            volatility_signals = []

            # Bollinger Bands
            if latest['Close'] < latest['BB_Lower']:
                volatility_signals.append(0.7)  # Oversold
            elif latest['Close'] > latest['BB_Upper']:
                volatility_signals.append(0.3)  # Overbought
            else:
                # Position within the bands
                bb_position = (latest['Close'] - latest['BB_Lower']) / (latest['BB_Upper'] - latest['BB_Lower'])
                volatility_signals.append(0.5 + (0.5 - bb_position) / 2)  # Convert to 0.25-0.75 range

            # Bollinger Band width (higher width = higher volatility)
            normalized_width = min(1.0, latest['BB_Width'] / 0.1)  # Normalize to 0-1
            if normalized_width > 0.7:  # High volatility
                volatility_signals.append(0.4)  # Slightly bearish
            elif normalized_width < 0.3:  # Low volatility
                volatility_signals.append(0.6)  # Slightly bullish (consolidation)

            # ATR - higher values indicate higher volatility
            if 'ATR' in latest and latest['ATR'] > 0:
                normalized_atr = min(1.0, latest['ATR'] / (latest['Close'] * 0.05))  # Normalize to 0-1
                if normalized_atr > 0.7:  # High volatility
                    volatility_signals.append(0.4)  # Slightly bearish

            # Average the volatility signals
            volatility_signal = sum(volatility_signals) / len(volatility_signals) if volatility_signals else 0.5

            # Calculate volume signals
            volume_signals = []

            # OBV trend
            if len(df) >= 10:
                obv_trend = (latest['OBV'] - df['OBV'].iloc[-10]) / abs(df['OBV'].iloc[-10] + 0.0001)
                if obv_trend > 0.05:
                    volume_signals.append(0.7)  # Strong bullish volume
                elif obv_trend < -0.05:
                    volume_signals.append(0.3)  # Strong bearish volume
                else:
                    volume_signals.append(0.5)  # Neutral volume

            # Volume change
            if len(df) >= 5:
                avg_volume = df['Volume'].iloc[-5:].mean()
                recent_volume = latest['Volume']
                if recent_volume > avg_volume * 1.5:
                    # High volume combined with price direction
                    if latest['Close'] > df['Close'].iloc[-2]:
                        volume_signals.append(0.7)  # Strong bullish
                    else:
                        volume_signals.append(0.3)  # Strong bearish

            # Average the volume signals
            volume_signal = sum(volume_signals) / len(volume_signals) if volume_signals else 0.5

            # Calculate pattern signals (simplified version)
            pattern_signals = []

            # Simple candlestick patterns
            if len(df) >= 3:
                # Bullish engulfing
                if (df['Close'].iloc[-2] < df['Open'].iloc[-2] and  # Previous bearish
                        df['Close'].iloc[-1] > df['Open'].iloc[-1] and  # Current bullish
                        df['Close'].iloc[-1] > df['Open'].iloc[-2] and  # Current close > previous open
                        df['Open'].iloc[-1] < df['Close'].iloc[-2]):  # Current open < previous close
                    pattern_signals.append(0.7)  # Bullish

                # Bearish engulfing
                if (df['Close'].iloc[-2] > df['Open'].iloc[-2] and  # Previous bullish
                        df['Close'].iloc[-1] < df['Open'].iloc[-1] and  # Current bearish
                        df['Close'].iloc[-1] < df['Open'].iloc[-2] and  # Current close < previous open
                        df['Open'].iloc[-1] > df['Close'].iloc[-2]):  # Current open > previous close
                    pattern_signals.append(0.3)  # Bearish

                # Hammer (potential reversal after downtrend)
                if (df['Close'].iloc[-3] > df['Close'].iloc[-2] and  # Downtrend
                        df['Low'].iloc[-1] < df['Close'].iloc[-1] and  # Long lower shadow
                        (df['Close'].iloc[-1] - df['Low'].iloc[-1]) > 2 * abs(
                            df['Open'].iloc[-1] - df['Close'].iloc[-1]) and
                        (df['High'].iloc[-1] - max(df['Open'].iloc[-1], df['Close'].iloc[-1])) < 0.5 * abs(
                            df['Open'].iloc[-1] - df['Close'].iloc[-1])):
                    pattern_signals.append(0.6)  # Moderately bullish

            # Average the pattern signals
            pattern_signal = sum(pattern_signals) / len(pattern_signals) if pattern_signals else 0.5

            # Combine all signals with weights
            weights = {
                'trend': 0.35,
                'momentum': 0.25,
                'volatility': 0.15,
                'volume': 0.15,
                'pattern': 0.10
            }

            combined_signal = (
                    trend_signal * weights['trend'] +
                    momentum_signal * weights['momentum'] +
                    volatility_signal * weights['volatility'] +
                    volume_signal * weights['volume'] +
                    pattern_signal * weights['pattern']
            )

            # Log signal components
            logger.debug(f"Technical signal components - Trend: {trend_signal:.4f}, Momentum: {momentum_signal:.4f}, " +
                         f"Volatility: {volatility_signal:.4f}, Volume: {volume_signal:.4f}, Pattern: {pattern_signal:.4f}")
            logger.info(f"Combined technical signal: {combined_signal:.4f}")

            return combined_signal
        except Exception as e:
            logger.error(f"Error calculating technical signal: {e}")
            return 0.5  # Neutral on error