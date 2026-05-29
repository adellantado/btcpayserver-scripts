#!/usr/bin/env python3
"""
Populate InvoiceSearches from an invoices CSV export.

Reads invoice rows from a CSV file (same format used for the Invoices table)
and inserts matching search records into InvoiceSearches, using the same
value derivation as populate_tables.py.

Table "InvoiceSearches":
- Id: integer
- InvoiceDataId: text
- Value: text

Usage:
    python populate_invoicesearches.py --config universal_config.json \\
        --csv data/invoices_updated_server3-4.csv

    python populate_invoicesearches.py --host localhost --database testdb \\
        --user postgres --password secret --csv data/invoices.csv

    python populate_invoicesearches.py --config universal_config.json \\
        --csv data/invoices.csv --store YOUR_STORE_ID

    python populate_invoicesearches.py --config universal_config.json \\
        --csv data/invoices.csv --blob2-only
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 is required for database connectivity.")
    print("Install it with: pip install psycopg2-binary")
    exit(1)

from tqdm import tqdm

from populate_tables import (
    InvoicesTablePopulator,
    load_config,
    merge_config_with_args,
    validate_config,
)


def parse_created(value: str) -> datetime:
    """Parse Created column from invoice CSV (e.g. 2025-11-03 19:11:23.000+0000)."""
    value = value.strip()
    if not value:
        raise ValueError("empty Created value")

    # Normalize timezone offset: +0000 -> +00:00, -0400 -> -04:00
    if len(value) >= 5 and value[-5] in "+-" and value[-4:].isdigit():
        value = value[:-5] + value[-5:-2] + ":" + value[-2:]

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S%z",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"unrecognized Created datetime: {value!r}")


def csv_row_to_invoice(row: Dict[str, str]) -> Dict:
    """Convert a CSV row to an invoice dict for search value building."""
    created = parse_created(row["Created"])

    archived_raw = (row.get("Archived") or "").strip()
    archived = archived_raw in ("1", "true", "True", "TRUE")

    blob_raw = row.get("Blob") or ""
    blob = blob_raw.encode("utf-8") if blob_raw else b""

    amount_raw = row.get("Amount") or "0"
    amount = float(amount_raw) if "." in amount_raw else int(amount_raw)

    return {
        "Id": row["Id"],
        "Blob": blob,
        "Created": created,
        "ExceptionStatus": row.get("ExceptionStatus") or "",
        "Status": row.get("Status") or "",
        "StoreDataId": row.get("StoreDataId") or "",
        "Archived": archived,
        "Blob2": row["Blob2"],
        "Amount": amount,
        "Currency": row.get("Currency") or "",
    }


def read_invoices_from_csv(
    csv_path: Path, store_id: Optional[str] = None
) -> List[Dict]:
    """Read invoice records from CSV file.

    Args:
        csv_path: Path to invoices CSV.
        store_id: If set, replaces StoreDataId from each CSV row.
    """
    invoices = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header: {csv_path}")

        required = {
            "Id", "Created", "Blob2", "Amount",
        }
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"CSV missing required columns {sorted(missing)}: {csv_path}"
            )

        for line_no, row in enumerate(reader, start=2):
            if not any((v or "").strip() for v in row.values()):
                continue
            try:
                invoice = csv_row_to_invoice(row)
                if store_id is not None:
                    invoice["StoreDataId"] = store_id
                invoices.append(invoice)
            except Exception as e:
                raise ValueError(
                    f"Failed to parse CSV line {line_no} in {csv_path}: {e}"
                ) from e

    return invoices


class InvoiceSearchesPopulator(InvoicesTablePopulator):
    """Populate InvoiceSearches from existing invoice CSV data."""

    def __init__(self, db_config: Dict, blob2_only: bool = False):
        super().__init__(db_config)
        self.blob2_only = blob2_only
        self.search_stats = {
            "invoices_processed": 0,
            "invoices_failed": 0,
            "search_rows_inserted": 0,
            "start_time": None,
            "end_time": None,
        }

    def _build_invoice_search_values_blob2_only(self, invoice: Dict) -> List[str]:
        """Build search values sourced only from the invoice Blob2 JSON."""
        values = []
        try:
            blob2_json = json.loads(invoice["Blob2"])
        except (json.JSONDecodeError, KeyError, TypeError):
            self.logger.warning(
                f"Invoice {invoice.get('Id', 'unknown')} has invalid Blob2 JSON"
            )
            return values

        prompts = blob2_json.get("prompts", {})
        btc_chain = prompts.get("BTC-CHAIN", {})
        destination = btc_chain.get("destination")
        if destination:
            values.append(destination)

        metadata = blob2_json.get("metadata")
        if isinstance(metadata, dict):
            for meta_value in metadata.values():
                if isinstance(meta_value, (dict, list)):
                    continue
                if meta_value is not None and str(meta_value) != "":
                    values.append(str(meta_value))

        for field in ("notificationURL", "notificationEmail"):
            field_value = blob2_json.get(field)
            if field_value is not None and str(field_value) != "":
                values.append(str(field_value))

        return values

    def _get_search_values(self, invoice: Dict) -> List[str]:
        if self.blob2_only:
            return self._build_invoice_search_values_blob2_only(invoice)
        return self._build_invoice_search_values(invoice)

    def insert_invoice_searches_batch(self, invoices: List[Dict]) -> Tuple[int, int]:
        """Insert InvoiceSearches rows for a batch of invoices.

        Returns:
            Tuple of (successful_invoices, failed_invoices)
        """
        successful = 0
        failed = 0

        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()

            for invoice in invoices:
                try:
                    search_values = self._get_search_values(invoice)
                    for search_value in search_values:
                        cursor.execute(
                            """
                            INSERT INTO "InvoiceSearches" (
                                "InvoiceDataId", "Value"
                            ) VALUES (
                                %(InvoiceDataId)s, %(Value)s
                            )
                            """,
                            {
                                "InvoiceDataId": invoice["Id"],
                                "Value": search_value,
                            },
                        )
                        self.search_stats["search_rows_inserted"] += 1

                    successful += 1

                except Exception as e:
                    failed += 1
                    self.logger.error(
                        f"Failed to insert searches for invoice "
                        f"{invoice.get('Id', 'unknown')}: {e}"
                    )

            conn.commit()
            cursor.close()
            conn.close()

        except Exception as e:
            self.logger.error(f"Batch insertion error: {e}")
            failed += len(invoices)
            successful = 0

        return successful, failed

    def populate_from_csv(
        self,
        csv_path: Path,
        batch_size: int = 100,
        store_id: Optional[str] = None,
    ) -> None:
        """Populate InvoiceSearches from invoices CSV."""
        invoices = read_invoices_from_csv(csv_path, store_id=store_id)
        if not invoices:
            print(f"No invoice rows found in {csv_path}")
            return

        self.search_stats["start_time"] = datetime.now()
        store_note = f", store={store_id!r}" if store_id is not None else ""
        mode_note = ", blob2-only" if self.blob2_only else ""
        self.logger.info(
            f"Populating InvoiceSearches for {len(invoices)} invoices "
            f"from {csv_path} (batch size: {batch_size}{store_note}{mode_note})"
        )

        pbar = tqdm(total=len(invoices), desc="Populating invoice searches")

        for batch_start in range(0, len(invoices), batch_size):
            batch = invoices[batch_start : batch_start + batch_size]
            successful, failed = self.insert_invoice_searches_batch(batch)

            self.search_stats["invoices_processed"] += successful
            self.search_stats["invoices_failed"] += failed
            pbar.update(len(batch))

            self.logger.info(
                f"Batch {batch_start // batch_size + 1}: "
                f"{successful}/{len(batch)} invoices successful"
            )

        pbar.close()
        self.search_stats["end_time"] = datetime.now()
        self.print_summary()

    def print_summary(self) -> None:
        """Print population summary statistics."""
        start = self.search_stats["start_time"]
        end = self.search_stats["end_time"]
        duration = end - start if start and end else None

        total_invoices = (
            self.search_stats["invoices_processed"]
            + self.search_stats["invoices_failed"]
        )
        success_rate = (
            (self.search_stats["invoices_processed"] / total_invoices) * 100
            if total_invoices
            else 0.0
        )

        print("\n" + "=" * 60)
        print("INVOICE SEARCHES POPULATION SUMMARY")
        print("=" * 60)
        print(f"Invoices Processed:  {self.search_stats['invoices_processed']:,}")
        print(f"Invoices Failed:     {self.search_stats['invoices_failed']:,}")
        print(
            f"Search Rows Inserted:{self.search_stats['search_rows_inserted']:,}"
        )
        print(f"Invoice Success Rate:{success_rate:.1f}%")
        if duration:
            print(f"Duration:            {duration}")
            if self.search_stats["invoices_processed"] > 0:
                rate = (
                    self.search_stats["invoices_processed"]
                    / duration.total_seconds()
                )
                print(f"Rate:                {rate:.2f} invoices/second")
        print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate InvoiceSearches from an invoices CSV file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config universal_config.json --csv data/invoices_updated_server3-4.csv
  %(prog)s --host localhost --database testdb --user postgres --password secret \\
      --csv data/invoices.csv --batch-size 50
  %(prog)s --config universal_config.json --csv data/invoices.csv \\
      --store 3jFPYUVUpGqiJ5pT2TgaSXMj3986NQMzRXfYDBJq5owf
        """,
    )

    parser.add_argument(
        "--csv",
        required=True,
        type=str,
        help="Path to invoices CSV file (same format as Invoices table import)",
    )
    parser.add_argument("--config", type=str, help="Configuration file path (JSON)")
    parser.add_argument("--host", help="Database host")
    parser.add_argument("--database", help="Database name")
    parser.add_argument("--user", help="Database user")
    parser.add_argument("--password", help="Database password")
    parser.add_argument("--port", type=int, default=5432, help="Database port")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of invoices per batch (default: 100)",
    )
    parser.add_argument(
        "--store",
        help="Store ID to use for all invoices (overrides StoreDataId from CSV)",
    )
    parser.add_argument(
        "--blob2-only",
        action="store_true",
        help=(
            "Only insert search values from Blob2 (destination, metadata, "
            "notification URL/email). Skips invoice id, dates, amount, store, "
            "and computed BTC amount."
        ),
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only test database connection, do not populate",
    )

    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.is_file():
        print(f"Error: CSV file not found: {csv_path}")
        return 1

    if args.config:
        try:
            config = load_config(args.config)
            if not validate_config(config):
                print("Configuration validation failed")
                return 1
            args = merge_config_with_args(config, args)
            print(f"Loaded configuration from: {args.config}")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return 1

    for field in ("host", "database", "user", "password"):
        if not getattr(args, field):
            print(f"Error: --{field.replace('_', '-')} is required (or in config)")
            return 1

    if args.batch_size <= 0:
        print("Error: Batch size must be positive")
        return 1

    db_config = {
        "host": args.host,
        "database": args.database,
        "user": args.user,
        "password": args.password,
        "port": args.port,
    }

    populator = InvoiceSearchesPopulator(db_config, blob2_only=args.blob2_only)

    print("Testing database connection...")
    if not populator.test_connection():
        print("Database connection test failed.")
        return 1
    print("Database connection test successful.")

    if not populator.create_invoices_table_if_not_exists():
        print("Failed to create or verify InvoiceSearches table.")
        return 1

    if args.test_only:
        print("Test completed. Remove --test-only to populate InvoiceSearches.")
        return 0

    try:
        if args.store:
            print(f"Using store ID from --store: {args.store}")
        if args.blob2_only:
            print("Using --blob2-only: inserting only Blob2-derived search values")
        print(f"\nPopulating InvoiceSearches from {csv_path}...")
        populator.populate_from_csv(
            csv_path, batch_size=args.batch_size, store_id=args.store
        )

        if populator.search_stats["invoices_failed"] == 0:
            print(
                f"\nSuccessfully populated searches for "
                f"{populator.search_stats['invoices_processed']:,} invoices "
                f"({populator.search_stats['search_rows_inserted']:,} rows)."
            )
            return 0

        print(
            f"\n{populator.search_stats['invoices_failed']:,} invoice(s) failed. "
            "See logs/invoices_population.log for details."
        )
        return 1

    except KeyboardInterrupt:
        print("\nPopulation interrupted by user")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
