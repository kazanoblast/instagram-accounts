"""
Main orchestrator script for Instagram multi-clone account login automation.

Reads accounts from a spreadsheet, logs 2 accounts per Instagram clone
(192 clones total = 384 accounts), and exports results to CSV.

Usage:
    python main.py
    python main.py --input accounts.csv --output results.csv
    python main.py --start-clone 50  # Resume from clone 50
    python main.py --dry-run  # Test without Appium
"""

import argparse
import logging
import sys
import time
from typing import List, Dict, Tuple

import pandas as pd

from config import (
    TOTAL_CLONES,
    ACCOUNTS_PER_CLONE,
    INPUT_SPREADSHEET,
    OUTPUT_CSV,
    get_clone_bundle_id,
    get_clone_app_name,
)
from export_results import export_results, export_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("automation.log"),
    ],
)
logger = logging.getLogger(__name__)


def load_accounts(filepath: str) -> List[Dict[str, str]]:
    """
    Load accounts from a spreadsheet (CSV or Excel).

    Expected columns: username, password
    Optional columns: email, phone

    Returns list of dicts with 'username' and 'password' keys.
    """
    logger.info(f"Loading accounts from: {filepath}")

    if filepath.endswith((".xlsx", ".xls")):
        df = pd.read_excel(filepath)
    elif filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        raise ValueError(
            f"Unsupported file format: {filepath}. Use .csv or .xlsx"
        )

    # Normalize column names
    df.columns = df.columns.str.strip().str.lower()

    if "username" not in df.columns or "password" not in df.columns:
        raise ValueError(
            "Spreadsheet must contain 'username' and 'password' columns."
        )

    accounts = df[["username", "password"]].to_dict("records")
    logger.info(f"Loaded {len(accounts)} accounts.")

    return accounts


def validate_accounts(accounts: List[Dict], num_clones: int) -> bool:
    """
    Validate that we have enough accounts for all clones.
    Each clone needs 2 accounts.
    """
    required = num_clones * ACCOUNTS_PER_CLONE
    available = len(accounts)

    if available < required:
        logger.error(
            f"Not enough accounts! Need {required} "
            f"(for {num_clones} clones x {ACCOUNTS_PER_CLONE} each), "
            f"but only have {available}."
        )
        return False

    logger.info(
        f"Account validation passed: {available} available, "
        f"{required} required."
    )
    return True


def pair_accounts(
    accounts: List[Dict], num_clones: int
) -> List[Tuple[Dict, Dict]]:
    """
    Pair accounts into groups of 2 for each clone.
    Returns list of (account1, account2) tuples.
    """
    pairs = []
    for i in range(num_clones):
        idx = i * ACCOUNTS_PER_CLONE
        account1 = accounts[idx]
        account2 = accounts[idx + 1]
        pairs.append((account1, account2))

    return pairs


def run_automation(
    accounts_file: str,
    output_file: str,
    num_clones: int = TOTAL_CLONES,
    start_clone: int = 1,
    dry_run: bool = False,
):
    """
    Main automation loop.

    Args:
        accounts_file: Path to the input spreadsheet
        output_file: Path for the output CSV
        num_clones: Number of Instagram clones to process
        start_clone: Clone number to start from (for resuming)
        dry_run: If True, skip Appium and just generate output
    """
    # Load accounts
    accounts = load_accounts(accounts_file)

    # Validate
    if not validate_accounts(accounts, num_clones):
        sys.exit(1)

    # Pair accounts
    account_pairs = pair_accounts(accounts, num_clones)

    # Results storage
    all_results = []

    # Initialize automation (only import if not dry run)
    automation = None
    if not dry_run:
        from instagram_login import InstagramAutomation
        automation = InstagramAutomation()

    logger.info(f"Starting automation for {num_clones} clones...")
    logger.info(f"Starting from clone: {start_clone}")

    for clone_idx in range(start_clone - 1, num_clones):
        clone_number = clone_idx + 1
        bundle_id = get_clone_bundle_id(clone_number)
        app_name = get_clone_app_name(clone_number)
        account1, account2 = account_pairs[clone_idx]

        logger.info(
            f"\n{'='*60}\n"
            f"Processing clone {clone_number}/{num_clones}: {app_name}\n"
            f"Bundle ID: {bundle_id}\n"
            f"Account 1: {account1['username']}\n"
            f"Account 2: {account2['username']}\n"
            f"{'='*60}"
        )

        if dry_run:
            # Dry run - simulate success
            result = {
                "clone_number": clone_number,
                "app_name": app_name,
                "bundle_id": bundle_id,
                "account1_username": account1["username"],
                "account1_success": True,
                "account2_username": account2["username"],
                "account2_success": True,
            }
        else:
            # Actual automation
            login_result = automation.login_accounts(
                bundle_id, account1, account2
            )
            result = {
                "clone_number": clone_number,
                "app_name": app_name,
                "bundle_id": bundle_id,
                **login_result,
            }

        all_results.append(result)

        # Export intermediate results (in case of crash/interruption)
        if clone_number % 10 == 0:
            intermediate_file = f"intermediate_results_{clone_number}.csv"
            export_results(all_results, intermediate_file)
            logger.info(
                f"Intermediate results saved at clone {clone_number}"
            )

        # Brief delay between clones
        if not dry_run:
            time.sleep(2)

    # Final export
    logger.info("\nAutomation complete! Exporting final results...")
    export_results(all_results, output_file)
    export_summary(all_results, output_file.replace(".csv", "_summary.csv"))

    # Print summary
    successful_1 = sum(1 for r in all_results if r["account1_success"])
    successful_2 = sum(1 for r in all_results if r["account2_success"])
    total_success = successful_1 + successful_2
    total_attempts = len(all_results) * 2

    logger.info(
        f"\n{'='*60}\n"
        f"FINAL SUMMARY\n"
        f"{'='*60}\n"
        f"Clones processed: {len(all_results)}\n"
        f"Account 1 successes: {successful_1}/{len(all_results)}\n"
        f"Account 2 successes: {successful_2}/{len(all_results)}\n"
        f"Total logins: {total_success}/{total_attempts}\n"
        f"Output file: {output_file}\n"
        f"{'='*60}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Instagram multi-clone account login automation"
    )
    parser.add_argument(
        "--input",
        "-i",
        default=INPUT_SPREADSHEET,
        help=f"Input spreadsheet path (default: {INPUT_SPREADSHEET})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=OUTPUT_CSV,
        help=f"Output CSV path (default: {OUTPUT_CSV})",
    )
    parser.add_argument(
        "--clones",
        "-c",
        type=int,
        default=TOTAL_CLONES,
        help=f"Number of clones to process (default: {TOTAL_CLONES})",
    )
    parser.add_argument(
        "--start-clone",
        "-s",
        type=int,
        default=1,
        help="Clone number to start from, for resuming (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Dry run mode - skip Appium, generate sample output",
    )

    args = parser.parse_args()

    run_automation(
        accounts_file=args.input,
        output_file=args.output,
        num_clones=args.clones,
        start_clone=args.start_clone,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
