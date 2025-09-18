#!/usr/bin/env python3
"""
BTCPay Server Health Checker

This script tests the health and connectivity of a BTCPay Server instance.
It checks various endpoints and services to ensure the server is functioning properly.

Usage:
    python test_btcpay_health.py --config universal_config.json
    python test_btcpay_health.py --base-url https://your-btcpay-server.com --api-key your_key --store-id your_store
"""

import json
import requests
import time
import logging
import argparse
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('btcpay_health_check.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BTCPayHealthChecker:
    """BTCPay Server health checker utility."""
    
    def __init__(self, base_url: str, api_key: str, store_id: str):
        """
        Initialize the health checker.
        
        Args:
            base_url (str): BTCPay Server base URL
            api_key (str): API key for authentication
            store_id (str): Store ID to test
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.store_id = store_id
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {api_key}',
            'Content-Type': 'application/json'
        })
        
        logger.info(f"Initialized BTCPay health checker for: {self.base_url}")
    
    def test_server_connectivity(self) -> Tuple[bool, str]:
        """
        Test basic server connectivity.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            response = self.session.get(self.base_url, timeout=10)
            if response.status_code == 200:
                return True, f"Server is reachable (HTTP {response.status_code})"
            else:
                return False, f"Server returned HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Connection failed: {str(e)}"
    
    def test_api_authentication(self) -> Tuple[bool, str]:
        """
        Test API authentication.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            url = urljoin(self.base_url, '/api/v1/stores')
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                stores = response.json()
                if any(store.get('id') == self.store_id for store in stores):
                    return True, f"API authentication successful, store '{self.store_id}' found"
                else:
                    return False, f"API authentication successful, but store '{self.store_id}' not found"
            elif response.status_code == 401:
                return False, "API authentication failed - invalid credentials"
            else:
                return False, f"API request failed with HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"API request failed: {str(e)}"
    
    def test_store_health(self) -> Tuple[bool, str]:
        """
        Test store-specific health.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            url = urljoin(self.base_url, f'/api/v1/stores/{self.store_id}')
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                store_data = response.json()
                return True, f"Store health check passed: {store_data.get('name', 'Unknown')}"
            else:
                return False, f"Store health check failed with HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Store health check failed: {str(e)}"
    
    def test_invoice_creation(self) -> Tuple[bool, str]:
        """
        Test invoice creation capability.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            url = urljoin(self.base_url, f'/api/v1/stores/{self.store_id}/invoices')
            
            # Create a test invoice
            test_invoice_data = {
                "amount": "0.00001",  # Very small amount for testing
                "currency": "BTC",
                "metadata": {
                    "orderId": f"health_check_{int(time.time())}"
                }
            }
            
            response = self.session.post(url, json=test_invoice_data, timeout=10)
            
            if response.status_code == 200:
                invoice_data = response.json()
                invoice_id = invoice_data.get('id')
                return True, f"Invoice creation test passed (Invoice ID: {invoice_id})"
            else:
                return False, f"Invoice creation failed with HTTP {response.status_code}: {response.text}"
        except requests.exceptions.RequestException as e:
            return False, f"Invoice creation test failed: {str(e)}"
    
    def test_webhook_capability(self) -> Tuple[bool, str]:
        """
        Test webhook configuration capability.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            url = urljoin(self.base_url, f'/api/v1/stores/{self.store_id}/webhooks')
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                webhooks = response.json()
                return True, f"Webhook capability test passed ({len(webhooks)} webhooks configured)"
            else:
                return False, f"Webhook capability test failed with HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Webhook capability test failed: {str(e)}"
    
    def test_payment_methods(self) -> Tuple[bool, str]:
        """
        Test available payment methods.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            url = urljoin(self.base_url, f'/api/v1/stores/{self.store_id}/payment-methods')
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                payment_methods = response.json()
                btc_methods = [pm for pm in payment_methods if pm.get('cryptoCode') == 'BTC']
                if btc_methods:
                    return True, f"Payment methods test passed - BTC methods available: {len(btc_methods)}"
                else:
                    return False, "Payment methods test failed - No BTC payment methods available"
            else:
                return False, f"Payment methods test failed with HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Payment methods test failed: {str(e)}"
    
    def run_full_health_check(self) -> Dict:
        """
        Run a comprehensive health check.
        
        Returns:
            Dict: Health check results
        """
        logger.info("Starting BTCPay Server health check...")
        
        tests = [
            ("Server Connectivity", self.test_server_connectivity),
            ("API Authentication", self.test_api_authentication),
            ("Store Health", self.test_store_health),
            ("Invoice Creation", self.test_invoice_creation),
            ("Webhook Capability", self.test_webhook_capability),
            ("Payment Methods", self.test_payment_methods)
        ]
        
        results = {
            "timestamp": time.time(),
            "base_url": self.base_url,
            "store_id": self.store_id,
            "tests": {},
            "overall_status": "unknown",
            "passed_tests": 0,
            "total_tests": len(tests)
        }
        
        for test_name, test_func in tests:
            logger.info(f"Running {test_name} test...")
            try:
                success, message = test_func()
                results["tests"][test_name] = {
                    "status": "passed" if success else "failed",
                    "message": message,
                    "timestamp": time.time()
                }
                if success:
                    results["passed_tests"] += 1
                    logger.info(f"✅ {test_name}: {message}")
                else:
                    logger.error(f"❌ {test_name}: {message}")
            except Exception as e:
                results["tests"][test_name] = {
                    "status": "error",
                    "message": f"Test failed with exception: {str(e)}",
                    "timestamp": time.time()
                }
                logger.error(f"💥 {test_name}: Test failed with exception: {str(e)}")
        
        # Determine overall status
        if results["passed_tests"] == results["total_tests"]:
            results["overall_status"] = "healthy"
        elif results["passed_tests"] > 0:
            results["overall_status"] = "degraded"
        else:
            results["overall_status"] = "unhealthy"
        
        logger.info(f"Health check complete: {results['overall_status']} ({results['passed_tests']}/{results['total_tests']} tests passed)")
        
        return results
    
    def print_summary(self, results: Dict):
        """
        Print a formatted summary of health check results.
        
        Args:
            results (Dict): Health check results
        """
        print("\n" + "="*60)
        print("🔍 BTCPay Server Health Check Summary")
        print("="*60)
        print(f"Server: {results['base_url']}")
        print(f"Store ID: {results['store_id']}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Tests Passed: {results['passed_tests']}/{results['total_tests']}")
        print(f"Timestamp: {time.ctime(results['timestamp'])}")
        print("\nDetailed Results:")
        print("-" * 40)
        
        for test_name, test_result in results["tests"].items():
            status_icon = "✅" if test_result["status"] == "passed" else "❌" if test_result["status"] == "failed" else "💥"
            print(f"{status_icon} {test_name}: {test_result['message']}")
        
        print("\n" + "="*60)
        
        if results["overall_status"] == "healthy":
            print("🎉 BTCPay Server is healthy and ready for use!")
        elif results["overall_status"] == "degraded":
            print("⚠️  BTCPay Server is partially functional. Some features may not work.")
        else:
            print("🚨 BTCPay Server is unhealthy. Please check configuration and server status.")


def load_config(config_file: str) -> Dict:
    """
    Load configuration from JSON file.
    
    Args:
        config_file (str): Path to configuration file
        
    Returns:
        Dict: Configuration dictionary
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise


def main():
    """Main function to run the health check."""
    parser = argparse.ArgumentParser(
        description='BTCPay Server Health Checker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config universal_config.json
  %(prog)s --base-url https://your-btcpay-server.com --api-key your_key --store-id your_store
        """
    )
    
    parser.add_argument('--config', type=str, help='Configuration file path (JSON format)')
    parser.add_argument('--base-url', type=str, help='BTCPay Server base URL')
    parser.add_argument('--api-key', type=str, help='API key for authentication')
    parser.add_argument('--store-id', type=str, help='Store ID to test')
    parser.add_argument('--output', type=str, default='btcpay_health_results.json', help='Output file for results')
    
    args = parser.parse_args()
    
    # Load configuration if provided
    if args.config:
        try:
            config = load_config(args.config)
            # Extract BTCPay settings from config
            btcpay_config = config.get('_invoice_generation', {})
            base_url = args.base_url or btcpay_config.get('base_url')
            api_key = args.api_key or btcpay_config.get('api_key')
            store_id = args.store_id or btcpay_config.get('store_id')
        except Exception as e:
            print(f"❌ Error loading configuration: {str(e)}")
            return 1
    else:
        base_url = args.base_url
        api_key = args.api_key
        store_id = args.store_id
    
    # Validate required parameters
    if not all([base_url, api_key, store_id]):
        print("❌ Error: Missing required parameters. Please provide --config or --base-url, --api-key, and --store-id")
        return 1
    
    try:
        # Create health checker
        checker = BTCPayHealthChecker(base_url, api_key, store_id)
        
        # Run health check
        results = checker.run_full_health_check()
        
        # Print summary
        checker.print_summary(results)
        
        # Save results to file
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Health check results saved to: {args.output}")
        
        # Return appropriate exit code
        if results["overall_status"] == "healthy":
            return 0
        elif results["overall_status"] == "degraded":
            return 1
        else:
            return 2
            
    except KeyboardInterrupt:
        logger.info("Health check cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error during health check: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
