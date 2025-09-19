# Bitcoin Tools & Scripts

A collection of Python scripts for Bitcoin operations including address generation and BTCPay Server invoice management with advanced transaction handling and robust error recovery.

## Scripts Included

### 1. Bitcoin Address Generator (`generate_addresses.py`)
- ✅ Generate 1000+ unique Bitcoin addresses with private keys
- ✅ Support for both mainnet and testnet
- ✅ Automatic funding from a source wallet with UTXO validation
- ✅ Batch transaction processing for efficiency
- ✅ **NEW**: Enhanced wallet balance synchronization
- ✅ **NEW**: Transaction broadcasting verification and fallback
- ✅ **NEW**: Change address handling (sends change back to funding wallet)
- ✅ **NEW**: Manual transaction broadcasting via multiple APIs
- ✅ Comprehensive logging and error handling
- ✅ JSON export of generated addresses
- ✅ Safety checks and balance verification
- ✅ **NEW**: Centralized logging to `logs/` directory

### 2. BTCPay Server Invoice Generator (`generate_invoices.py`)
- ✅ Generate up to 1000+ invoices via BTCPay Server API
- ✅ Async processing for high-performance batch generation
- ✅ Configurable invoice amounts, currencies, and descriptions
- ✅ Rate limiting and error handling
- ✅ Progress tracking with visual progress bars
- ✅ Export results to JSON files
- ✅ Connection testing and validation
- ✅ **NEW**: Universal config format support
- ✅ **NEW**: Centralized logging to `logs/` directory
- ✅ Configuration file support for easy automation

### 3. BTCPay Invoice Payment Processor (`pay_invoices.py`)
- ✅ Pay BTCPay Server invoices using generated Bitcoin addresses
- ✅ **NEW**: Sequential address selection (round-robin)
- ✅ **NEW**: Enhanced transaction creation with change handling
- ✅ **NEW**: UTXO validation and wallet synchronization
- ✅ **NEW**: Transaction broadcasting verification
- ✅ **NEW**: Manual broadcasting fallback mechanisms
- ✅ **NEW**: Funding wallet recreation for address mismatches
- ✅ **NEW**: Support for both `private_key` and `wif` formats
- ✅ Load addresses from `generate_addresses.py` output
- ✅ Load invoices from `generate_invoices.py` output  
- ✅ Support for both mainnet and testnet operations
- ✅ Progress tracking and comprehensive logging
- ✅ Export payment results and statistics
- ✅ **NEW**: Universal config format support
- ✅ **NEW**: Centralized logging to `logs/` directory
- ✅ Configuration file support for easy automation

### 4. BTCPay Server Health Check (`test_btcpay_health.py`)
- ✅ **NEW**: Test BTCPay Server connectivity and API access
- ✅ **NEW**: Validate store configuration and permissions
- ✅ **NEW**: Centralized logging to `logs/` directory

## Quick Start Workflow

The scripts are designed to work together in a complete Bitcoin payment testing workflow:

### Option 1: Universal Config (Recommended)
Use a single configuration file for all scripts:

```bash

# Or run individual steps with the same config
python generate_addresses.py --config universal_config.json
python generate_invoices.py --config universal_config.json
python pay_invoices.py --config universal_config.json
```

### Option 2: Individual Config Files
Use separate configuration files for each script:

```bash
# 1. Generate and fund Bitcoin addresses
python generate_addresses.py --config example_btc_config.json

# 2. Generate BTCPay Server invoices
python generate_invoices.py --config example_invoice_config.json

# 3. Pay invoices using the generated addresses
python pay_invoices.py --config example_payment_config.json
```

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure you have a Bitcoin wallet set up or the script will create one for you.

## Usage

### Bitcoin Address Generator

#### Basic Usage (Testnet - Recommended for testing)
```bash
python generate_addresses.py --testnet
```

#### Mainnet Usage (⚠️ Uses real Bitcoin)
```bash
python generate_addresses.py
```

#### Custom Options
```bash
# Generate 500 addresses with 0.002 BTC each
python generate_addresses.py --count 500 --amount 0.002 --testnet

# Generate addresses only (no funding)
python generate_addresses.py --no-funding --count 1000

# Custom output file
python generate_addresses.py --output my_addresses.json --testnet

# Import wallet from private key
python generate_addresses.py --private-key YOUR_PRIVATE_KEY --testnet

# Import wallet from mnemonic
python generate_addresses.py --mnemonic "your twelve word mnemonic phrase" --testnet
```

#### Command Line Options

- `--testnet`: Use Bitcoin testnet instead of mainnet
- `--amount AMOUNT`: Amount in BTC to send to each address (default: 0.001)
- `--count COUNT`: Number of addresses to generate (default: 1000)
- `--no-funding`: Generate addresses only, skip funding
- `--output FILE`: Output file for addresses (default: generated_addresses.json)
- `--private-key KEY`: Import funding wallet from private key (hex format)
- `--mnemonic PHRASE`: Import funding wallet from mnemonic phrase
- `--key-file FILE`: Import funding wallet from file containing private key or mnemonic
- `--derivation-mode`: Generate addresses from existing wallet using derivation path
- `--start-index INDEX`: Starting index for derivation path (default: 0)

