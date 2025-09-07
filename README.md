# Bitcoin Tools & Scripts

A collection of Python scripts for Bitcoin operations including address generation and BTCPay Server invoice management.

## Scripts Included

### 1. Bitcoin Address Generator (`generate-addresses.py`)
- ✅ Generate 1000 unique Bitcoin addresses with private keys
- ✅ Support for both mainnet and testnet
- ✅ Automatic funding from a source wallet
- ✅ Batch transaction processing for efficiency
- ✅ Comprehensive logging and error handling
- ✅ JSON export of generated addresses
- ✅ Safety checks and balance verification

### 2. BTCPay Server Invoice Generator (`generate_invoices.py`)
- ✅ Generate up to 1000+ invoices via BTCPay Server API
- ✅ Async processing for high-performance batch generation
- ✅ Configurable invoice amounts, currencies, and descriptions
- ✅ Rate limiting and error handling
- ✅ Progress tracking with visual progress bars
- ✅ Export results to JSON files
- ✅ Connection testing and validation

### 3. BTCPay Invoice Payment Processor (`pay_invoices.py`)
- ✅ Pay BTCPay Server invoices using generated Bitcoin addresses
- ✅ Automatic Bitcoin transaction creation and broadcasting
- ✅ Load addresses from `generate-addresses.py` output
- ✅ Load invoices from `generate_invoices.py` output  
- ✅ Support for both mainnet and testnet operations
- ✅ Progress tracking and comprehensive logging
- ✅ Export payment results and statistics
- ✅ Configuration file support for easy automation

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
python generate-addresses.py --testnet
```

#### Mainnet Usage (⚠️ Uses real Bitcoin)
```bash
python generate-addresses.py
```

#### Custom Options
```bash
# Generate 500 addresses with 0.002 BTC each
python generate-addresses.py --count 500 --amount 0.002 --testnet

# Generate addresses only (no funding)
python generate-addresses.py --no-funding --count 1000

# Custom output file
python generate-addresses.py --output my_addresses.json --testnet
```

#### Command Line Options

- `--testnet`: Use Bitcoin testnet instead of mainnet
- `--amount AMOUNT`: Amount in BTC to send to each address (default: 0.001)
- `--count COUNT`: Number of addresses to generate (default: 1000)
- `--no-funding`: Generate addresses only, skip funding
- `--output FILE`: Output file for addresses (default: generated_addresses.json)

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
python pay_invoices.py --addresses generated_addresses.json --invoices successful_invoices.json
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
  --max-invoices 10 \
  --delay 2.0

# Test file loading without making payments
python pay_invoices.py \
  --addresses generated_addresses.json \
  --invoices successful_invoices.json \
  --test-only
```

#### Mainnet Usage (⚠️ Uses real Bitcoin)
```bash
python pay_invoices.py \
  --addresses generated_addresses.json \
  --invoices successful_invoices.json \
  --mainnet
```

#### Payment Script Options
- `--config FILE`: Configuration file path (JSON format)
- `--addresses FILE`: Generated addresses JSON file (required)
- `--invoices FILE`: Generated invoices JSON file (required)
- `--mainnet`: Use mainnet instead of testnet
- `--delay SECONDS`: Delay between payments (default: 1.0)
- `--max-invoices COUNT`: Maximum number of invoices to pay
- `--output-dir DIR`: Output directory for results (default: payment_results)
- `--test-only`: Test file loading without making payments

## ⚠️ Important Security Notes

1. **Mainnet Warning**: The script operates on real Bitcoin when not using `--testnet`. Double-check before running on mainnet.

2. **Private Key Storage**: Generated private keys are stored in plain text in the output JSON file. Secure this file appropriately.

3. **Wallet Security**: The funding wallet (wallet_0) will be created automatically if it doesn't exist. Back up your wallet data.

4. **Network Fees**: The script includes network fee calculations, but fees can vary based on network congestion.

## Complete Workflow Example

Here's how to use all three scripts together for a complete invoice payment workflow:

### Step 1: Generate Bitcoin Addresses
```bash
# Generate 100 addresses on testnet
python generate-addresses.py --count 100 --testnet --output my_addresses.json
```

### Step 2: Generate BTCPay Invoices  
```bash
# Generate 50 invoices
python generate_invoices.py \
  --api-key YOUR_API_KEY \
  --store-id YOUR_STORE_ID \
  --base-url https://your-btcpay-server.com \
  --count 50 \
  --output-dir my_invoices
```

### Step 3: Pay the Invoices
```bash
# Pay all invoices using generated addresses
python pay_invoices.py \
  --addresses my_addresses.json \
  --invoices my_invoices/successful_invoices_*.json \
  --output-dir my_payments
```

### Using Configuration Files
```bash
# 1. Generate addresses with config
python generate-addresses.py --config btc_config.json

# 2. Generate invoices with config  
python generate_invoices.py --config invoice_config.json

# 3. Pay invoices with config
python pay_invoices.py --config payment_config.json
```

## Output Files

### Address Generator
- `generated_addresses.json`: Contains all generated addresses with private keys
- `summary_[timestamp].json`: Summary of the operation
- `btc_address_generation.log`: Detailed log file

### Invoice Generator
- `successful_invoices_[timestamp].json`: Successfully created invoices
- `failed_invoices_[timestamp].json`: Failed invoice attempts
- `generation_summary_[timestamp].json`: Generation statistics
- `invoice_generation.log`: Detailed log file

### Payment Processor
- `successful_payments_[timestamp].json`: Successfully paid invoices
- `failed_payments_[timestamp].json`: Failed payment attempts  
- `payment_summary_[timestamp].json`: Payment statistics
- `invoice_payment.log`: Detailed log file

## Example Output Structure

```json
{
  "index": 1,
  "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
  "private_key": "L4rK1yDtCWekvXuE6oXD9jCYfFNV2cWRpVuPLBcCU2z8TrisoyY1",
  "public_key": "02f12345...",
  "wif": "L4rK1yDtCWekvXuE6oXD9jCYfFNV2cWRpVuPLBcCU2z8TrisoyY1",
  "network": "bitcoin"
}
```

## Troubleshooting

### Common Issues

1. **Insufficient Balance**: Make sure wallet_0 has enough Bitcoin to fund all addresses
2. **Network Connection**: Ensure you have a stable internet connection
3. **Dependencies**: Install all required packages with `pip install -r requirements.txt`

### Logs

Check `btc_address_generation.log` for detailed error messages and operation logs.

## License

This script is provided as-is for educational and development purposes. Use at your own risk.

