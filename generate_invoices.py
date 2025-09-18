#!/usr/bin/env python3
"""
BTCPay Server Invoice Generator

This script generates a specified number of invoices using the BTCPay Server API.
It supports batch processing, error handling, and progress tracking.

Requirements:
- BTCPay Server instance with API access
- Valid API key with invoice creation permissions
- Store ID from your BTCPay Server store

Usage:
    python generate_invoices.py --api-key YOUR_API_KEY --store-id YOUR_STORE_ID --count 1000
"""

import argparse
import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import aiohttp
import requests
from tqdm import tqdm


class BTCPayInvoiceGenerator:
    """BTCPay Server invoice generator with async support and error handling."""
    
    def __init__(self, api_key: str, store_id: str, base_url: str):
        """Initialize the invoice generator.
        
        Args:
            api_key: BTCPay Server API key
            store_id: Store ID from BTCPay Server
            base_url: Base URL of BTCPay Server instance (e.g., https://btcpay.example.com)
        """
        self.api_key = api_key
        self.store_id = store_id
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1/stores/{self.store_id}/invoices"
        
        self.headers = {
            'Authorization': f'token {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('invoice_generation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Statistics tracking
        self.stats = {
            'total_requested': 0,
            'successful': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
        # Store generated invoices for export
        self.generated_invoices: List[Dict] = []
        self.failed_invoices: List[Dict] = []

    def generate_invoice_data(self, index: int) -> Dict:
        """Generate randomized invoice data.
        
        Args:
            index: Invoice index for unique identification
            
        Returns:
            Dictionary containing invoice data
        """
        # amounts $1
        amount = round(1, 2)
        
        # Randomize currencies (you can adjust this list)
        currencies = ['USD']
        currency = random.choice(currencies)
        
        # Generate realistic item descriptions
        items = [
            'Digital Product Purchase',
            'Software License',
            'Consultation Service',
            'E-book Download',
            'Course Access',
            'Premium Subscription',
            'API Access Credits',
            'Digital Asset',
            'Service Fee',
            'Product Bundle'
        ]
        
        invoice_data = {
            'amount': str(amount),
            'currency': currency,
            'posData': json.dumps({
                'invoiceIndex': index,
                'generatedAt': datetime.now().isoformat(),
                'batchId': f'batch-{int(time.time())}'
            }),
            'metadata': {
                'orderId': f'INV-{datetime.now().strftime("%Y%m%d")}-{index:06d}',
                'itemDesc': random.choice(items),
                'buyerName': f'Customer-{index:06d}',
                'buyerEmail': f'customer{index:06d}@example.com',
                'itemCode': f'ITEM-{random.randint(1000, 9999)}',
                'generationBatch': True
            }
        }
        
        return invoice_data

    async def create_invoice_async(self, session: aiohttp.ClientSession, invoice_data: Dict, index: int) -> Tuple[bool, Dict]:
        """Create a single invoice asynchronously.
        
        Args:
            session: aiohttp session
            invoice_data: Invoice data dictionary
            index: Invoice index
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        try:
            async with session.post(
                self.api_url,
                json=invoice_data,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                result = await response.json()
                
                if response.status == 200:
                    self.stats['successful'] += 1
                    invoice_result = {
                        'index': index,
                        'success': True,
                        'invoice_id': result.get('id'),
                        'order_id': invoice_data['metadata']['orderId'],
                        'amount': invoice_data['amount'],
                        'currency': invoice_data['currency'],
                        'status': result.get('status'),
                        'checkout_link': result.get('checkoutLink'),
                        'created_time': result.get('createdTime'),
                        'expiration_time': result.get('expirationTime')
                    }
                    self.generated_invoices.append(invoice_result)
                    return True, invoice_result
                else:
                    error_msg = result.get('message', f'HTTP {response.status}')
                    self.logger.error(f"Failed to create invoice {index}: {error_msg}")
                    self.stats['failed'] += 1
                    
                    failed_result = {
                        'index': index,
                        'success': False,
                        'error': error_msg,
                        'order_id': invoice_data['orderId'],
                        'amount': invoice_data['amount'],
                        'currency': invoice_data['currency']
                    }
                    self.failed_invoices.append(failed_result)
                    return False, failed_result
                    
        except asyncio.TimeoutError:
            error_msg = "Request timeout"
            self.logger.error(f"Timeout creating invoice {index}")
            self.stats['failed'] += 1
            failed_result = {
                'index': index,
                'success': False,
                'error': error_msg,
                'order_id': invoice_data['orderId']
            }
            self.failed_invoices.append(failed_result)
            return False, failed_result
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error creating invoice {index}: {error_msg}")
            self.stats['failed'] += 1
            failed_result = {
                'index': index,
                'success': False,
                'error': error_msg,
                'order_id': invoice_data['orderId']
            }
            self.failed_invoices.append(failed_result)
            return False, failed_result

    def test_connection(self) -> bool:
        """Test connection to BTCPay Server API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_url = f"{self.base_url}/api/v1/stores/{self.store_id}"
            response = requests.get(test_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                store_info = response.json()
                self.logger.info(f"Successfully connected to store: {store_info.get('name', 'Unknown')}")
                return True
            else:
                self.logger.error(f"Connection test failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test error: {str(e)}")
            return False

    async def generate_invoices_batch(self, count: int, batch_size: int = 50, delay: float = 0.1) -> None:
        """Generate invoices in batches with rate limiting.
        
        Args:
            count: Total number of invoices to generate
            batch_size: Number of concurrent requests per batch
            delay: Delay between batches in seconds
        """
        self.stats['total_requested'] = count
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"Starting generation of {count} invoices (batch size: {batch_size})")
        
        connector = aiohttp.TCPConnector(limit=batch_size, limit_per_host=batch_size)
        timeout = aiohttp.ClientTimeout(total=300)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create progress bar
            pbar = tqdm(total=count, desc="Generating invoices")
            
            # Process invoices in batches
            for batch_start in range(0, count, batch_size):
                batch_end = min(batch_start + batch_size, count)
                batch_tasks = []
                
                # Create tasks for current batch
                for i in range(batch_start, batch_end):
                    invoice_data = self.generate_invoice_data(i + 1)
                    task = self.create_invoice_async(session, invoice_data, i + 1)
                    batch_tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Update progress bar
                pbar.update(len(batch_tasks))
                
                # Log batch completion
                successful_in_batch = sum(1 for success, _ in batch_results if isinstance(success, bool) and success)
                self.logger.info(
                    f"Batch {batch_start//batch_size + 1}: "
                    f"{successful_in_batch}/{len(batch_tasks)} successful"
                )
                
                # Rate limiting delay between batches
                if batch_end < count:
                    await asyncio.sleep(delay)
            
            pbar.close()
        
        self.stats['end_time'] = datetime.now()
        self.print_summary()

    def print_summary(self) -> None:
        """Print generation summary statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        success_rate = (self.stats['successful'] / self.stats['total_requested']) * 100
        
        print("\n" + "="*60)
        print("INVOICE GENERATION SUMMARY")
        print("="*60)
        print(f"Total Requested:    {self.stats['total_requested']:,}")
        print(f"Successful:         {self.stats['successful']:,}")
        print(f"Failed:             {self.stats['failed']:,}")
        print(f"Success Rate:       {success_rate:.1f}%")
        print(f"Duration:           {duration}")
        print(f"Rate:               {self.stats['successful'] / duration.total_seconds():.2f} invoices/second")
        print("="*60)

    def export_results(self, output_dir: str = "invoice_results") -> None:
        """Export generation results to JSON files.
        
        Args:
            output_dir: Directory to save result files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export successful invoices
        if self.generated_invoices:
            success_file = output_path / f"successful_invoices_{timestamp}.json"
            with open(success_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'total_count': len(self.generated_invoices),
                        'generated_at': datetime.now().isoformat(),
                        'store_id': self.store_id
                    },
                    'invoices': self.generated_invoices
                }, f, indent=2)
            print(f"Successful invoices exported to: {success_file}")
        
        # Export failed invoices
        if self.failed_invoices:
            failed_file = output_path / f"failed_invoices_{timestamp}.json"
            with open(failed_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'total_count': len(self.failed_invoices),
                        'generated_at': datetime.now().isoformat(),
                        'store_id': self.store_id
                    },
                    'failed_invoices': self.failed_invoices
                }, f, indent=2)
            print(f"Failed invoices exported to: {failed_file}")
        
        # Export summary statistics
        summary_file = output_path / f"generation_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'statistics': {
                    **self.stats,
                    'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                    'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
                    'success_rate_percent': (self.stats['successful'] / self.stats['total_requested']) * 100
                },
                'configuration': {
                    'store_id': self.store_id,
                    'base_url': self.base_url
                }
            }, f, indent=2)
        print(f"Summary statistics exported to: {summary_file}")


