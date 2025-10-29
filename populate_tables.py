#!/usr/bin/env python3
"""
Database Payments and Invoices Table Populator

This script populates the Payments and/or Invoices tables with fake data.
It generates realistic records with all required fields and supports batch processing.
Note: When populating both tables, invoices are populated first so payments can reference them.

Table "Payments":
- Id: text
- Blob: bytea
- InvoiceDataId: text
- Accounted: bool
- Blob2: jsonb
- PaymentMethodId: text
- Amount: numeric
- Created: timestampz
- Currency: text
- Status: text

Table "Invoices":
- Id: text
- Blob: bytea
- Created: timestamptz
- ExceptionStatus: text
- Status: text
- StoreDataId: text
- Archived: bool
- Blob2: jsonb
- Amount: numeric
- Currency: text

Usage:
    # Populate payments table only
    python populate_tables.py --config universal_config.json --count 1000
    
    # Populate invoices table only
    python populate_tables.py --config universal_config.json --populate-invoices --invoice-count 1000
    
    # Populate both tables (invoices first, then payments that reference them)
    python populate_tables.py --config universal_config.json --count 1000 --populate-invoices --invoice-count 1000
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


def generate_base58_id(length: int = 22) -> str:
    """Generate a BTCPay Server style invoice ID."""
    # Base58 alphabet (no 0, O, I, l)
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    return ''.join(random.choice(alphabet) for _ in range(length))


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

    def generate_payment_data(self, index: int, invoice_id: str = None, key_path: str = None, destination: str = None) -> Dict:
        """Generate randomized payment data.
        
        Args:
            index: Payment index for unique identification
            invoice_id: Optional invoice ID to reference (if None, generates a fake one)
            key_path: Optional keyPath from invoice (if None, generates a random one)
            destination: Optional destination address from invoice (if None, generates a random one)
            
        Returns:
            Dictionary containing payment data
        """
        # Generate unique ID
        payment_id = str(uuid.uuid4())
        # Generate invoice data ID (use provided invoice_id or simulate reference to invoice)
        invoice_data_id = invoice_id if invoice_id else f"INV-{datetime.now().strftime('%Y%m%d')}-{index:06d}"
        amount = 1.00
        currency = 'USD'
        payment_method_id = 'BTC-CHAIN'
        status = 'Settled'
        accounted = False
        create_time = datetime.now()
        
        # Generate blob data (simulate binary payment data)
        blob_data = "".encode('utf-8')
        
        # Use provided destination from invoice, or generate new one
        if destination is None:
            # testnet_address_chars = '023456789acdefghjklmnpqrstuvwxyz'
            # address_suffix = ''.join(random.choice(testnet_address_chars) for _ in range(31))
            # destination = f"tb1q{address_suffix}"
            destination = "tb1qu0rmltek4y653wh3twc3p6u2zf3ev4ew6g0zxc"
        
        # Use provided keyPath from invoice, or generate new one
        if key_path is None:
            key_path = f"{random.randint(0, 20)}/{random.randint(0, 10)}"
        
        # Generate outpoint (transaction hash-like string)
        # Format: alphanumeric string followed by dash and output index
        # Example: "11cec777e08regjnwerolfgmfoiermvmrvikevrvb-1"
        # outpoint_chars = '0123456789abcdefghijklmnopqrstuvwxyz'
        # tx_hash = ''.join(random.choice(outpoint_chars) for _ in range(40))
        # output_index = random.randint(0, 10)
        # outpoint = f"{tx_hash}-{output_index}"
        outpoint = "11cec777e08a3ab323e368d2637b1f36517df6ca06ad3c11196bddcfb774346b-1"
        
        # Generate confirmation count (1-6 for most payments)
        confirmation_count = random.randint(3, 6)
        
        # Generate JSON blob2 in BTCPay Server payment format
        blob2_data = {
            'details': {
                'keyPath': key_path,
                'outpoint': outpoint,
                'confirmationCount': confirmation_count
            },
            'version': 2,
            'destination': destination,
            'divisibility': 8
        }
        
        payment_data = {
            'Id': payment_id,
            'Blob': blob_data,
            'InvoiceDataId': invoice_data_id,
            'Accounted': accounted,
            'Blob2': json.dumps(blob2_data),
            'PaymentMethodId': payment_method_id,
            'Amount': amount,
            'Created': create_time,
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
                    WHERE table_name = 'Payments'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                self.logger.info("Creating Payments table...")
                cursor.execute("""
                    CREATE TABLE Payments (
                        "Id" text PRIMARY KEY,
                        "Blob" bytea,
                        "InvoiceDataId" text,
                        "Accounted" boolean,
                        "Blob2" jsonb,
                        "PaymentMethodId" text,
                        "Amount" numeric,
                        "Created" timestamp with time zone,
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
                        INSERT INTO "Payments" (
                            "Id", "Blob", "InvoiceDataId", "Accounted", "Blob2", 
                            "PaymentMethodId", "Amount", "Created", "Currency", "Status"
                        ) VALUES (
                            %(Id)s, %(Blob)s, %(InvoiceDataId)s, %(Accounted)s, %(Blob2)s,
                            %(PaymentMethodId)s, %(Amount)s, %(Created)s, %(Currency)s, %(Status)s
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

    def populate_payments(self, count: int, batch_size: int = 100, invoice_ids: Optional[List[str]] = None, invoice_details: Optional[Dict[str, Dict]] = None) -> None:
        """Populate the Payments table with fake data.
        
        Args:
            count: Total number of payments to generate
            batch_size: Number of payments per batch
            invoice_ids: Optional list of invoice IDs to reference. If provided, payments will reference these IDs.
            invoice_details: Optional dict mapping invoice_id to {key_path, destination} for matching payment details.
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
                # Use invoice ID from list if available (round-robin if more payments than invoices)
                invoice_id = None
                key_path = None
                destination = None
                
                if invoice_ids:
                    invoice_id = invoice_ids[i % len(invoice_ids)]
                    # Get key_path and destination from invoice_details if available
                    if invoice_details and invoice_id in invoice_details:
                        details = invoice_details[invoice_id]
                        key_path = details.get('key_path')
                        destination = details.get('destination')
                
                payment_data = self.generate_payment_data(
                    i + 1, 
                    invoice_id=invoice_id,
                    key_path=key_path,
                    destination=destination
                )
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


class InvoicesTablePopulator:
    """Database Invoices table populator with batch processing and error handling."""
    
    def __init__(self, db_config: Dict, store_id: Optional[str] = None):
        """Initialize the invoices populator.
        
        Args:
            db_config: Database configuration dictionary
            store_id: Optional store ID to use for all invoices
        """
        self.db_config = db_config
        self.store_id = store_id
        
        # Setup logging
        os.makedirs('logs', exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/invoices_population.log'),
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
        # Generate unique ID in BTCPay Server format (base58, 22 chars)
        invoice_id = generate_base58_id(22)
        
        # Generate store data ID (simulate reference to store)
        store_data_id = self.store_id if self.store_id else f"STORE-{random.randint(1, 10):02d}"
        amount = 1.00
        currency = 'USD'
        status = 'Settled'
        exception_status = ''
        archived = False
        created_time = datetime.now()
        
        # Generate blob data (simulate binary invoice data)
        blob_data = "".encode('utf-8')
        
        # Calculate expiration times (24 hours from now)
        expiration_time = int((created_time + timedelta(hours=24)).timestamp())
        monitoring_expiration = int((created_time + timedelta(hours=48)).timestamp())
        
        # Generate realistic BTC exchange rate (between 50k and 150k USD)
        btc_rate = 100000
        
        # Generate realistic testnet address (Bech32 format: tb1q...)
        # Using a simplified approach - in reality these are complex but for testing we can generate similar format
        # testnet_address_chars = '023456789acdefghjklmnpqrstuvwxyz'
        # address_suffix = ''.join(random.choice(testnet_address_chars) for _ in range(31))
        # destination = f"tb1q{address_suffix}"
        destination = "tb1qu0rmltek4y653wh3twc3p6u2zf3ev4ew6g0zxc"
        
        # Generate keyPath (derivation path like "0/1", "1/2", etc.)
        key_path = f"{random.randint(0, 10)}/{random.randint(0, 10)}"
        key_index = random.randint(0, 1000)
        
        # Generate account derivation (similar to tpub...)
        tpub_chars = '0123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        tpub_suffix = ''.join(random.choice(tpub_chars) for _ in range(97))
        account_derivation = f"tpub{tpub_suffix}"
        
        # Generate item description
        item_desc = random.choice([
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
        ])
        
        # Generate fee rates (between 0.1 and 5.0)
        fee_rate = round(random.uniform(0.1, 5.0), 1)
        
        # Generate JSON blob2 in BTCPay Server format
        blob2_data = {
            'rates': {
                'BTC': str(btc_rate)
            },
            'prompts': {
                'BTC-CHAIN': {
                    'details': {
                        'keyPath': key_path,
                        'keyIndex': key_index,
                        'payjoinEnabled': True,
                        'accountDerivation': account_derivation,
                        'recommendedFeeRate': fee_rate,
                        'paymentMethodFeeRate': fee_rate
                    },
                    'currency': 'BTC',
                    'destination': destination,
                    'divisibility': 8
                }
            },
            'version': 3,
            'metadata': {
                'orderId': str(index),
                'itemDesc': item_desc
            },
            'serverUrl': 'http://localhost',
            'speedPolicy': 1,
            'internalTags': [],
            'expirationTime': expiration_time,
            'receiptOptions': {},
            'fullNotifications': True,
            'monitoringExpiration': monitoring_expiration
        }
        
        invoice_data = {
            'Id': invoice_id,
            'Blob': blob_data,
            'Created': created_time,
            'ExceptionStatus': exception_status,
            'Status': status,
            'StoreDataId': store_data_id,
            'Archived': archived,
            'Blob2': json.dumps(blob2_data),
            'Amount': amount,
            'Currency': currency
        }
        
        return invoice_data

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

    def create_invoices_table_if_not_exists(self) -> bool:
        """Create Invoices table if it doesn't exist.
        
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
                    WHERE table_name = 'Invoices'
                );
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                self.logger.info("Creating Invoices table...")
                cursor.execute("""
                    CREATE TABLE Invoices (
                        "Id" text PRIMARY KEY,
                        "Blob" bytea,
                        "Created" timestamp with time zone,
                        "ExceptionStatus" text,
                        "Status" text,
                        "StoreDataId" text,
                        "Archived" boolean,
                        "Blob2" jsonb,
                        "Amount" numeric,
                        "Currency" text
                    );
                """)
                conn.commit()
                self.logger.info("Invoices table created successfully")
            else:
                self.logger.info("Invoices table already exists")
            
            cursor.close()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating table: {str(e)}")
            return False

    def insert_invoices_batch(self, invoices: List[Dict]) -> Tuple[int, int]:
        """Insert a batch of invoices into the database.
        
        Args:
            invoices: List of invoice dictionaries
            
        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for invoice in invoices:
                try:
                    cursor.execute("""
                        INSERT INTO "Invoices" (
                            "Id", "Blob", "Created", "ExceptionStatus", "Status", 
                            "StoreDataId", "Archived", "Blob2", "Amount", "Currency"
                        ) VALUES (
                            %(Id)s, %(Blob)s, %(Created)s, %(ExceptionStatus)s, %(Status)s,
                            %(StoreDataId)s, %(Archived)s, %(Blob2)s, %(Amount)s, %(Currency)s
                        )
                    """, invoice)
                    
                    successful += 1
                    # Extract key_path and destination from blob2
                    key_path = None
                    destination = None
                    try:
                        blob2_json = json.loads(invoice['Blob2'])
                        if 'prompts' in blob2_json and 'BTC-CHAIN' in blob2_json['prompts']:
                            btc_chain = blob2_json['prompts']['BTC-CHAIN']
                            destination = btc_chain.get('destination')
                            if 'details' in btc_chain and 'keyPath' in btc_chain['details']:
                                key_path = btc_chain['details']['keyPath']
                    except (json.JSONDecodeError, KeyError):
                        pass
                    
                    self.generated_invoices.append({
                        'index': invoice.get('index', 0),
                        'success': True,
                        'invoice_id': invoice['Id'],
                        'store_data_id': invoice['StoreDataId'],
                        'amount': invoice['Amount'],
                        'currency': invoice['Currency'],
                        'status': invoice['Status'],
                        'exception_status': invoice['ExceptionStatus'],
                        'archived': invoice['Archived'],
                        'key_path': key_path,
                        'destination': destination
                    })
                    
                except Exception as e:
                    failed += 1
                    self.logger.error(f"Failed to insert invoice {invoice.get('Id', 'unknown')}: {str(e)}")
                    self.failed_invoices.append({
                        'index': invoice.get('index', 0),
                        'success': False,
                        'error': str(e),
                        'invoice_id': invoice.get('Id', 'unknown')
                    })
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Batch insertion error: {str(e)}")
            failed += len(invoices)
            successful = 0
        
        return successful, failed

    def populate_invoices(self, count: int, batch_size: int = 100) -> None:
        """Populate the Invoices table with fake data.
        
        Args:
            count: Total number of invoices to generate
            batch_size: Number of invoices per batch
        """
        self.stats['total_requested'] = count
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"Starting population of {count} invoices (batch size: {batch_size})")
        
        # Create progress bar
        pbar = tqdm(total=count, desc="Populating invoices")
        
        # Process invoices in batches
        for batch_start in range(0, count, batch_size):
            batch_end = min(batch_start + batch_size, count)
            batch_invoices = []
            
            # Generate invoice data for current batch
            for i in range(batch_start, batch_end):
                invoice_data = self.generate_invoice_data(i + 1)
                invoice_data['index'] = i + 1
                batch_invoices.append(invoice_data)
            
            # Insert batch
            successful, failed = self.insert_invoices_batch(batch_invoices)
            
            # Update statistics
            self.stats['successful'] += successful
            self.stats['failed'] += failed
            
            # Update progress bar
            pbar.update(len(batch_invoices))
            
            # Log batch completion
            self.logger.info(
                f"Batch {batch_start//batch_size + 1}: "
                f"{successful}/{len(batch_invoices)} successful"
            )
        
        pbar.close()
        
        self.stats['end_time'] = datetime.now()
        self.print_summary()

    def print_summary(self) -> None:
        """Print population summary statistics."""
        duration = self.stats['end_time'] - self.stats['start_time']
        success_rate = (self.stats['successful'] / self.stats['total_requested']) * 100
        
        print("\n" + "="*60)
        print("INVOICES POPULATION SUMMARY")
        print("="*60)
        print(f"Total Requested:    {self.stats['total_requested']:,}")
        print(f"Successful:        {self.stats['successful']:,}")
        print(f"Failed:            {self.stats['failed']:,}")
        print(f"Success Rate:      {success_rate:.1f}%")
        print(f"Duration:          {duration}")
        print(f"Rate:              {self.stats['successful'] / duration.total_seconds():.2f} invoices/second")
        print("="*60)

    def export_results(self, output_dir: str = "invoice_results") -> None:
        """Export population results to JSON files.
        
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
                        'table_name': 'invoices'
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
                        'table_name': 'invoices'
                    },
                    'failed_invoices': self.failed_invoices
                }, f, indent=2)
            print(f"Failed invoices exported to: {failed_file}")
        
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
                    'table_name': 'invoices',
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
        
        # Handle store_id in legacy config format
        if not args.store_id and 'store_id' in config:
            args.store_id = config['store_id']
    
    # Handle invoice generation config if present (for store_id) - works for both universal and legacy formats
    if '_invoice_generation' in config:
        invoice_config = config['_invoice_generation']
        
        if not args.store_id and 'store_id' in invoice_config:
            args.store_id = invoice_config['store_id']
    
    return args


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description='Populate Payments and/or Invoices tables with fake data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Populate payments table only
  %(prog)s --host localhost --database testdb --user postgres --password secret --count 1000
  
  # Populate invoices table only
  %(prog)s --host localhost --database testdb --user postgres --password secret --populate-invoices --invoice-count 1000
  
  # Populate both tables
  %(prog)s --config universal_config.json --count 100 --populate-invoices --invoice-count 100
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
    
    # Invoice population arguments
    parser.add_argument('--populate-invoices', action='store_true',
                       help='Populate invoices table with fake data')
    parser.add_argument('--invoice-batch-size', type=int, default=100,
                       help='Number of invoices per batch (default: 100)')
    parser.add_argument('--invoice-output-dir', default='invoice_results',
                       help='Output directory for invoice result files (default: invoice_results)')
    parser.add_argument('--store-id', help='Store ID to use for invoices (from _invoice_generation in config)')
    
    args = parser.parse_args()
    args.populate_invoices = True
    
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
    
    # Create payments table if it doesn't exist
    if not populator.create_payments_table_if_not_exists():
        print("❌ Failed to create or verify Payments table.")
        return 1
    
    # Initialize invoice populator if needed
    invoice_populator = None
    if args.populate_invoices:
        invoice_populator = InvoicesTablePopulator(db_config, store_id=args.store_id)
        
        # Create invoices table if it doesn't exist
        if not invoice_populator.create_invoices_table_if_not_exists():
            print("❌ Failed to create or verify Invoices table.")
            return 1
    
    if args.test_only:
        print("Test completed successfully. Use --count to populate the table(s).")
        return 0
    
    try:
        # Populate invoices first (if requested) - payments reference invoices
        invoice_ids = None
        invoice_details = None
        if args.populate_invoices and invoice_populator:
            print(f"\nStarting population of {args.count:,} invoices...")
            invoice_populator.populate_invoices(
                count=args.count,
                batch_size=args.batch_size
            )
            
            # Export invoice results
            invoice_populator.export_results(args.invoice_output_dir)
            
            if invoice_populator.stats['successful'] > 0:
                print(f"\n✅ Successfully populated {invoice_populator.stats['successful']:,} invoices!")
                
                # Extract invoice IDs and details (key_path, destination) from generated invoices
                invoice_ids = [inv['invoice_id'] for inv in invoice_populator.generated_invoices]
                invoice_details = {
                    inv['invoice_id']: {
                        'key_path': inv.get('key_path'),
                        'destination': inv.get('destination')
                    }
                    for inv in invoice_populator.generated_invoices
                }
                print(f"   Using {len(invoice_ids)} invoice IDs for payment references")
                print(f"   Matching key_path and destination from invoices")
            
            if invoice_populator.stats['failed'] > 0:
                print(f"⚠️  {invoice_populator.stats['failed']:,} invoices failed to insert.")
                print("Check the failed_invoices_*.json file for details.")
        
        # Populate payments (can reference invoice IDs and details if invoices were created)
        print(f"\nStarting population of {args.count:,} payments...")
        populator.populate_payments(
            count=args.count,
            batch_size=args.batch_size,
            invoice_ids=invoice_ids,
            invoice_details=invoice_details
        )
        
        # Export results
        populator.export_results(args.output_dir)
        
        if populator.stats['successful'] > 0:
            print(f"\n✅ Successfully populated {populator.stats['successful']:,} payments!")
        
        if populator.stats['failed'] > 0:
            print(f"⚠️  {populator.stats['failed']:,} payments failed to insert.")
            print("Check the failed_payments_*.json file for details.")
        
        # Determine overall success
        payments_success = populator.stats['failed'] == 0
        invoices_success = not args.populate_invoices or (invoice_populator and invoice_populator.stats['failed'] == 0)
        
        return 0 if (payments_success and invoices_success) else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Population interrupted by user")
        if args.populate_invoices and invoice_populator:
            invoice_populator.export_results(args.invoice_output_dir)
        populator.export_results(args.output_dir)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
