"""
Export results to CSV using the real discovered bundle IDs.

Output pattern per row:
    "AppName, real.bundle.id"  (the actual bundle ID extracted from the device)

The base apps row (always present) uses:
    "YouTube, com.google.ios.youtube; Instagram, com.burbn.instagram; TikTok, com.zhiliaoapp.musically"

Each clone row uses the real app_name and bundle_id discovered from the device,
plus a column for each account username logged into that clone.
"""

import csv
import logging
from typing import List, Dict

from config import OUTPUT_CSV

logger = logging.getLogger(__name__)

# The fixed base apps string (always present for the original profile)
BASE_APPS_STRING = (
    "YouTube, com.google.ios.youtube; "
    "Instagram, com.burbn.instagram; "
    "TikTok, com.zhiliaoapp.musically"
)


def format_app_entry(app_name: str, bundle_id: str) -> str:
    """
    Format a single app entry as "AppName, bundle.id".
    Uses the real app name and bundle ID from the device.
    """
    return f"{app_name}, {bundle_id}"


def export_results(results: List[Dict], output_path: str = OUTPUT_CSV):
    """
    Export login results to CSV.

    Args:
        results: List of dicts with keys:
            - clone_number (int): 1-based index of the clone
            - app_name (str): Real app name from device (e.g. "InstaClone")
            - bundle_id (str): Real bundle ID from device (e.g. "com.xyz.instaclone")
            - account1_username (str)
            - account1_success (bool)
            - account2_username (str)
            - account2_success (bool)
        output_path: Path for the output CSV file.

    CSV Columns:
        - clone_number: The clone index
        - app_name: Real app display name from the device
        - bundle_id: Real bundle identifier from the device
        - app_entry: Formatted as "AppName, bundle.id"
        - base_apps: The fixed base apps string
        - account1_username: First account username
        - account1_status: success/failed
        - account2_username: Second account username
        - account2_status: success/failed
    """
    fieldnames = [
        "clone_number",
        "app_name",
        "bundle_id",
        "app_entry",
        "base_apps",
        "account1_username",
        "account1_status",
        "account2_username",
        "account2_status",
    ]

    rows = []
    for result in results:
        app_name = result.get("app_name", "")
        bundle_id = result.get("bundle_id", "")
        app_entry = format_app_entry(app_name, bundle_id)

        row = {
            "clone_number": result["clone_number"],
            "app_name": app_name,
            "bundle_id": bundle_id,
            "app_entry": app_entry,
            "base_apps": BASE_APPS_STRING,
            "account1_username": result.get("account1_username", ""),
            "account1_status": (
                "success" if result.get("account1_success") else "failed"
            ),
            "account2_username": result.get("account2_username", ""),
            "account2_status": (
                "success" if result.get("account2_success") else "failed"
            ),
        }
        rows.append(row)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Results exported to: {output_path}")
    logger.info(f"Total rows written: {len(rows)}")


def export_summary(results: List[Dict], output_path: str = "summary.csv"):
    """
    Export a simplified summary CSV with app entry and usernames.

    Format per row:
        "AppName, real.bundle.id", username1, username2
    """
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["app_entry", "username_1", "username_2"])

        for result in results:
            app_name = result.get("app_name", "")
            bundle_id = result.get("bundle_id", "")
            app_entry = format_app_entry(app_name, bundle_id)
            writer.writerow([
                app_entry,
                result.get("account1_username", ""),
                result.get("account2_username", ""),
            ])

    logger.info(f"Summary exported to: {output_path}")
