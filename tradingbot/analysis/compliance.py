import logging
import os
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HalalComplianceChecker:
    """Checker for Halal compliance of stocks"""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize Halal compliance checker with configuration

        Args:
            config: Compliance configuration
        """
        self.config = config
        self.api_key = os.environ.get("ZOYA_API_KEY", "")
        self.use_cache = config.get("use_cache", True)
        self.cache_duration = config.get("cache_duration", 86400)  # 1 day in seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}

    def check_compliance(self, symbol: str) -> Dict[str, Any]:
        """Check if a stock is halal compliant

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with compliance information
        """
        # Check cache first
        if self.use_cache and symbol in self.cache:
            cache_age = datetime.now().timestamp() - self.cache_timestamps.get(symbol, 0)
            if cache_age < self.cache_duration:
                logger.debug(f"Using cached compliance result for {symbol}")
                return self.cache[symbol]

        # Get compliance from API
        if not self.api_key:
            logger.error("Zoya API key not found in environment variables")
            return {
                "symbol": symbol,
                "compliant": False,
                "timestamp": datetime.now().isoformat(),
                "error": "API key not found"
            }

        try:
            # Use GraphQL API for more detailed information
            result = self._check_compliance_graphql(symbol)

            # Cache the result
            if self.use_cache:
                self.cache[symbol] = result
                self.cache_timestamps[symbol] = datetime.now().timestamp()

            return result
        except Exception as e:
            logger.error(f"Error checking compliance for {symbol}: {e}")

            # Return failure result
            return {
                "symbol": symbol,
                "compliant": False,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }

    def _check_compliance_graphql(self, symbol: str) -> Dict[str, Any]:
        """Check compliance using Zoya GraphQL API

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with compliance information
        """
        # GraphQL API endpoint
        url = "https://api.zoya.finance/graphql"

        # GraphQL query
        query = """
        query getReport {
          basicCompliance {
            report(symbol: "%s") {
              exchange
              name
              reportDate
              status
              symbol
              details {
                category
                passed
                failingCriteria {
                  id
                  name
                  value
                  description
                }
              }
            }
          }
        }
        """ % symbol

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Prepare the GraphQL request
        request_data = {
            "query": query
        }

        # Make the request
        response = requests.post(url, headers=headers, json=request_data)

        if response.status_code == 200:
            data = response.json()

            # Extract compliance status
            report = data.get("data", {}).get("basicCompliance", {}).get("report", {})
            status = report.get("status")

            # Build detailed response
            details = report.get("details", [])
            failing_categories = []

            for detail in details:
                if detail.get("passed") is False:
                    failing_criteria = detail.get("failingCriteria", [])
                    for criteria in failing_criteria:
                        failing_categories.append({
                            "category": detail.get("category"),
                            "criteria": criteria.get("name"),
                            "value": criteria.get("value"),
                            "description": criteria.get("description")
                        })

            return {
                "symbol": symbol,
                "name": report.get("name"),
                "compliant": status == "COMPLIANT",
                "status": status,
                "exchange": report.get("exchange"),
                "report_date": report.get("reportDate"),
                "failing_categories": failing_categories,
                "timestamp": datetime.now().isoformat()
            }
        else:
            logger.error(f"Error from Zoya API: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")

    def get_all_compliant_stocks(self) -> List[str]:
        """Get a list of all halal compliant stocks

        Returns:
            List of compliant stock symbols
        """
        # Use REST API to get all compliant stocks
        if not self.api_key:
            logger.error("Zoya API key not found in environment variables")
            return []

        try:
            url = "https://api.zoya.finance/stocks/compliant"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                symbols = [stock.get("symbol") for stock in data.get("data", [])]
                logger.info(f"Retrieved {len(symbols)} compliant stocks")
                return symbols
            else:
                logger.error(f"Error getting compliant stocks: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting compliant stocks: {e}")
            return []
