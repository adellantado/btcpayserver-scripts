#!/usr/bin/env python3
"""
Bitcoin Address Generator and Funder

This script generates 1000 Bitcoin addresses and funds them from wallet 0.
Supports both mainnet and testnet operations.

Requirements:
- bitcoinlib
- python-bitcoinrpc (optional, for RPC operations)

Usage:
    python generate-addresses.py [--testnet] [--amount AMOUNT] [--rpc-url URL]
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional
from decimal import Decimal
import argparse

try:
    from bitcoinlib.wallets import Wallet
    from bitcoinlib.keys import HDKey
    from bitcoinlib.transactions import Transaction
    from bitcoinlib.services.services import Service
except ImportError:
    print("Error: bitcoinlib not installed. Install with: pip install bitcoinlib")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('btc_address_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BTCAddressGenerator:
    """Bitcoin address generator and funding utility."""
    
    def __init__(self, network='bitcoin', testnet=True):
        """
        Initialize the BTC address generator.
        
        Args:
            network (str): Network type ('bitcoin' for mainnet, 'testnet' for testnet)
            testnet (bool): Whether to use testnet
        """
        self.network = 'testnet' if testnet else 'bitcoin'
        self.testnet = testnet
        self.generated_addresses = []
        self.funding_wallet = None
        
        logger.info(f"Initialized BTCAddressGenerator for {self.network}")
    
    def create_or_load_funding_wallet(self, wallet_name='wallet_0') -> Wallet:
        """
        Create or load the funding wallet (wallet 0).
        
        Args:
            wallet_name (str): Name of the funding wallet
            
        Returns:
            Wallet: The funding wallet object
        """
        try:
            # Try to load existing wallet
            self.funding_wallet = Wallet(wallet_name, network=self.network)
            logger.info(f"Loaded existing wallet: {wallet_name}")
        except Exception:
            # Create new wallet if it doesn't exist
            self.funding_wallet = Wallet.create(
                wallet_name,
                network=self.network,
                witness_type='segwit'
            )
            logger.info(f"Created new wallet: {wallet_name}")
        
        # Get wallet info
        balance = self.funding_wallet.balance()
        logger.info(f"Wallet balance: {balance} satoshis")
        
        return self.funding_wallet
    
    def generate_addresses(self, count: int = 1000) -> List[Dict]:
        """
        Generate the specified number of Bitcoin addresses.
        
        Args:
            count (int): Number of addresses to generate
            
        Returns:
            List[Dict]: List of generated address information
        """
        logger.info(f"Starting generation of {count} Bitcoin addresses...")
        
        addresses = []
        
        for i in range(count):
            try:
                # Generate a new HD key
                key = HDKey(network=self.network)
                
                # Get address information
                address_info = {
                    'index': i + 1,
                    'address': key.address(),
                    'private_key': key.private_hex,
                    'public_key': key.public_hex,
                    'wif': key.wif(),
                    'network': self.network
                }
                
                addresses.append(address_info)
                
                if (i + 1) % 100 == 0:
                    logger.info(f"Generated {i + 1}/{count} addresses...")
                    
            except Exception as e:
                logger.error(f"Error generating address {i + 1}: {str(e)}")
                continue
        
        self.generated_addresses = addresses
        logger.info(f"Successfully generated {len(addresses)} addresses")
        
        return addresses
    
    def save_addresses_to_file(self, filename: str = 'generated_addresses.json'):
        """
        Save generated addresses to a JSON file.
        
        Args:
            filename (str): Output filename
        """
        if not self.generated_addresses:
            logger.warning("No addresses to save")
            return
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.generated_addresses, f, indent=2)
            
            logger.info(f"Saved {len(self.generated_addresses)} addresses to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving addresses to file: {str(e)}")
    
    def get_wallet_balance(self) -> int:
        """
        Get the current balance of the funding wallet.
        
        Returns:
            int: Balance in satoshis
        """
        if not self.funding_wallet:
            return 0
        
        try:
            return self.funding_wallet.balance()
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return 0
    
    def fund_addresses(self, amount_per_address: float = 0.001, max_fee: float = 0.0001):
        """
        Fund generated addresses from wallet 0.
        
        Args:
            amount_per_address (float): Amount in BTC to send to each address
            max_fee (float): Maximum fee in BTC per transaction
        """
        if not self.funding_wallet:
            logger.error("Funding wallet not initialized")
            return
        
        if not self.generated_addresses:
            logger.error("No addresses to fund")
            return
        
        logger.info(f"Starting funding process for {len(self.generated_addresses)} addresses...")
        logger.info(f"Amount per address: {amount_per_address} BTC")
        
        # Convert BTC to satoshis
        amount_satoshis = int(amount_per_address * 100_000_000)
        max_fee_satoshis = int(max_fee * 100_000_000)
        
        # Check if wallet has sufficient balance
        total_needed = (amount_satoshis + max_fee_satoshis) * len(self.generated_addresses)
        current_balance = self.get_wallet_balance()
        
        if current_balance < total_needed:
            logger.error(f"Insufficient balance. Need: {total_needed} satoshis, Have: {current_balance} satoshis")
            return
        
        # Fund addresses in batches to avoid creating huge transactions
        batch_size = 50  # Adjust based on network limits
        funded_count = 0
        
        for i in range(0, len(self.generated_addresses), batch_size):
            batch = self.generated_addresses[i:i + batch_size]
            
            try:
                # Create transaction outputs for this batch
                outputs = []
                for addr_info in batch:
                    outputs.append((addr_info['address'], amount_satoshis))
                
                # Create and send transaction
                tx = self.funding_wallet.send(outputs, fee=max_fee_satoshis)
                
                if tx:
                    funded_count += len(batch)
                    logger.info(f"Funded batch {i//batch_size + 1}: {len(batch)} addresses (TX: {tx.txid})")
                    
                    # Add small delay between batches to avoid overwhelming the network
                    time.sleep(2)
                else:
                    logger.error(f"Failed to send transaction for batch {i//batch_size + 1}")
                    
            except Exception as e:
                logger.error(f"Error funding batch {i//batch_size + 1}: {str(e)}")
                continue
        
        logger.info(f"Funding complete. Successfully funded {funded_count}/{len(self.generated_addresses)} addresses")
    
    def create_funding_summary(self) -> Dict:
        """
        Create a summary of the funding operation.
        
        Returns:
            Dict: Summary information
        """
        summary = {
            'network': self.network,
            'total_addresses': len(self.generated_addresses),
            'wallet_balance': self.get_wallet_balance(),
            'timestamp': time.time(),
            'addresses': self.generated_addresses
        }
        
        return summary


def main():
    """Main function to run the address generation and funding process."""
    parser = argparse.ArgumentParser(description='Generate and fund Bitcoin addresses')
    parser.add_argument('--mainnet', action='store_true', help='Use mainnet instead of testnet')
    parser.add_argument('--amount', type=float, default=0.001, help='Amount in BTC to send to each address (default: 0.001)')
    parser.add_argument('--count', type=int, default=1000, help='Number of addresses to generate (default: 1000)')
    parser.add_argument('--no-funding', action='store_true', help='Generate addresses only, skip funding')
    parser.add_argument('--output', type=str, default='generated_addresses.json', help='Output file for addresses')
    
    args = parser.parse_args()
    
    # Warning for mainnet usage
    if args.mainnet:
        print("\n⚠️  WARNING: You are about to operate on Bitcoin MAINNET!")
        print("This will use real Bitcoin. Make sure this is intended.")
        response = input("Continue? (yes/no): ").lower().strip()
        if response != 'yes':
            print("Operation cancelled.")
            return
    
    try:
        # Initialize generator
        generator = BTCAddressGenerator(testnet=not args.mainnet)
        
        # Create or load funding wallet
        if not args.no_funding:
            generator.create_or_load_funding_wallet()
        
        # Generate addresses
        addresses = generator.generate_addresses(args.count)
        
        # Save addresses to file
        generator.save_addresses_to_file(args.output)
        
        # Fund addresses if requested
        if not args.no_funding and addresses:
            generator.fund_addresses(amount_per_address=args.amount)
        
        # Create and save summary
        summary = generator.create_funding_summary()
        summary_file = f"summary_{int(time.time())}.json"
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Operation complete. Summary saved to {summary_file}")
        
        # Print final statistics
        print(f"\n📊 Final Statistics:")
        print(f"Network: {generator.network}")
        print(f"Addresses generated: {len(addresses)}")
        print(f"Output file: {args.output}")
        print(f"Summary file: {summary_file}")
        
        if not args.no_funding:
            print(f"Funding amount per address: {args.amount} BTC")
            print(f"Wallet balance: {generator.get_wallet_balance()} satoshis")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
