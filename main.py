"""
Main orchestrator script for Instagram multi-clone account login automation.

Reads accounts from a spreadsheet, discovers Instagram clones installed on
the device (extracting their real bundle IDs), logs 2 accounts per clone,
and exports results to CSV.

Usage:
    python main.py
    python main.py --input accounts.csv --output results.csv
    python main.py --discovery appium          # use Appium to find clones
    python main.py --discovery ideviceinstaller # use ideviceinstaller
    python main.py --discovery simctl          # use simulator
    python main.py --discovery csv --clone-csv clone_list.csv  # manual list
    python main.py --start-clone 50            # resume from clone 50
    python main.py --dry-run                   # test without Appium
"""

import argparse
import logging
import sys
import time
from typing import List, Dict, Tuple

import pandas as pd

from config import (
    ACCOUNTS_PER_CLONE,
    INPUT_SPREADSHEET,
    OUTPUT_CSV,
    DISCOVERY_METHOD,
    CLONE_LIST_CSV,
    UDID,
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


def validate_accounts(
    accounts: List[Dict], num_clones: int
) -> bool:
    """
    Validate that we have enough accounts for all discovered clones.
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


def discover_clones(
    method: str, csv_path: str, udid: str
) -> List[Dict[str, str]]:
    """
    Discover Instagram clone apps on the device.
    Returns list of {"app_name": ..., "bundle_id": ...} dicts.
    """
    from app_discovery import discover_instagram_clones

    clones = discover_instagram_clones(
        method=method,
        udid=udid or None,
        csv_path=csv_path if method == "csv" else None,
    )

    if not clones:
        logger.error(
            "No Instagram clones discovered! Check that:\n"
            "  - The device is connected and Appium is running\n"
            "  - Instagram clones are installed on the device\n"
            "  - The discovery method is correct\n"
            "  - If using CSV, the file exists and has app_name,bundle_id columns"
        )

    return clones


def run_automation(
    accounts_file: str,
    output_file: str,
    discovery_method: str = DISCOVERY_METHOD,
    clone_csv: str = CLONE_LIST_CSV,
    udid: str = UDID,
    start_clone: int = 1,
    dry_run: bool = False,
):
    """
    Main automation loop.

    Args:
        accounts_file: Path to the input spreadsheet
        output_file: Path for the output CSV
        discovery_method: How to find Instagram clones on the device
        clone_csv: Path to CSV with clone bundle IDs (for "csv" method)
        udid: Device UDID
        start_clone: Clone index to start from (1-based, for resuming)
        dry_run: If True, skip Appium and just generate output
    """
    # --- Step 1: Discover clones ---
    if dry_run:
        # In dry-run mode, generate fake clones for testing
        logger.info("Dry run: generating placeholder clone list...")
        clones = [
            {"app_name": f"FakeInsta_{i}", "bundle_id": f"com.fake{i}.insta{i}"}
            for i in range(1, 5)
        ]
    else:
        logger.info(f"Discovering Instagram clones (method: {discovery_method})...")
        clones = discover_clones(discovery_method, clone_csv, udid)
        if not clones:
            sys.exit(1)

    num_clones = len(clones)
    logger.info(f"Found {num_clones} Instagram clones on the device.")
    for i, clone in enumerate(clones, 1):
        logger.info(f"  Clone {i}: {clone['app_name']} ({clone['bundle_id']})")

    # --- Step 2: Load and validate accounts ---
    accounts = load_accounts(accounts_file)

    if not validate_accounts(accounts, num_clones):
        sys.exit(1)

    account_pairs = pair_accounts(accounts, num_clones)

    # --- Step 3: Run login automation ---
    all_results = []

    automation = None
    if not dry_run:
        from instagram_login import InstagramAutomation
        automation = InstagramAutomation()

    logger.info(f"Starting automation for {num_clones} clones...")
    logger.info(f"Starting from clone index: {start_clone}")

    for clone_idx in range(start_clone - 1, num_clones):
        clone = clones[clone_idx]
        clone_number = clone_idx + 1
        bundle_id = clone["bundle_id"]
        app_name = clone["app_name"]
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

        # Save intermediate results every 10 clones
        if clone_number % 10 == 0:
            intermediate_file = f"intermediate_results_{clone_number}.csv"
            export_results(all_results, intermediate_file)
            logger.info(
                f"Intermediate results saved at clone {clone_number}"
            )

        if not dry_run:
            time.sleep(2)

    # --- Step 4: Export final results ---
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
        "--input", "-i",
        default=INPUT_SPREADSHEET,
        help=f"Input spreadsheet path (default: {INPUT_SPREADSHEET})",
    )
    parser.add_argument(
        "--output", "-o",
        default=OUTPUT_CSV,
        help=f"Output CSV path (default: {OUTPUT_CSV})",
    )
    parser.add_argument(
        "--discovery",
        default=DISCOVERY_METHOD,
        choices=["auto", "appium", "ideviceinstaller", "simctl", "csv"],
        help=f"How to discover Instagram clones (default: {DISCOVERY_METHOD})",
    )
    parser.add_argument(
        "--clone-csv",
        default=CLONE_LIST_CSV,
        help="CSV file with clone bundle IDs (for --discovery csv)",
    )
    parser.add_argument(
        "--udid",
        default=UDID,
        help="Device UDID (overrides config.py)",
    )
    parser.add_argument(
        "--start-clone", "-s",
        type=int,
        default=1,
        help="Clone index to start from, for resuming (default: 1)",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Dry run mode - skip Appium, generate sample output",
    )

    args = parser.parse_args()

    run_automation(
        accounts_file=args.input,
        output_file=args.output,
        discovery_method=args.discovery,
        clone_csv=args.clone_csv,
        udid=args.udid,
        start_clone=args.start_clone,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