### BTCPay Server Invoice Generator

#### Basic Usage
```bash
python generate_invoices.py --api-key YOUR_API_KEY --store-id YOUR_STORE_ID --count 1000
```

#### Test Connection Only
```bash
python generate_invoices.py --api-key YOUR_API_KEY --store-id YOUR_STORE_ID --test-only
```

#### Custom Configuration
```bash
# Generate 500 invoices with custom batch size and rate limiting
python generate_invoices.py \
  --api-key YOUR_API_KEY \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --count 500 \
  --batch-size 25 \
  --delay 0.5

# Custom output directory
python generate_invoices.py \
  --api-key YOUR_API_KEY \
  --store-id YOUR_STORE_ID \
  --count 1000 \
  --output-dir my_invoice_results
```

#### BTCPay Server Setup Requirements

1. **API Key**: Generate an API key in your BTCPay Server admin panel
   - Go to Account → Manage Account → API Keys
   - Create new API key with `btcpay.store.canmodifyinvoices` permission

2. **Store ID**: Find your store ID in the BTCPay Server dashboard
   - Go to Stores → [Your Store] 
   - Copy the Store ID from the URL or store settings

3. **Base URL**: Your BTCPay Server instance URL (e.g., `https://btcpay.example.com`)

#### Command Line Options (Invoice Generator)

