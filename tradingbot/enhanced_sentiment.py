# Install required libraries:
# pip install transformers torch

import logging
import torch
import transformers
import math
from datetime import datetime

logger = logging.getLogger("Enhanced Sentiment")


class EnhancedSentimentAnalyzer:
    def __init__(self):
        try:
            self.finbert = transformers.AutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert')
            self.tokenizer = transformers.AutoTokenizer.from_pretrained('ProsusAI/finbert')
            self.model_loaded = True
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            self.model_loaded = False
            logger.error(f"Error loading FinBERT model: {e}")
            logger.info("Will fall back to basic sentiment analysis")

    def analyze_sentiment(self, text):
        """Use advanced NLP for financial news sentiment analysis"""
        if not self.model_loaded:
            # Fall back to simpler method
            return self._simple_sentiment_analysis(text)

        try:
            # Process text through model
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
            outputs = self.finbert(**inputs)

            # Convert to sentiment score (-1 to 1 scale)
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
            # FinBERT outputs [negative, neutral, positive]
            sentiment_score = probabilities[0][2].item() - probabilities[0][0].item()

            return sentiment_score
        except Exception as e:
            logger.error(f"Error in advanced sentiment analysis: {e}")
            # Fall back to simpler method
            return self._simple_sentiment_analysis(text)

    def _simple_sentiment_analysis(self, text):
        """Legacy simple sentiment analysis as fallback"""
        # Copy the existing _simple_sentiment_analysis method from financial_news_module.py
        # This serves as a fallback when the advanced model fails
        pass
