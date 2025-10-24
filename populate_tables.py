#!/usr/bin/env python3
"""
Database Payments Table Populator

This script populates the Payments table with fake payment data.
It generates realistic payment records with all required fields and supports batch processing.

Table "Payments":
- Id: text
- Blob: bytea
- InvoiceDataId: text
- Accounted: bool
- Blob2: jsonb
- PaymentMethodId: text
- Amount: numeric
- Create: timestampz
- Currency: text
- Status: text

Usage:
    python populate_tables.py --config universal_config.json --count 1000
"""

import argparse
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2 is required for database connectivity.")
    print("Install it with: pip install psycopg2-binary")
    exit(1)

from tqdm import tqdm


class PaymentsTablePopulator:
    """Database Payments table populator with batch processing and error handling."""
    
    def __init__(self, db_config: Dict):
        """Initialize the payments populator.
        
        Args:
            db_config: Database configuration dictionary
        """
        self.db_config = db_config
        
        # Setup logging
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/payments_population.log'),
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
        
        # Store generated payments for export
        self.generated_payments: List[Dict] = []
        self.failed_payments: List[Dict] = []

    def generate_payment_data(self, index: int) -> Dict:
        """Generate randomized payment data.
        
        Args:
            index: Payment index for unique identification
            
        Returns:
            Dictionary containing payment data
        """
        # Generate unique ID
        payment_id = str(uuid.uuid4())
        
        # Generate invoice data ID (simulate reference to invoice)
        invoice_data_id = f"INV-{datetime.now().strftime('%Y%m%d')}-{index:06d}"
        
        # Random amounts between $0.50 and $100.00
        amount = round(random.uniform(0.50, 100.00), 2)
        
        # Random currencies
        currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY']
        currency = random.choice(currencies)
        
        # Random payment methods
        payment_methods = [
            'BTC', 'LTC', 'BCH', 'ETH', 'XMR', 'DASH', 'ZEC',
            'Credit Card', 'PayPal', 'Bank Transfer', 'Stripe'
        ]
        payment_method_id = random.choice(payment_methods)
        
        # Random statuses
        statuses = ['New', 'Processing', 'Settled', 'Invalid', 'Expired', 'Paid']
        status = random.choice(statuses)
        
        # Random accounted status (mostly true for settled payments)
        accounted = status in ['Settled', 'Paid'] and random.random() > 0.1
        
        # Generate random creation time (last 30 days)
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        create_time = datetime.now() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # Generate blob data (simulate binary payment data)
        blob_data = f"payment_data_{index}_{int(time.time())}".encode('utf-8')
        
        # Generate JSON blob2 (payment metadata)
        blob2_data = {
            'payment_index': index,
            'generated_at': datetime.now().isoformat(),
            'transaction_hash': f"tx_{random.randint(100000, 999999):06d}",
            'block_height': random.randint(800000, 900000) if payment_method_id in ['BTC', 'LTC', 'BCH'] else None,
            'confirmations': random.randint(1, 6) if payment_method_id in ['BTC', 'LTC', 'BCH'] else None,
            'network_fee': round(random.uniform(0.0001, 0.01), 6) if payment_method_id in ['BTC', 'LTC', 'BCH'] else None,
            'payment_provider': 'BTCPay Server' if payment_method_id in ['BTC', 'LTC', 'BCH'] else 'Stripe',
            'customer_info': {
                'email': f'customer{index:06d}@example.com',
                'name': f'Customer {index:06d}',
                'country': random.choice(['US', 'CA', 'GB', 'DE', 'FR', 'AU', 'JP'])
            }
        }
        
        payment_data = {
            'Id': payment_id,
            'Blob': blob_data,
            'InvoiceDataId': invoice_data_id,
            'Accounted': accounted,
            'Blob2': json.dumps(blob2_data),
            'PaymentMethodId': payment_method_id,
            'Amount': amount,
            'Create': create_time,
            'Currency': currency,
            'Status': status
        }
        
        return payment_data

    def test_connection(self) -> bool:
        """Test database connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            self.logger.info("Successfully connected to database")
            return True
            
        except Exception as e:
            self.logger.error(f"Database connection test failed: {str(e)}")
            return False

    def create_payments_table_if_not_exists(self) -> bool:
        """Create Payments table if it doesn't exist.
        
        Returns:
            True if table exists or was created successfully, False otherwise
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'payments'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                self.logger.info("Creating Payments table...")
                cursor.execute("""
                    CREATE TABLE payments (
                        "Id" text PRIMARY KEY,
                        "Blob" bytea,
                        "InvoiceDataId" text,
                        "Accounted" boolean,
                        "Blob2" jsonb,
                        "PaymentMethodId" text,
                        "Amount" numeric,
                        "Create" timestamp with time zone,
                        "Currency" text,
                        "Status" text
                    );
                """)
                conn.commit()
                self.logger.info("Payments table created successfully")
            else:
                self.logger.info("Payments table already exists")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating table: {str(e)}")
            return False

    def insert_payments_batch(self, payments: List[Dict]) -> Tuple[int, int]:
        """Insert a batch of payments into the database.
        
        Args:
            payments: List of payment dictionaries
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for payment in payments:
                try:
                    cursor.execute("""
                        INSERT INTO payments (
                            "Id", "Blob", "InvoiceDataId", "Accounted", "Blob2", 
                            "PaymentMethodId", "Amount", "Create", "Currency", "Status"
                        ) VALUES (
                            %(Id)s, %(Blob)s, %(InvoiceDataId)s, %(Accounted)s, %(Blob2)s,
                            %(PaymentMethodId)s, %(Amount)s, %(Create)s, %(Currency)s, %(Status)s
                        )
                    """, payment)
                    
                    successful += 1
                    self.generated_payments.append({
                        'index': payment.get('index', 0),
                        'success': True,
                        'payment_id': payment['Id'],
                        'invoice_data_id': payment['InvoiceDataId'],
                        'amount': payment['Amount'],
                        'currency': payment['Currency'],
                        'status': payment['Status'],
                        'payment_method': payment['PaymentMethodId']
                    })
                    
                except Exception as e:
                    failed += 1
                    self.logger.error(f"Failed to insert payment {payment.get('Id', 'unknown')}: {str(e)}")
                    self.failed_payments.append({
                        'index': payment.get('index', 0),
                        'success': False,
                        'error': str(e),
                        'payment_id': payment.get('Id', 'unknown')
                    })
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Batch insertion error: {str(e)}")
            failed += len(payments)
            successful = 0
        
        return successful, failed

    def populate_payments(self, count: int, batch_size: int = 100) -> None:
        """Populate the Payments table with fake data.
        
        Args:
            count: Total number of payments to generate
            batch_size: Number of payments per batch
        """
        self.stats['total_requested'] = count
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"Starting population of {count} payments (batch size: {batch_size})")
        
        # Create progress bar
        pbar = tqdm(total=count, desc="Populating payments")
        
        # Process payments in batches
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_payments = []
            
            # Generate payment data for current batch
            for i in range(batch_start, batch_end):
                payment_data = self.generate_payment_data(i + 1)
                payment_data['index'] = i + 1
                batch_payments.append(payment_data)
            
            # Insert batch
            successful, failed = self.insert_payments_batch(batch_payments)
            
            # Update statistics
            self.stats['successful'] += successful
            self.stats['failed'] += failed
            
            # Update progress bar
            pbar.update(len(batch_payments))
            
            # Log batch completion
            self.logger.info(
                f"Batch {batch_start//batch_size + 1}: "
                f"{successful}/{len(batch_payments)} successful"
            )
        
        pbar.close()
        
        self.stats['end_time'] = datetime.now()
        self.print_summary()

    def print_summary(self) -> None:
        """Print population summary statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        success_rate = (self.stats['successful'] / self.stats['total_requested']) * 100
        
        print("\n" + "="*60)
        print("PAYMENTS POPULATION SUMMARY")
        print("="*60)
        print(f"Total Requested:    {self.stats['total_requested']:,}")
        print(f"Successful:        {self.stats['successful']:,}")
        print(f"Failed:            {self.stats['failed']:,}")
        print(f"Success Rate:      {success_rate:.1f}%")
        print(f"Duration:          {duration}")
        print(f"Rate:              {self.stats['successful'] / duration.total_seconds():.2f} payments/second")
        print("="*60)

    def export_results(self, output_dir: str = "payment_results") -> None:
        """Export population results to JSON files.
        
        Args:
            output_dir: Directory to save result files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export successful payments
        if self.generated_payments:
            success_file = output_path / f"successful_payments_{timestamp}.json"
            with open(success_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'total_count': len(self.generated_payments),
                        'generated_at': datetime.now().isoformat(),
                        'table_name': 'payments'
                    },
                    'payments': self.generated_payments
                }, f, indent=2)
            print(f"Successful payments exported to: {success_file}")
        
        # Export failed payments
        if self.failed_payments:
            failed_file = output_path / f"failed_payments_{timestamp}.json"
            with open(failed_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'total_count': len(self.failed_payments),
                        'generated_at': datetime.now().isoformat(),
                        'table_name': 'payments'
                    },
                    'failed_payments': self.failed_payments
                }, f, indent=2)
            print(f"Failed payments exported to: {failed_file}")
        
        # Export summary statistics
        summary_file = output_path / f"population_summary_{timestamp}.json"
        with open(summary_file, 'w') as f:
            json.dump({
                'statistics': {
                    **self.stats,
                    'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                    'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None,
                    'success_rate_percent': (self.stats['successful'] / self.stats['total_requested']) * 100
                },
                'configuration': {
                    'table_name': 'payments',
                    'database_host': self.db_config.get('host', 'unknown')
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
    if '_payments_population' in config:
        # Universal config format - check _payments_population section
        payments_config = config['_payments_population']
        required_fields = ['host', 'database', 'user', 'password']
        for field in required_fields:
            if field not in payments_config:
                print(f"Config error: missing required field '{field}' in _payments_population section")
                return False
        
        # Validate optional numeric fields in _payments_population section
        numeric_fields = ['count', 'batch_size', 'port']
        for field in numeric_fields:
            if field in payments_config and not isinstance(payments_config[field], (int, float)):
                print(f"Config error: '{field}' must be a number")
                return False
    else:
        # Legacy config format - check root level
        required_fields = ['host', 'database', 'user', 'password']
        for field in required_fields:
            if field not in config:
                print(f"Config error: missing required field '{field}'")
                return False
        
        # Validate optional numeric fields
        numeric_fields = ['count', 'batch_size', 'port']
        for field in numeric_fields:
            if field in config and not isinstance(config[field], (int, float)):
                print(f"Config error: '{field}' must be a number")
                return False
    
    return True


def merge_config_with_args(config: Dict, args: argparse.Namespace) -> argparse.Namespace:
    """Merge configuration file values with command line arguments.
    Supports both legacy config format and universal config format."""
    
    # Handle universal config format
    if '_payments_population' in config:
        # Universal config format
        payments_config = config['_payments_population']
        
        if not args.host and 'host' in payments_config:
            args.host = payments_config['host']
        
        if not args.database and 'database' in payments_config:
            args.database = payments_config['database']
        
        if not args.user and 'user' in payments_config:
            args.user = payments_config['user']
        
        if not args.password and 'password' in payments_config:
            args.password = payments_config['password']
        
        if args.port == 5432 and 'port' in payments_config:
            args.port = payments_config['port']
        
        if args.count == 1000 and 'count' in payments_config:
            args.count = payments_config['count']
        
        if args.batch_size == 100 and 'batch_size' in payments_config:
            args.batch_size = payments_config['batch_size']
        
        if args.output_dir == 'payment_results' and 'output_dir' in payments_config:
            args.output_dir = payments_config['output_dir']
    
    else:
        # Legacy config format
        if not args.host and 'host' in config:
            args.host = config['host']
        
        if not args.database and 'database' in config:
            args.database = config['database']
        
        if not args.user and 'user' in config:
            args.user = config['user']
        
        if not args.password and 'password' in config:
            args.password = config['password']
        
        if args.port == 5432 and 'port' in config:
            args.port = config['port']
        
        if args.count == 1000 and 'count' in config:
            args.count = config['count']
        
        if args.batch_size == 100 and 'batch_size' in config:
            args.batch_size = config['batch_size']
        
        if args.output_dir == 'payment_results' and 'output_dir' in config:
            args.output_dir = config['output_dir']
    
    return args


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description='Populate Payments table with fake payment data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --host localhost --database testdb --user postgres --password secret --count 1000
  %(prog)s --config universal_config.json --count 100 --batch-size 50
        """
    )
    
    parser.add_argument('--config', type=str, help='Configuration file path (JSON format)')
    parser.add_argument('--host', help='Database host')
    parser.add_argument('--database', help='Database name')
    parser.add_argument('--user', help='Database user')
    parser.add_argument('--password', help='Database password')
    parser.add_argument('--port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('--count', type=int, default=1000,
                       help='Number of payments to generate (default: 1000)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Number of payments per batch (default: 100)')
    parser.add_argument('--output-dir', default='payment_results',
                       help='Output directory for result files (default: payment_results)')
    parser.add_argument('--test-only', action='store_true',
                       help='Only test connection, do not populate table')
    
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
    if not args.host:
        print("❌ Error: --host is required (or specify in config file)")
        return 1
    
    if not args.database:
        print("❌ Error: --database is required (or specify in config file)")
        return 1
    
    if not args.user:
        print("❌ Error: --user is required (or specify in config file)")
        return 1
    
    if not args.password:
        print("❌ Error: --password is required (or specify in config file)")
        return 1
    
    # Validate arguments
    if args.count <= 0:
        print("Error: Count must be positive")
        return 1
    
    if args.batch_size <= 0:
        print("Error: Batch size must be positive")
        return 1
    
    # Prepare database configuration
    db_config = {
        'host': args.host,
        'database': args.database,
        'user': args.user,
        'password': args.password,
        'port': args.port
    }
    
    # Initialize populator
    populator = PaymentsTablePopulator(db_config)
    
    # Test connection
    print("Testing database connection...")
    if not populator.test_connection():
        print("❌ Database connection test failed. Please check your database credentials.")
        return 1
    
    print("✅ Database connection test successful!")
    
    # Create table if it doesn't exist
    if not populator.create_payments_table_if_not_exists():
        print("❌ Failed to create or verify Payments table.")
        return 1
    
    if args.test_only:
        print("Test completed successfully. Use --count to populate the table.")
        return 0
    
    try:
        # Populate payments
        print(f"\nStarting population of {args.count:,} payments...")
        populator.populate_payments(
            count=args.count,
            batch_size=args.batch_size
        )
        
        # Export results
        populator.export_results(args.output_dir)
        
        if populator.stats['successful'] > 0:
            print(f"\n✅ Successfully populated {populator.stats['successful']:,} payments!")
        
        if populator.stats['failed'] > 0:
            print(f"⚠️  {populator.stats['failed']:,} payments failed to insert.")
            print("Check the failed_payments_*.json file for details.")
        
        return 0 if populator.stats['failed'] == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Population interrupted by user")
        populator.export_results(args.output_dir)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