- `--api-key`: BTCPay Server API key (required)
- `--store-id`: BTCPay Server store ID (required)
- `--base-url`: BTCPay Server base URL (default: https://btcpay.example.com)
- `--count`: Number of invoices to generate (default: 1000)
- `--batch-size`: Concurrent requests per batch (default: 50)
- `--delay`: Delay between batches in seconds (default: 0.1)
- `--output-dir`: Output directory for results (default: invoice_results)
- `--test-only`: Test connection without generating invoices

### BTCPay Invoice Payment Processor

#### Basic Usage (Testnet - Recommended for testing)
```bash
python pay_invoices.py --addresses generated_addresses.json --invoices successful_invoices.json --store-id YOUR_STORE_ID --base-url https://your-btcpay-server.com --api-key YOUR_API_KEY
```

#### Configuration File Usage
```bash
python pay_invoices.py --config example_payment_config.json
```

#### Advanced Options
```bash
# Pay only first 10 invoices with 2 second delays
python pay_invoices.py \
  --addresses generated_addresses.json \
  --invoices successful_invoices.json \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --api-key YOUR_API_KEY \
  --max-invoices 10 \
  --delay 2.0

# Test file loading without making payments
python pay_invoices.py \
  --addresses generated_addresses.json \
  --invoices successful_invoices.json \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --api-key YOUR_API_KEY \
  --test-only
```

#### Mainnet Usage (⚠️ Uses real Bitcoin)
```bash
python pay_invoices.py \
  --addresses generated_addresses.json \
  --invoices successful_invoices.json \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --api-key YOUR_API_KEY \
  --mainnet
```

#### Payment Script Options
- `--config FILE`: Configuration file path (JSON format)
- `--addresses FILE`: Generated addresses JSON file (required)
- `--invoices FILE`: Generated invoices JSON file (required)
- `--store-id ID`: BTCPay Server store ID (required)
- `--base-url URL`: BTCPay Server base URL (required)
- `--api-key KEY`: BTCPay Server API key (required)
- `--mainnet`: Use mainnet instead of testnet
- `--delay SECONDS`: Delay between payments (default: 1.0)
- `--max-invoices COUNT`: Maximum number of invoices to pay
- `--output-dir DIR`: Output directory for results (default: payment_results)
- `--test-only`: Test file loading without making payments

### BTCPay Server Health Check

#### Basic Usage
```bash
python test_btcpay_health.py --api-key YOUR_API_KEY --store-id YOUR_STORE_ID --base-url https://your-btcpay-server.com
```

#### Health Check Options
- `--api-key`: BTCPay Server API key (required)
- `--store-id`: BTCPay Server store ID (required)
- `--base-url`: BTCPay Server base URL (required)

## ⚠️ Important Security Notes

1. **Mainnet Warning**: The script operates on real Bitcoin when not using `--testnet`. Double-check before running on mainnet.

2. **Private Key Storage**: Generated private keys are stored in plain text in the output JSON file. Secure this file appropriately.

3. **Wallet Security**: The funding wallet (wallet_0) will be created automatically if it doesn't exist. Back up your wallet data.

4. **Network Fees**: The script includes network fee calculations, but fees can vary based on network congestion.

5. **Change Handling**: All transactions now properly handle change by sending it back to the funding wallet.

## Complete Workflow Example

Here's how to use all three scripts together for a complete invoice payment workflow:

### Step 1: Test BTCPay Server Connection
```bash
# Test BTCPay Server connectivity
python test_btcpay_health.py \
  --api-key YOUR_API_KEY \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com
```

### Step 2: Generate Bitcoin Addresses
```bash
# Generate 100 addresses on testnet
python generate_addresses.py --count 100 --testnet --output my_addresses.json
```

### Step 3: Generate BTCPay Invoices  
```bash
# Generate 50 invoices
python generate_invoices.py \
  --api-key YOUR_API_KEY \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --count 50 \
  --output-dir my_invoices
```

### Step 4: Pay the Invoices
```bash
# Pay all invoices using generated addresses
python pay_invoices.py \
  --addresses my_addresses.json \
  --invoices my_invoices/successful_invoices_*.json \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --api-key YOUR_API_KEY \
  --output-dir my_payments
```

### Using Configuration Files
```bash
# 1. Test BTCPay Server health
python test_btcpay_health.py --config universal_config.json

# 2. Generate addresses with config
python generate_addresses.py --config universal_config.json

# 3. Generate invoices with config  
python generate_invoices.py --config universal_config.json

# 4. Pay invoices with config
python pay_invoices.py --config universal_config.json
```

## Output Files

### Address Generator
- `generated_addresses.json`: Contains all generated addresses with private keys
- `summary_[timestamp].json`: Summary of the operation
- `logs/btc_address_generation.log`: Detailed log file

### Invoice Generator
- `successful_invoices_[timestamp].json`: Successfully created invoices
- `failed_invoices_[timestamp].json`: Failed invoice attempts
- `generation_summary_[timestamp].json`: Generation statistics
- `logs/invoice_generation.log`: Detailed log file

### Payment Processor
- `successful_payments_[timestamp].json`: Successfully paid invoices
- `failed_payments_[timestamp].json`: Failed payment attempts  
- `payment_summary_[timestamp].json`: Payment statistics
- `logs/invoice_payment.log`: Detailed log file

### Health Check
- `logs/btcpay_health_check.log`: Detailed log file

## Logging System

All scripts now use a centralized logging system:

- **Log Directory**: All logs are stored in the `logs/` directory
- **Automatic Creation**: The logs directory is created automatically if it doesn't exist
- **Individual Log Files**: Each script has its own dedicated log file
- **Comprehensive Logging**: Detailed logging for debugging and monitoring
- **Log Levels**: INFO, WARNING, ERROR levels for different types of messages

## Example Output Structure

```json
{
  "index": 1,
  "address": "tb1qmh59yrkx06deul6zyqj4l224ryhr5z5p7sxqyr",
  "private_key": "a70134b68ac598d06725580f812fd25957fcb166e9230d868b416dd1686e3683",
  "public_key": "02f12345...",
  "wif": "vprv9NqMRPAQib6kPSw5kKjUv3dn8uDrZRvbwos9mXv33Z2sG9DWLbRTXkJQYBxUB5bjELX663zFvAwVmfDoLXtfYgooxDVcaAr8HmLHS9mRhcu",
  "network": "testnet"
}
```

## Recent Improvements

### Enhanced Transaction Handling
- **UTXO Validation**: Pre-transaction UTXO validation and synchronization
- **Transaction Verification**: Post-transaction verification on the network
- **Manual Broadcasting**: Fallback broadcasting via multiple APIs
- **Change Handling**: Proper change address management

### Improved Error Recovery
- **Address Mismatch Handling**: Automatic funding wallet recreation
- **Balance Synchronization**: Enhanced wallet balance retrieval
- **Sequential Address Usage**: Round-robin address selection
- **Format Flexibility**: Support for both `private_key` and `wif` formats

### Better Configuration Management
- **Universal Config**: Single configuration file for all scripts
- **Legacy Support**: Backward compatibility with individual config files
- **Validation**: Comprehensive configuration validation

### Centralized Logging
- **Organized Logs**: All logs in dedicated `logs/` directory
- **Detailed Tracking**: Comprehensive operation logging
- **Easy Debugging**: Clear error messages and status updates

## Troubleshooting

### Common Issues

1. **Insufficient Balance**: Make sure wallet_0 has enough Bitcoin to fund all addresses
2. **Network Connection**: Ensure you have a stable internet connection
3. **Dependencies**: Install all required packages with `pip install -r requirements.txt`
4. **Address Mismatch**: The system will automatically recreate the funding wallet if needed
5. **Transaction Broadcasting**: Multiple fallback methods ensure transactions are broadcasted

### Logs

Check the appropriate log file in the `logs/` directory for detailed error messages and operation logs:
- `logs/btc_address_generation.log` - Address generation operations
- `logs/invoice_generation.log` - Invoice generation operations  
- `logs/invoice_payment.log` - Payment processing operations
- `logs/btcpay_health_check.log` - BTCPay Server health checks

## License

This script is provided as-is for educational and development purposes. Use at your own risk.
