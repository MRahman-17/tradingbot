#!/usr/bin/env python3
"""
Zoya Finance API Adapter
Provides integration with Zoya Finance API for Islamic finance compliance checking.
Handles both sandbox and production environments with proper error handling.
"""
import os
import time
import json
import logging
import requests
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger("Zoya Adapter")


class ZoyaAdapter:
    """
    Adapter for integrating with Zoya Finance API.
    Provides methods to check stock compliance with Islamic finance principles.
    """

    # API URLs
    BASE_URL = "https://api.zoya.finance/v1"
    SANDBOX_URL = "https://sandbox-api.zoya.finance/v1"

    def __init__(self, api_key=None, sandbox_mode=True, retry_count=3, retry_delay=2):
        """Initialize the Zoya adapter"""
        self.sandbox_mode = sandbox_mode
        self.api_url = self.SANDBOX_URL if sandbox_mode else self.BASE_URL
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.session = requests.Session()

        # Set API key
        self.api_key = api_key or os.environ.get("ZOYA_API_KEY")
        if not self.api_key:
            logger.warning("No Zoya API key provided")

        logger.info(f"Zoya Adapter initialized in {'sandbox' if sandbox_mode else 'production'} mode")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        Make a request to the Zoya API with retry logic

        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            Dict: API response data
        """
        # Set up headers
        headers = kwargs.pop('headers', {})
        headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })

        # Set default timeout
        timeout = kwargs.pop('timeout', 30)

        # Build URL
        url = f"{self.api_url}/{endpoint.lstrip('/')}"

        # Attempt request with retry logic
        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = getattr(self.session, method.lower())(
                    url,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )

                # Handle 204 No Content specifically (common with Zoya sandbox)
                if response.status_code == 204:
                    logger.debug("Received 204 No Content response")
                    return {"status": "success", "message": "No content", "data": {}}

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay * (attempt + 2)))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    continue

                # Check for authentication issues
                if response.status_code == 401:
                    logger.error("Authentication failed. Invalid API key.")
                    return {"status": "error", "message": "Authentication failed"}

                # Check for successful response
                response.raise_for_status()

                # Parse JSON response
                try:
                    return response.json()
                except ValueError:
                    # Return empty dict for empty responses
                    if not response.text:
                        return {}
                    # Return text for non-JSON responses
                    return {"text": response.text}

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"API request failed (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))

        # All attempts failed
        error_msg = f"API request failed after {self.retry_count} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"

        logger.error(error_msg)
        return {"status": "error", "message": error_msg}

    def check_health(self) -> Dict:
        """
        Check the health of the Zoya API

        Returns:
            Dict: Health status information
        """
        try:
            response = self._make_request("get", "/health")

            # For sandbox mode, a 204 is treated as healthy
            if self.sandbox_mode and response.get("message") == "No content":
                return {"status": "OK", "mode": "sandbox"}

            # For production, expect a proper response
            if response.get("status") == "success" or "version" in response:
                return {"status": "OK", "mode": "production", "version": response.get("version")}

            # Otherwise, something's wrong
            return {"status": "Error", "message": response.get("message", "Unknown error")}

        except Exception as e:
            logger.error(f"Error checking API health: {str(e)}")
            return {"status": "Error", "message": str(e)}

    def get_stock_compliance(self, symbol: str) -> Dict:
        """
        Get Islamic finance compliance information for a stock

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dict: Compliance information
        """
        try:
            response = self._make_request("get", f"/stocks/{symbol}")

            # Handle sandbox mode with no data
            if self.sandbox_mode and response.get("message") == "No content":
                # Return simulated data for sandbox
                return self._generate_sandbox_compliance(symbol)

            # Handle error responses
            if response.get("status") == "error":
                logger.error(f"Error getting compliance for {symbol}: {response.get('message')}")
                return {"compliant": False, "error": response.get("message")}

            return response

        except Exception as e:
            logger.error(f"Error getting compliance for {symbol}: {str(e)}")
            return {"compliant": False, "error": str(e)}

    def _generate_sandbox_compliance(self, symbol: str) -> Dict:
        """
        Generate simulated compliance data for sandbox mode

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Simulated compliance data
        """
        # Determine compliance based on symbol (simulated)
        # In a real app, you'd never do this - this is just for testing
        first_letter = symbol[0].lower()
        compliant = first_letter in "abcdef"  # Arbitrary rule for simulation

        return {
            "symbol": symbol,
            "compliant": compliant,
            "compliance_score": 75 if compliant else 35,
            "concerns": [] if compliant else ["revenue_from_interest", "debt_level"],
            "sector": "Technology",
            "industry": "Software",
            "note": "Sandbox simulated data - not real compliance information"
        }

    def batch_check_compliance(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Check compliance for multiple stocks in batch

        Args:
            symbols: List of stock symbols

        Returns:
            Dict[str, Dict]: Compliance information by symbol
        """
        try:
            # If sandbox mode, handle directly with simulated data
            if self.sandbox_mode:
                results = {}
                for symbol in symbols:
                    results[symbol] = self._generate_sandbox_compliance(symbol)
                return results

            # Otherwise, use the batch API endpoint
            payload = {"symbols": symbols}
            response = self._make_request("post", "/stocks/batch", json=payload)

            # Handle error responses
            if response.get("status") == "error":
                logger.error(f"Error in batch compliance check: {response.get('message')}")
                return {symbol: {"compliant": False, "error": response.get("message")} for symbol in symbols}

            return response.get("data", {})

        except Exception as e:
            logger.error(f"Error in batch compliance check: {str(e)}")
            return {symbol: {"compliant": False, "error": str(e)} for symbol in symbols}

    def get_compliance_details(self, symbol: str) -> Dict:
        """
        Get detailed compliance analysis for a stock

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Detailed compliance information
        """
        try:
            response = self._make_request("get", f"/stocks/{symbol}/details")

            # Handle sandbox mode with no data
            if self.sandbox_mode and response.get("message") == "No content":
                # Return simulated detailed data for sandbox
                return self._generate_sandbox_compliance_details(symbol)

            # Handle error responses
            if response.get("status") == "error":
                logger.error(f"Error getting compliance details for {symbol}: {response.get('message')}")
                return {"error": response.get("message")}

            return response

        except Exception as e:
            logger.error(f"Error getting compliance details for {symbol}: {str(e)}")
            return {"error": str(e)}

    def _generate_sandbox_compliance_details(self, symbol: str) -> Dict:
        """
        Generate simulated detailed compliance data for sandbox mode

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Simulated detailed compliance data
        """
        # Determine compliance based on symbol (simulated)
        first_letter = symbol[0].lower()
        compliant = first_letter in "abcdef"  # Arbitrary rule for simulation

        # Basic compliance info
        details = {
            "symbol": symbol,
            "compliant": compliant,
            "compliance_score": 75 if compliant else 35,
            "sector": "Technology",
            "industry": "Software",
            "business_activity": {
                "compliant": True,
                "details": "No prohibited business activities detected"
            },
            "financial_ratios": {
                "compliant": compliant,
                "details": {}
            },
            "note": "Sandbox simulated data - not real compliance information"
        }

        # Add simulated financial ratios
        if compliant:
            details["financial_ratios"]["details"] = {
                "interest_income_ratio": {"value": 0.03, "threshold": 0.05, "compliant": True},
                "debt_ratio": {"value": 0.25, "threshold": 0.33, "compliant": True},
                "cash_and_interest_bearing_securities_ratio": {"value": 0.28, "threshold": 0.33, "compliant": True}
            }
        else:
            details["financial_ratios"]["details"] = {
                "interest_income_ratio": {"value": 0.07, "threshold": 0.05, "compliant": False},
                "debt_ratio": {"value": 0.42, "threshold": 0.33, "compliant": False},
                "cash_and_interest_bearing_securities_ratio": {"value": 0.31, "threshold": 0.33, "compliant": True}
            }

        return details

    def get_stock_purity(self, symbol: str) -> Dict:
        """
        Get purity calculation for a stock

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Purity information
        """
        try:
            response = self._make_request("get", f"/stocks/{symbol}/purity")

            # Handle sandbox mode with no data
            if self.sandbox_mode and response.get("message") == "No content":
                # Return simulated purity data for sandbox
                return self._generate_sandbox_purity(symbol)

            # Handle error responses
            if response.get("status") == "error":
                logger.error(f"Error getting purity for {symbol}: {response.get('message')}")
                return {"error": response.get("message")}

            return response

        except Exception as e:
            logger.error(f"Error getting purity for {symbol}: {str(e)}")
            return {"error": str(e)}

    def _generate_sandbox_purity(self, symbol: str) -> Dict:
        """
        Generate simulated purity data for sandbox mode

        Args:
            symbol: Stock symbol

        Returns:
            Dict: Simulated purity data
        """
        # Determine compliance based on symbol (simulated)
        first_letter = symbol[0].lower()
        compliant = first_letter in "abcdef"  # Arbitrary rule for simulation

        # Generate purity percentage based on compliance
        purity_percent = 92.5 if compliant else 65.2

        return {
            "symbol": symbol,
            "purity_percent": purity_percent,
            "purity_calculation": {
                "income_from_compliant_sources": 1 - (purity_percent / 100),
                "breakdown": {
                    "interest_income": 0.05,
                    "prohibited_business_revenue": 0.02
                }
            },
            "purification_amount": {
                "per_share": 0.12,
                "calculation_method": "dividend_method"
            },
            "note": "Sandbox simulated data - not real purity information"
        }

    def get_market_screening(self,
                             market: str = "US",
                             filter_compliant: bool = True,
                             limit: int = 20,
                             offset: int = 0) -> Dict:
        """
        Get a screened list of stocks from a market

        Args:
            market: Market to screen (e.g., 'US', 'UK')
            filter_compliant: Only return compliant stocks
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Dict: Screened stocks
        """
        try:
            params = {
                "market": market,
                "compliant": "true" if filter_compliant else "false",
                "limit": limit,
                "offset": offset
            }

            response = self._make_request("get", "/stocks/screening", params=params)

            # Handle sandbox mode with no data
            if self.sandbox_mode and response.get("message") == "No content":
                # Return simulated screening data for sandbox
                return self._generate_sandbox_screening(market, filter_compliant, limit, offset)

            # Handle error responses
            if response.get("status") == "error":
                logger.error(f"Error getting market screening: {response.get('message')}")
                return {"error": response.get("message")}

            return response

        except Exception as e:
            logger.error(f"Error getting market screening: {str(e)}")
            return {"error": str(e)}

    def _generate_sandbox_screening(self, market: str, filter_compliant: bool,
                                    limit: int, offset: int) -> Dict:
        """
        Generate simulated screening data for sandbox mode

        Args:
            market: Market to screen
            filter_compliant: Only return compliant stocks
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Dict: Simulated screening data
        """
        # Simulated symbols
        all_symbols = [
            {"symbol": "AAPL", "name": "Apple Inc.", "compliant": True},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "compliant": True},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "compliant": False},
            {"symbol": "GOOG", "name": "Alphabet Inc.", "compliant": True},
            {"symbol": "META", "name": "Meta Platforms Inc.", "compliant": False},
            {"symbol": "TSLA", "name": "Tesla Inc.", "compliant": True},
            {"symbol": "BRK.A", "name": "Berkshire Hathaway Inc.", "compliant": False},
            {"symbol": "NVDA", "name": "NVIDIA Corporation", "compliant": True},
            {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "compliant": False},
            {"symbol": "JNJ", "name": "Johnson & Johnson", "compliant": True}
        ]

        # Filter by compliance if needed
        if filter_compliant:
            filtered_symbols = [s for s in all_symbols if s["compliant"]]
        else:
            filtered_symbols = all_symbols

        # Apply pagination
        paginated = filtered_symbols[offset:offset + limit]

        # Add extra details for simulation
        for stock in paginated:
            stock["market"] = market
            stock["compliance_score"] = 85 if stock["compliant"] else 40
            stock["sector"] = "Technology" if "OO" in stock["symbol"] else "Finance"

        return {
            "results": paginated,
            "total": len(filtered_symbols),
            "limit": limit,
            "offset": offset,
            "note": "Sandbox simulated data - not real screening information"
        }

    def get_purification_calculation(self, symbol: str,
                                     shares: int,
                                     method: str = "dividend") -> Dict:
        """
        Calculate purification amount for a stock holding

        Args:
            symbol: Stock symbol
            shares: Number of shares held
            method: Purification method ('dividend' or 'market_cap')

        Returns:
            Dict: Purification calculation
        """
        try:
            params = {
                "shares": shares,
                "method": method
            }

            response = self._make_request("get", f"/stocks/{symbol}/purification", params=params)

            # Handle sandbox mode with no data
            if self.sandbox_mode and response.get("message") == "No content":
                # Return simulated purification data for sandbox
                return self._generate_sandbox_purification(symbol, shares, method)

            # Handle error responses
            if response.get("status") == "error":
                logger.error(f"Error getting purification for {symbol}: {response.get('message')}")
                return {"error": response.get("message")}

            return response

        except Exception as e:
            logger.error(f"Error getting purification for {symbol}: {str(e)}")
            return {"error": str(e)}

    def _generate_sandbox_purification(self, symbol: str, shares: int, method: str) -> Dict:
        """
        Generate simulated purification data for sandbox mode

        Args:
            symbol: Stock symbol
            shares: Number of shares held
            method: Purification method

        Returns:
            Dict: Simulated purification data
        """
        # Generate per-share amount based on symbol (simulated)
        first_letter = symbol[0].lower()
        compliant = first_letter in "abcdef"  # Arbitrary rule for simulation

        # Per-share amounts
        if compliant:
            per_share = 0.05
        else:
            per_share = 0.18

        # Total amount
        total = per_share * shares

        return {
            "symbol": symbol,
            "shares": shares,
            "purification_method": method,
            "per_share_amount": per_share,
            "total_amount": total,
            "calculation_details": {
                "interest_income": 0.7 * total,
                "prohibited_revenue": 0.3 * total
            },
            "note": "Sandbox simulated data - not real purification information"
        }

    def health_check(self) -> Dict:
        """
        Perform a health check on the Zoya API connection

        Returns:
            Dict: Health check results
        """
        try:
            # Check API health
            health = self.check_health()

            # Add API key status
            if not self.api_key:
                health["status"] = "Error"
                health["message"] = "No API key provided"

            # Add mode information
            health["sandbox_mode"] = self.sandbox_mode

            # For sandbox mode, check if this is using the detected sandbox key
            if self.sandbox_mode and self.api_key and self.api_key.startswith("sandbox-"):
                health["api_key_valid_for_mode"] = True
            elif not self.sandbox_mode and self.api_key and not self.api_key.startswith("sandbox-"):
                health["api_key_valid_for_mode"] = True
            else:
                health["api_key_valid_for_mode"] = False
                health["message"] = "API key does not match the selected mode"

            return health

        except Exception as e:
            logger.error(f"Health check error: {str(e)}")
            return {
                "status": "Error",
                "message": str(e),
                "sandbox_mode": self.sandbox_mode
            }

    def close(self):
        """Close the adapter and clean up resources"""
        try:
            self.session.close()
            logger.info("Zoya adapter closed")
        except Exception as e:
            logger.error(f"Error closing adapter: {str(e)}")


# Helper factory function to create adapter instance
def create_zoya_adapter(sandbox_mode=True, api_key=None):
    """
    Create a Zoya adapter instance with settings from environment variables

    Args:
        sandbox_mode: Use sandbox mode
        api_key: Override environment API key

    Returns:
        ZoyaAdapter: Configured adapter instance
    """
    # Use environment API key if not specified
    if api_key is None:
        api_key = os.environ.get("ZOYA_API_KEY")

    # Create and return adapter
    adapter = ZoyaAdapter(api_key=api_key, sandbox_mode=sandbox_mode)

    return adapter


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create adapter
    adapter = create_zoya_adapter()

    try:
        # Check health
        health = adapter.health_check()
        print(f"API Health: {health['status']}")

        # Check compliance for a stock
        compliance = adapter.get_stock_compliance("AAPL")
        print(f"AAPL Compliance: {compliance}")

        # Batch check compliance
        batch = adapter.batch_check_compliance(["MSFT", "GOOG", "AMZN"])
        print(f"Batch Compliance Results: {len(batch)} stocks")

    finally:
        # Close adapter
        adapter.close()