def load_config(config_file: str) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Configuration file not found: {config_file}")
        raise
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in configuration file: {str(e)}")
        raise
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")
        raise


def validate_config(config: Dict) -> bool:
    """Validate configuration file values."""
    # Handle universal config format
    if '_invoice_generation' in config:
        # Universal config format - check _invoice_generation section
        invoice_config = config['_invoice_generation']
        required_fields = ['api_key', 'store_id']
        for field in required_fields:
            if field not in invoice_config:
                print(f"Config error: missing required field '{field}' in _invoice_generation section")
                return False
        
        # Validate optional numeric fields in _invoice_generation section
        numeric_fields = ['count', 'batch_size', 'delay']
        for field in numeric_fields:
            if field in invoice_config and not isinstance(invoice_config[field], (int, float)):
                print(f"Config error: '{field}' must be a number")
                return False
    else:
        # Legacy config format - check root level
        required_fields = ['api_key', 'store_id']
        for field in required_fields:
            if field not in config:
                print(f"Config error: missing required field '{field}'")
                return False
        
        # Validate optional numeric fields
        numeric_fields = ['count', 'batch_size', 'delay']
        for field in numeric_fields:
            if field in config and not isinstance(config[field], (int, float)):
                print(f"Config error: '{field}' must be a number")
                return False
    
    return True


