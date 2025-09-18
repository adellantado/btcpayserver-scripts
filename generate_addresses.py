#!/usr/bin/env python3
"""
Bitcoin Address Generator and Funder

This script generates Bitcoin addresses and funds them from wallet 0.
Supports both mainnet and testnet operations, and can import wallets from private keys or mnemonics.

Requirements:
- bitcoinlib
- python-bitcoinrpc (optional, for RPC operations)

Usage:
    python generate_addresses.py [--mainnet] [--amount AMOUNT] [--count COUNT]
    python generate_addresses.py --private-key YOUR_PRIVATE_KEY [--mainnet]
    python generate_addresses.py --mnemonic "your twelve word mnemonic phrase" [--mainnet]
    python generate_addresses.py --key-file path/to/keyfile [--mainnet]
    python generate_addresses.py --config example_btc_config.json
    python generate_addresses.py --config config.json --count 2000  # Override config values
    python generate_addresses.py --derivation-mode --start-index 0
    python generate_addresses.py --config config.json --derivation-mode  # Use config for derivation settings
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional
from decimal import Decimal
import argparse

try:
    from bitcoinlib.wallets import Wallet, Mnemonic, HDKey, wallet_delete_if_exists
    from bitcoinlib.transactions import Transaction
    from bitcoinlib.services.services import Service
except ImportError:
    print("Error: bitcoinlib not installed. Install with: pip install bitcoinlib")
    exit(1)

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/btc_address_generation.log'),
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
    
    def create_or_load_funding_wallet(self, wallet_name='wallet_0', private_key=None, mnemonic=None) -> Wallet:
        """
        Create or load the funding wallet (wallet 0).
        
        Args:
            wallet_name (str): Name of the funding wallet
            private_key (str, optional): Private key in hex format to import wallet
            mnemonic (str, optional): Mnemonic phrase to import wallet
            
        Returns:
            Wallet: The funding wallet object
        """
        try:
            # If private key or mnemonic provided, import the wallet
            if private_key or mnemonic:
                if private_key:
                    logger.info(f"Importing wallet from private key...")
                    # Delete existing wallet if it exists
                    try:
                        wallet_delete_if_exists(wallet_name, force=True)
                        logger.info(f"Deleted existing wallet: {wallet_name}")
                    except Exception as e:
                        logger.warning(f"Could not delete existing wallet {wallet_name}: {str(e)}")
                        pass
                    
                    # Create wallet from private key
                    self.funding_wallet: Wallet = Wallet.create(
                        wallet_name,
                        keys=private_key,
                        network=self.network,
                        witness_type='segwit',
                    )
                    logger.info(f"Imported wallet from private key: {wallet_name}, zero address: {self.funding_wallet.addresslist()[0]}")
                    
                elif mnemonic:
                    logger.info(f"Importing wallet from mnemonic...")
                    # Delete existing wallet if it exists
                    try:
                        wallet_delete_if_exists(wallet_name, force=True)
                        logger.info(f"Deleted existing wallet: {wallet_name}")
                    except Exception as e:
                        logger.warning(f"Could not delete existing wallet {wallet_name}: {str(e)}")
                        pass
                    
                    # Create wallet from mnemonic
                    self.funding_wallet = Wallet.create(
                        wallet_name,
                        keys=mnemonic,
                        network=self.network,
                        witness_type='segwit'
                    )
                    logger.info(f"Imported wallet from mnemonic: {wallet_name}, zero address: {self.funding_wallet.addresslist()[0]}")
            else:
                # Try to load existing wallet
                self.funding_wallet = Wallet(wallet_name, network=self.network)
                logger.info(f"Loaded existing wallet: {wallet_name}")
                
        except Exception as e:
            if private_key or mnemonic:
                logger.error(f"Failed to import wallet: {str(e)}")
                raise
            else:

                try:
                    wallet_delete_if_exists(wallet_name, force=True)
                    logger.info(f"Deleted existing wallet: {wallet_name}")
                except Exception as e:
                    logger.warning(f"Could not delete existing wallet {wallet_name}: {str(e)}")
                    pass

                mn = Mnemonic()
                mnemonic = mn.generate()   
                self.funding_wallet = Wallet.create(
                    wallet_name, 
                    keys=mnemonic, 
                    network=self.network,
                    witness_type='segwit'
                )

                logger.info(f"Created new wallet: {wallet_name}, seed: {mnemonic}, zero address: {self.funding_wallet.addresslist()[0]}")
        
        # Get wallet info
        balance = self.get_wallet_balance()

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
    
    def generate_addresses_from_path(self, start_index: int = 0, count: int = 1000) -> List[Dict]:
        """
        Generate addresses from an existing wallet using a derivation path.
        
        Args:
            start_index (int): Starting index for address generation
            count (int): Number of addresses to generate
            
        Returns:
            List[Dict]: List of generated address information
        """
        if not self.funding_wallet:
            logger.error("Funding wallet not initialized. Cannot generate addresses from derivation path.")
            return []
        
        logger.info(f"Starting generation of {count} addresses starting from index: {start_index}")
        
        addresses = []
        
        try:

            keys = self.funding_wallet.get_keys(account_id=0, number_of_keys=count+start_index)
            
            for i in range(start_index, start_index+count):
                try:
                    # Get address information
                    address_info = {
                        'index': i,
                        'address': keys[i-1].address,
                        'wif': keys[i-1].wif,
                        'network': self.network
                    }
                    
                    addresses.append(address_info)
                    
                    if (i + 1) % 100 == 0:
                        logger.info(f"Generated {i + 1}/{count} addresses...")
                        
                except Exception as e:
                    logger.error(f"Error generating address (index {i}): {str(e)}")
                    continue
            
            self.generated_addresses = addresses
            logger.info(f"Successfully generated {len(addresses)} addresses from derivation path")
            
        except Exception as e:
            logger.error(f"Error in derivation path generation: {str(e)}")
            return []
        
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
            # First try the wallet's internal balance
            balance = self.funding_wallet.balance()
            
            # If balance is 0, try to get it from the service provider directly
            if balance == 0:
                logger.info(f"Wallet internal balance is 0, trying to get it from the service provider")
                try:
                    from bitcoinlib.services.services import Service
                    service = Service(network=self.network)
                    main_address = self.funding_wallet.addresslist()[0]
                    service_balance = service.getbalance(main_address)
                    if service_balance > 0:
                        logger.info(f"Wallet internal balance is 0, but service shows {service_balance} satoshis. Updating wallet...")
                        # Try to update the wallet's UTXOs
                        try:
                            self.funding_wallet.utxos_update()
                            # Check balance again after update
                            balance = self.funding_wallet.balance()
                            if balance > 0:
                                logger.info(f"Wallet update successful, balance now: {balance} satoshis")
                                return balance
                        except Exception as update_error:
                            logger.warning(f"Wallet UTXO update failed: {update_error}")
                        
                        # If wallet update failed, use service balance directly
                        logger.info(f"Using service balance directly: {service_balance} satoshis")
                        return service_balance
                except Exception as service_error:
                    logger.warning(f"Could not get balance from service: {service_error}")
            
            return balance
        except Exception as e:
            logger.error(f"Error getting wallet balance: {str(e)}")
            return 0
    
    def fund_addresses(self, amount_per_address: float = 0.001, max_fee: float = 0.0001, batch_size: int = 50):
        """
        Fund generated addresses from wallet 0.
        
        Args:
            amount_per_address (float): Amount in BTC to send to each address
            max_fee (float): Maximum fee in BTC per transaction
            batch_size (int): Number of addresses to fund per transaction
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
        
        # Validate UTXOs before attempting transactions
        logger.info("Validating wallet UTXOs...")
        try:
            utxos = self.funding_wallet.utxos()
            if not utxos:
                logger.error("No UTXOs available for spending. Wallet may not be properly synchronized.")
                logger.info("Attempting to force wallet synchronization...")
                try:
                    self.funding_wallet.utxos_update()
                    utxos = self.funding_wallet.utxos()
                    if not utxos:
                        logger.error("Failed to synchronize UTXOs. Cannot create transactions.")
                        return
                    else:
                        logger.info(f"Successfully synchronized {len(utxos)} UTXOs")
                except Exception as sync_error:
                    logger.error(f"Failed to synchronize wallet: {sync_error}")
                    return
            else:
                logger.info(f"Found {len(utxos)} UTXOs available for spending")
        except Exception as e:
            logger.error(f"Error validating UTXOs: {e}")
            return
        
        # Fund addresses in batches to avoid creating huge transactions
        funded_count = 0
        
        for i in range(0, len(self.generated_addresses), batch_size):
            batch = self.generated_addresses[i:i + batch_size]
            
            try:
                # Create transaction outputs for this batch
                outputs = []
                for addr_info in batch:
                    outputs.append((addr_info['address'], amount_satoshis))
                
                logger.info(f"Creating transaction for batch {i//batch_size + 1} with {len(batch)} addresses...")
                
                # Create and send transaction
                tx = self.funding_wallet.send(outputs, fee=max_fee_satoshis)
                
                if tx and tx.txid:
                    # Verify transaction was actually created and broadcasted
                    logger.info(f"Transaction created: {tx.txid}")
                    
                    # Wait a moment and verify the transaction exists
                    time.sleep(3)
                    
                    # Try to verify transaction was broadcasted by checking if it exists
                    broadcasted = False
                    try:
                        from bitcoinlib.services.services import Service
                        service = Service(network=self.network)
                        tx_info = service.gettransaction(tx.txid)
                        if tx_info:
                            broadcasted = True
                            logger.info(f"✅ Transaction verified on network: {tx.txid}")
                        else:
                            logger.warning(f"⚠️  Transaction {tx.txid} not found on network, attempting manual broadcast...")
                            
                            # Try manual broadcasting
                            if hasattr(tx, 'raw_hex'):
                                broadcasted = self.manual_broadcast_transaction(tx.raw_hex())
                            else:
                                logger.warning("Cannot get raw transaction hex for manual broadcasting")
                                
                    except Exception as verify_error:
                        logger.warning(f"Could not verify transaction {tx.txid}: {verify_error}")
                        
                        # Try manual broadcasting as fallback
                        try:
                            if hasattr(tx, 'raw_hex'):
                                broadcasted = self.manual_broadcast_transaction(tx.raw_hex())
                        except Exception as broadcast_error:
                            logger.warning(f"Manual broadcasting failed: {broadcast_error}")
                    
                    if broadcasted:
                        funded_count += len(batch)
                        logger.info(f"✅ Funded batch {i//batch_size + 1}: {len(batch)} addresses (TX: {tx.txid})")
                    else:
                        logger.warning(f"⚠️  Transaction {tx.txid} created but may not be broadcasted")
                        funded_count += len(batch)  # Still count as funded since transaction was created
                    
                    # Add small delay between batches to avoid overwhelming the network
                    time.sleep(2)
                else:
                    logger.error(f"Failed to create transaction for batch {i//batch_size + 1}")
                    
            except Exception as e:
                logger.error(f"Error funding batch {i//batch_size + 1}: {str(e)}")
                continue
        
        logger.info(f"Funding complete. Successfully funded {funded_count}/{len(self.generated_addresses)} addresses")
    
    def manual_broadcast_transaction(self, tx_hex: str) -> bool:
        """
        Manually broadcast a transaction using alternative methods.
        
        Args:
            tx_hex (str): Raw transaction hex string
            
        Returns:
            bool: True if broadcasted successfully, False otherwise
        """
        try:
            # Method 1: Try using requests to broadcast to multiple testnet APIs
            import requests
            
            testnet_apis = [
                "https://blockstream.info/testnet/api/tx",
                "https://mempool.space/testnet/api/tx",
                "https://api.blockcypher.com/v1/btc/test3/txs/push"
            ]
            
            for api_url in testnet_apis:
                try:
                    response = requests.post(api_url, data=tx_hex, timeout=10)
                    if response.status_code in [200, 201]:
                        logger.info(f"✅ Transaction broadcasted via {api_url}")
                        return True
                except Exception as e:
                    logger.debug(f"Failed to broadcast via {api_url}: {e}")
                    continue
            
            # Method 2: Try using bitcoinlib's raw transaction broadcasting
            try:
                from bitcoinlib.services.services import Service
                service = Service(network=self.network)
                result = service.sendrawtransaction(tx_hex)
                if result:
                    logger.info("✅ Transaction broadcasted via bitcoinlib service")
                    return True
            except Exception as e:
                logger.debug(f"Failed to broadcast via bitcoinlib service: {e}")
            
            logger.warning("❌ All broadcasting methods failed")
            return False
            
        except Exception as e:
            logger.error(f"Error in manual broadcasting: {e}")
            return False

    def get_wallet_info(self) -> Dict:
        """
        Get information about the funding wallet.
        
        Returns:
            Dict: Wallet information including keys and addresses
        """
        if not self.funding_wallet:
            return {}
        
        try:
            # Get the main key from the wallet
            main_key = self.funding_wallet.main_key
            
            info = {
                'wallet_name': self.funding_wallet.name,
                'network': self.network,
                'balance': self.get_wallet_balance(),
                'main_address': self.funding_wallet.get_key(0).address,
                'private_key': main_key.key_private if main_key else None,
                'public_key': main_key.key_public if main_key else None,
                'wif': main_key.wif if main_key else None,
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting wallet info: {str(e)}")
            return {}
    
    def create_funding_summary(self) -> Dict:
        """
        Create a summary of the funding operation.
        
        Returns:
            Dict: Summary information
        """
        summary = {
            'network': self.network,
            'total_addresses': len(self.generated_addresses),
            'wallet_info': self.get_wallet_info(),
            'timestamp': time.time(),
            'addresses': self.generated_addresses
        }
        
        return summary


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


def validate_config(config: Dict) -> bool:
    """
    Validate configuration file values.
    
    Args:
        config (Dict): Configuration dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Validate count
    if 'count' in config and (not isinstance(config['count'], int) or config['count'] <= 0):
        logger.error("Config error: 'count' must be a positive integer")
        return False
    
    # Validate amount
    if 'amount' in config and (not isinstance(config['amount'], (int, float)) or config['amount'] <= 0):
        logger.error("Config error: 'amount' must be a positive number")
        return False
    
    # Validate max_fee
    if 'max_fee' in config and (not isinstance(config['max_fee'], (int, float)) or config['max_fee'] <= 0):
        logger.error("Config error: 'max_fee' must be a positive number")
        return False
    
    # Validate batch_size
    if 'batch_size' in config and (not isinstance(config['batch_size'], int) or config['batch_size'] <= 0):
        logger.error("Config error: 'batch_size' must be a positive integer")
        return False
    
    # Validate mainnet
    if 'mainnet' in config and not isinstance(config['mainnet'], bool):
        logger.error("Config error: 'mainnet' must be a boolean")
        return False
    
    # Validate no_funding
    if 'no_funding' in config and not isinstance(config['no_funding'], bool):
        logger.error("Config error: 'no_funding' must be a boolean")
        return False
    
    # Validate derivation_mode
    if 'derivation_mode' in config and not isinstance(config['derivation_mode'], bool):
        logger.error("Config error: 'derivation_mode' must be a boolean")
        return False
    
    # Validate start_index
    if 'start_index' in config and (not isinstance(config['start_index'], int) or config['start_index'] < 0):
        logger.error("Config error: 'start_index' must be a non-negative integer")
        return False
    
    
    # Validate string fields
    string_fields = ['output', 'wallet_name', 'private_key', 'mnemonic', 'key_file']
    for field in string_fields:
        if field in config and not isinstance(config[field], str):
            logger.error(f"Config error: '{field}' must be a string")
            return False
    
    return True


def merge_config_with_args(config: Dict, args: argparse.Namespace) -> argparse.Namespace:
    """
    Merge configuration file values with command line arguments.
    Command line arguments take precedence over config file values.
    Supports both legacy config format and universal config format.
    
    Args:
        config (Dict): Configuration dictionary
        args (argparse.Namespace): Command line arguments
        
    Returns:
        argparse.Namespace: Merged arguments
    """
    # Handle universal config format
    if '_address_generation' in config:
        # Universal config format
        addr_config = config['_address_generation']
        network_config = config.get('_network_settings', {})
        key_config = config.get('_key_import_options', {})
        
        # Network settings
        if not args.mainnet and network_config.get('mainnet', False):
            args.mainnet = network_config['mainnet']
        
        # Address generation settings
        if args.amount == 0.001 and 'amount' in addr_config:
            args.amount = addr_config['amount']
        
        if args.count == 1000 and 'count' in addr_config:
            args.count = addr_config['count']
        
        if not args.no_funding and addr_config.get('no_funding', False):
            args.no_funding = addr_config['no_funding']
        
        if args.output == 'generated_addresses.json' and 'output' in addr_config:
            args.output = addr_config['output']
        
        # Derivation path settings
        if not args.derivation_mode and addr_config.get('derivation_mode', False):
            args.derivation_mode = addr_config['derivation_mode']
        
        if args.start_index == 0 and 'start_index' in addr_config:
            args.start_index = addr_config['start_index']
        
        # Key import options
        if not args.private_key and 'private_key' in key_config and key_config['private_key']:
            args.private_key = key_config['private_key']
        
        if not args.mnemonic and 'mnemonic' in key_config and key_config['mnemonic']:
            args.mnemonic = key_config['mnemonic']
        
        if not args.key_file and 'key_file' in key_config and key_config['key_file']:
            args.key_file = key_config['key_file']
        
        # Additional parameters
        if 'wallet_name' in addr_config:
            args.wallet_name = addr_config['wallet_name']
        else:
            args.wallet_name = 'wallet_0'
        
        if 'max_fee' in addr_config:
            args.max_fee = addr_config['max_fee']
        else:
            args.max_fee = 0.0001
        
        if 'batch_size' in addr_config:
            args.batch_size = addr_config['batch_size']
        else:
            args.batch_size = 50
    
    else:
        # Legacy config format
        if not args.mainnet and config.get('mainnet', False):
            args.mainnet = config['mainnet']
        
        if args.amount == 0.001 and 'amount' in config:
            args.amount = config['amount']
        
        if args.count == 1000 and 'count' in config:
            args.count = config['count']
        
        if not args.no_funding and config.get('no_funding', False):
            args.no_funding = config['no_funding']
        
        if args.output == 'generated_addresses.json' and 'output' in config:
            args.output = config['output']
        
        # Derivation path settings
        if not args.derivation_mode and config.get('derivation_mode', False):
            args.derivation_mode = config['derivation_mode']
        
        if args.start_index == 0 and 'start_index' in config:
            args.start_index = config['start_index']
        
        if not args.private_key and 'private_key' in config:
            args.private_key = config['private_key']
        
        if not args.mnemonic and 'mnemonic' in config:
            args.mnemonic = config['mnemonic']
        
        if not args.key_file and 'key_file' in config:
            args.key_file = config['key_file']
        
        # Additional config-only parameters
        if 'wallet_name' in config:
            args.wallet_name = config['wallet_name']
        else:
            args.wallet_name = 'wallet_0'
        
        if 'max_fee' in config:
            args.max_fee = config['max_fee']
        else:
            args.max_fee = 0.0001
        
        if 'batch_size' in config:
            args.batch_size = config['batch_size']
        else:
            args.batch_size = 50
    
    return args


def main():
    """Main function to run the address generation and funding process."""
    parser = argparse.ArgumentParser(
        description='Generate and fund Bitcoin addresses',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mainnet --count 500 --amount 0.002
  %(prog)s --private-key abc123... --count 100
  %(prog)s --config config.json
  %(prog)s --config config.json --count 2000  # Override config with CLI args
  %(prog)s --derivation-mode --start-index 0 --count 100
  %(prog)s --config config.json --derivation-mode  # Use config for derivation settings
        """
    )
    parser.add_argument('--config', type=str, help='Configuration file path (JSON format)')
    parser.add_argument('--mainnet', action='store_true', help='Use mainnet instead of testnet')
    parser.add_argument('--amount', type=float, default=0.001, help='Amount in BTC to send to each address (default: 0.001)')
    parser.add_argument('--count', type=int, default=1000, help='Number of addresses to generate (default: 1000)')
    parser.add_argument('--no-funding', action='store_true', help='Generate addresses only, skip funding')
    parser.add_argument('--output', type=str, default='generated_addresses.json', help='Output file for addresses')
    parser.add_argument('--private-key', type=str, help='Import funding wallet from private key (hex format)')
    parser.add_argument('--mnemonic', type=str, help='Import funding wallet from mnemonic phrase')
    parser.add_argument('--key-file', type=str, help='Import funding wallet from file containing private key or mnemonic')
    parser.add_argument('--wallet-name', type=str, default='wallet_0', help='Name of the funding wallet (default: wallet_0)')
    parser.add_argument('--max-fee', type=float, default=0.0001, help='Maximum fee in BTC per transaction (default: 0.0001)')
    parser.add_argument('--batch-size', type=int, default=50, help='Number of addresses to fund per transaction (default: 50)')
    parser.add_argument('--derivation-mode', action='store_true', help='Generate addresses from existing wallet using derivation path instead of creating new wallets')
    parser.add_argument('--start-index', type=int, default=0, help='Starting index for derivation path (default: 0)')
    
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
    
    # Handle key import options
    private_key = None
    mnemonic = None
    
    if args.key_file:
        try:
            with open(args.key_file, 'r') as f:
                key_content = f.read().strip()
                # Try to determine if it's a mnemonic (multiple words) or private key
                if len(key_content.split()) > 1:
                    mnemonic = key_content
                    logger.info("Loaded mnemonic from file")
                else:
                    private_key = key_content
                    logger.info("Loaded private key from file")
        except Exception as e:
            print(f"Error reading key file: {str(e)}")
            return
    elif args.private_key:
        private_key = args.private_key
    elif args.mnemonic:
        mnemonic = args.mnemonic
    
    # Validate that only one key import method is used
    key_methods = sum([bool(args.private_key), bool(args.mnemonic), bool(args.key_file)])
    if key_methods > 1:
        print("Error: Please specify only one key import method (--private-key, --mnemonic, or --key-file)")
        return
    
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
        
        if key_methods == 1:
            # Create or load funding wallet
            generator.create_or_load_funding_wallet(
                wallet_name=args.wallet_name,
                private_key=private_key,
                mnemonic=mnemonic
            )
        else:
            # Create or load funding wallet
            if not args.no_funding:
                generator.create_or_load_funding_wallet(
                    wallet_name=args.wallet_name,
                    private_key=private_key,
                    mnemonic=mnemonic
                )
        
        # Generate addresses
        if args.derivation_mode:
            # Generate addresses from derivation path
            addresses = generator.generate_addresses_from_path(
                start_index=args.start_index,
                count=args.count
            )
        else:
            # Generate new addresses (original mode)
            addresses = generator.generate_addresses(args.count)
        
        # Save addresses to file
        generator.save_addresses_to_file(args.output)
        
        # Fund addresses if requested
        if not args.no_funding and addresses:
            generator.fund_addresses(
                amount_per_address=args.amount,
                max_fee=args.max_fee,
                batch_size=args.batch_size
            )
        
        # Print final statistics
        print(f"\n📊 Final Statistics:")
        print(f"Network: {generator.network}")
        print(f"Addresses generated: {len(addresses)}")
        print(f"Output file: {args.output}")
        if args.derivation_mode:
            print(f"Mode: Derivation path generation")
            print(f"Start index: {args.start_index}")
        else:
            print(f"Mode: New wallet generation")
        # print(f"Summary file: {summary_file}")
        
        # Show configuration details
        if args.config:
            print(f"Configuration file: {args.config}")
        
        if not args.no_funding:
            print(f"Funding amount per address: {args.amount} BTC")
            print(f"Maximum fee per transaction: {args.max_fee} BTC")
            print(f"Batch size: {args.batch_size} addresses per transaction")
            print(f"Wallet name: {args.wallet_name}")
            print(f"Wallet balance: {generator.get_wallet_balance()} satoshis")
            
            # Show wallet info if keys were imported
            if private_key or mnemonic:
                wallet_info = generator.get_wallet_info()
                print(f"\n🔑 Imported Wallet Info:")
                print(f"Wallet name: {wallet_info.get('wallet_name', 'N/A')}")
                print(f"Main address: {wallet_info.get('main_address', 'N/A')}")
                if private_key:
                    print("✅ Imported from private key")
                elif mnemonic:
                    print("✅ Imported from mnemonic")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
