#!/usr/bin/env python3
"""
BTCPay Scripts Workflow Runner

This script runs the complete Bitcoin payment testing workflow using the universal config.
It executes all three scripts in sequence: generate_addresses.py, generate_invoices.py, and pay_invoices.py.

Usage:
    python run_workflow.py --config universal_config.json
    python run_workflow.py --config universal_config.json --skip-addresses
    python run_workflow.py --config universal_config.json --skip-invoices
"""

import argparse
import subprocess
import sys
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_config(config_file: str) -> dict:
    """Load configuration from JSON file."""
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


def run_script(script_name: str, config_file: str, extra_args: list = None) -> bool:
    """
    Run a script with the given config file.
    
    Args:
        script_name: Name of the script to run
        config_file: Path to the config file
        extra_args: Additional command line arguments
        
    Returns:
        bool: True if successful, False otherwise
    """
    cmd = [sys.executable, script_name, '--config', config_file]
    if extra_args:
        cmd.extend(extra_args)
    
    logger.info(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"✅ {script_name} completed successfully")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {script_name} failed with exit code {e.returncode}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Error running {script_name}: {str(e)}")
        return False


def check_prerequisites(config: dict) -> bool:
    """Check if prerequisites are met for running the workflow."""
    logger.info("Checking prerequisites...")
    
    # Check if config has required sections
    required_sections = ['_address_generation', '_invoice_generation', '_payment_processing']
    for section in required_sections:
        if section not in config:
            logger.error(f"Missing required config section: {section}")
            return False
    
    # Check if BTCPay credentials are configured
    invoice_config = config['_invoice_generation']
    if invoice_config.get('api_key') == 'your_btcpay_api_key_here':
        logger.warning("⚠️  BTCPay API key not configured in config file")
        return False
    
    if invoice_config.get('store_id') == 'your_store_id_here':
        logger.warning("⚠️  BTCPay store ID not configured in config file")
        return False
    
    if invoice_config.get('base_url') == 'https://your-btcpay-server.com':
        logger.warning("⚠️  BTCPay base URL not configured in config file")
        return False
    
    logger.info("✅ Prerequisites check passed")
    return True


def main():
    """Main function to run the complete workflow."""
    parser = argparse.ArgumentParser(
        description='Run the complete BTCPay scripts workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config universal_config.json
  %(prog)s --config universal_config.json --skip-addresses
  %(prog)s --config universal_config.json --skip-invoices
  %(prog)s --config universal_config.json --dry-run
        """
    )
    
    parser.add_argument('--config', type=str, required=True, 
                       help='Universal configuration file path')
    parser.add_argument('--skip-addresses', action='store_true',
                       help='Skip address generation step')
    parser.add_argument('--skip-invoices', action='store_true',
                       help='Skip invoice generation step')
    parser.add_argument('--skip-payments', action='store_true',
                       help='Skip payment processing step')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be executed without running')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return 1
    
    # Check prerequisites
    if not check_prerequisites(config):
        logger.error("Prerequisites check failed")
        return 1
    
    if args.dry_run:
        logger.info("DRY RUN - Would execute the following steps:")
        if not args.skip_addresses:
            logger.info("1. python generate_addresses.py --config " + args.config)
        if not args.skip_invoices:
            logger.info("2. python generate_invoices.py --config " + args.config)
        if not args.skip_payments:
            logger.info("3. python pay_invoices.py --config " + args.config)
        return 0
    
    # Run workflow steps
    success_count = 0
    total_steps = 0
    
    # Step 1: Generate addresses
    if not args.skip_addresses:
        total_steps += 1
        logger.info("="*60)
        logger.info("STEP 1: Generating Bitcoin addresses")
        logger.info("="*60)
        if run_script('generate_addresses.py', args.config):
            success_count += 1
        else:
            logger.error("Address generation failed. Stopping workflow.")
            return 1
    else:
        logger.info("Skipping address generation")
    
    # Step 2: Generate invoices
    if not args.skip_invoices:
        total_steps += 1
        logger.info("="*60)
        logger.info("STEP 2: Generating BTCPay invoices")
        logger.info("="*60)
        if run_script('generate_invoices.py', args.config):
            success_count += 1
        else:
            logger.error("Invoice generation failed. Stopping workflow.")
            return 1
    else:
        logger.info("Skipping invoice generation")
    
    # Step 3: Pay invoices
    if not args.skip_payments:
        total_steps += 1
        logger.info("="*60)
        logger.info("STEP 3: Paying invoices")
        logger.info("="*60)
        if run_script('pay_invoices.py', args.config):
            success_count += 1
        else:
            logger.error("Payment processing failed.")
            return 1
    else:
        logger.info("Skipping payment processing")
    
    # Summary
    logger.info("="*60)
    logger.info("WORKFLOW SUMMARY")
    logger.info("="*60)
    logger.info(f"Completed steps: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        logger.info("✅ Workflow completed successfully!")
        return 0
    else:
        logger.error("❌ Workflow completed with errors")
        return 1


if __name__ == "__main__":
    exit(main())