def merge_config_with_args(config: Dict, args: argparse.Namespace) -> argparse.Namespace:
    """Merge configuration file values with command line arguments.
    Supports both legacy config format and universal config format."""
    
    # Handle universal config format
    if '_invoice_generation' in config:
        # Universal config format
        invoice_config = config['_invoice_generation']
        
        if not args.api_key and 'api_key' in invoice_config:
            args.api_key = invoice_config['api_key']
        
        if not args.store_id and 'store_id' in invoice_config:
            args.store_id = invoice_config['store_id']
        
        if args.base_url == 'https://btcpay.example.com' and 'base_url' in invoice_config:
            args.base_url = invoice_config['base_url']
        
        if args.count == 1000 and 'count' in invoice_config:
            args.count = invoice_config['count']
        
        if args.batch_size == 50 and 'batch_size' in invoice_config:
            args.batch_size = invoice_config['batch_size']
        
        if args.delay == 0.1 and 'delay' in invoice_config:
            args.delay = invoice_config['delay']
        
        if args.output_dir == 'invoice_results' and 'output_dir' in invoice_config:
            args.output_dir = invoice_config['output_dir']
    
    else:
        # Legacy config format
        if not args.api_key and 'api_key' in config:
            args.api_key = config['api_key']
        
        if not args.store_id and 'store_id' in config:
            args.store_id = config['store_id']
        
        if args.base_url == 'https://btcpay.example.com' and 'base_url' in config:
            args.base_url = config['base_url']
        
        if args.count == 1000 and 'count' in config:
            args.count = config['count']
        
        if args.batch_size == 50 and 'batch_size' in config:
            args.batch_size = config['batch_size']
        
        if args.delay == 0.1 and 'delay' in config:
            args.delay = config['delay']
        
        if args.output_dir == 'invoice_results' and 'output_dir' in config:
            args.output_dir = config['output_dir']
    
    return args


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description='Generate invoices using BTCPay Server API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --api-key abc123 --store-id store123 --count 1000
  %(prog)s --api-key abc123 --store-id store123 --count 100 --batch-size 25 --delay 0.5
  %(prog)s --config config.json
        """
    )
    
    parser.add_argument('--config', type=str, help='Configuration file path (JSON format)')
    parser.add_argument('--api-key', help='BTCPay Server API key')
    parser.add_argument('--store-id', help='BTCPay Server store ID')
    parser.add_argument('--base-url', default='https://btcpay.example.com', 
                       help='BTCPay Server base URL (default: https://btcpay.example.com)')
    parser.add_argument('--count', type=int, default=1000,
                       help='Number of invoices to generate (default: 1000)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Number of concurrent requests per batch (default: 50)')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='Delay between batches in seconds (default: 0.1)')
    parser.add_argument('--output-dir', default='invoice_results',
                       help='Output directory for result files (default: invoice_results)')
    parser.add_argument('--test-only', action='store_true',
                       help='Only test connection, do not generate invoices')
    
    args = parser.parse_args()
    
    # Load configuration file if provided
    if args.config:
        try:
            config = load_config(args.config)
            if not validate_config(config):
                print(f"❌ Configuration validation failed")
                return 1
            args = merge_config_with_args(config, args)
            print(f"✅ Loaded configuration from: {args.config}")
        except Exception as e:
            print(f"❌ Error loading configuration: {str(e)}")
            return 1
    
    # Validate required arguments
    if not args.api_key:
        print("❌ Error: --api-key is required (or specify in config file)")
        return 1
    
    if not args.store_id:
        print("❌ Error: --store-id is required (or specify in config file)")
        return 1
    
    # Validate arguments
    if args.count <= 0:
        print("Error: Count must be positive")
        return 1
    
    if args.batch_size <= 0:
        print("Error: Batch size must be positive")
        return 1
    
    # Initialize generator
    generator = BTCPayInvoiceGenerator(
        api_key=args.api_key,
        store_id=args.store_id,
        base_url=args.base_url
    )
    
    # Test connection
    print("Testing connection to BTCPay Server...")
    if not generator.test_connection():
        print("❌ Connection test failed. Please check your API key, store ID, and base URL.")
        return 1
    
    print("✅ Connection test successful!")
    
    if args.test_only:
        print("Test completed successfully. Use --count to generate invoices.")
        return 0
    
    try:
        # Generate invoices
        print(f"\nStarting generation of {args.count:,} invoices...")
        asyncio.run(generator.generate_invoices_batch(
            count=args.count,
            batch_size=args.batch_size,
            delay=args.delay
        ))
        
        # Export results
        generator.export_results(args.output_dir)
        
        if generator.stats['successful'] > 0:
            print(f"\n✅ Successfully generated {generator.stats['successful']:,} invoices!")
        
        if generator.stats['failed'] > 0:
            print(f"⚠️  {generator.stats['failed']:,} invoices failed to generate.")
            print("Check the failed_invoices_*.json file for details.")
        
        return 0 if generator.stats['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        generator.export_results(args.output_dir)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
