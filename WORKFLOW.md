# BTCPay Scripts Workflow

This document explains how the three scripts work together to create a complete Bitcoin payment testing workflow.

## Scripts Overview

1. **`generate_addresses.py`** - Generates Bitcoin addresses and funds them
2. **`generate_invoices.py`** - Creates BTCPay Server invoices
3. **`pay_invoices.py`** - Pays invoices using the generated addresses

## Universal Configuration

The easiest way to run the complete workflow is using the universal configuration file:

### Quick Start with Universal Config

```bash
# Run complete workflow with one command
python run_workflow.py --config universal_config.json

# Or run individual steps with the same config
python generate_addresses.py --config universal_config.json
python generate_invoices.py --config universal_config.json
python pay_invoices.py --config universal_config.json
```

The `universal_config.json` file contains all settings for all three scripts in one place, making it easy to manage the entire workflow with consistent settings.

## Workflow Steps

### Step 1: Generate Bitcoin Addresses

Generate Bitcoin addresses and fund them with test Bitcoin:

```bash
# Using config file (recommended)
python generate_addresses.py --config example_btc_config.json

# Or with command line arguments
python generate_addresses.py --mainnet false --count 1000 --amount 0.001
```

**Output**: `generated_addresses.json` - Contains Bitcoin addresses with private keys

### Step 2: Generate BTCPay Invoices

Create invoices on your BTCPay Server:

```bash
# Using config file (recommended)
python generate_invoices.py --config example_invoice_config.json

# Or with command line arguments
python generate_invoices.py --api-key YOUR_API_KEY --store-id YOUR_STORE_ID --count 1000
```

**Output**: `invoice_results/successful_invoices_YYYYMMDD_HHMMSS.json` - Contains generated invoices

### Step 3: Pay Invoices

Pay the generated invoices using the Bitcoin addresses:

```bash
# Using config file (recommended)
python pay_invoices.py --config example_payment_config.json

# Or with command line arguments
python pay_invoices.py --addresses generated_addresses.json --invoices "invoice_results/successful_invoices_*.json"
```

**Output**: `payment_results/` - Contains payment results and statistics

## Configuration Files

### `example_btc_config.json`
- Configures Bitcoin address generation
- Sets network (mainnet/testnet)
- Defines funding amounts and batch sizes

### `example_invoice_config.json`
- Configures BTCPay Server connection
- Sets invoice generation parameters
- Defines batch processing settings

### `example_payment_config.json`
- Links address and invoice files
- Configures payment processing
- Sets network and timing parameters

## File Dependencies

```
generate_addresses.py → generated_addresses.json
generate_invoices.py → invoice_results/successful_invoices_*.json
pay_invoices.py ← generated_addresses.json + invoice_results/successful_invoices_*.json
```

## Network Configuration

All scripts default to **testnet** for safety. To use mainnet:

1. Set `"mainnet": true` in all config files
2. Ensure you have real Bitcoin in your funding wallet
3. Be aware that mainnet operations use real money

## Safety Features

- **Testnet by default**: All scripts default to testnet
- **Confirmation prompts**: Mainnet operations require explicit confirmation
- **Comprehensive logging**: All operations are logged
- **Error handling**: Robust error handling and recovery
- **Progress tracking**: Real-time progress indicators

## Example Complete Workflow

```bash
# 1. Generate and fund addresses
python generate_addresses.py --config example_btc_config.json

# 2. Generate invoices
python generate_invoices.py --config example_invoice_config.json

# 3. Pay invoices
python pay_invoices.py --config example_payment_config.json
```

## Troubleshooting

### Common Issues

1. **"No files found matching pattern"**: Ensure invoice generation completed successfully
2. **"Insufficient balance"**: Check that addresses were funded properly
3. **"Connection test failed"**: Verify BTCPay Server credentials and URL
4. **"Invalid JSON"**: Check that previous steps completed without errors

### Log Files

- `btc_address_generation.log` - Address generation logs
- `invoice_generation.log` - Invoice generation logs  
- `invoice_payment.log` - Payment processing logs

## Configuration Validation

All scripts validate their configuration files and provide helpful error messages for:
- Missing required fields
- Invalid data types
- File path issues
- Network configuration problems
