"""
Export results to CSV following the required naming pattern.

Pattern for original app:
    "Name, xxx.xxx.xxx" -> "Instagram, com.burbn.instagram"
    Always includes: "YouTube, com.google.ios.youtube; Instagram, com.burbn.instagram; TikTok, com.zhiliaoapp.musically"

Pattern for clone apps:
    "Name_N, xxx.xxx.xxx" -> "Instagram_1, com.burbn1.instagram1"

Each row also includes the account usernames logged into that clone.
"""

import csv
import logging
from typing import List, Dict

from config import (
    TOTAL_CLONES,
    OUTPUT_CSV,
    get_clone_bundle_id,
    get_clone_app_name,
)

logger = logging.getLogger(__name__)

# The fixed base apps string (always present for each device/profile)
BASE_APPS_STRING = (
    "YouTube, com.google.ios.youtube; "
    "Instagram, com.burbn.instagram; "
    "TikTok, com.zhiliaoapp.musically"
)


def generate_clone_apps_string(clone_number: int) -> str:
    """
    Generate the app string for a specific clone number.

    For clone N:
        "Instagram_N, com.burbnN.instagramN"

    Combined with the base apps for that device profile:
        "YouTube_N, com.google.iosN.youtubeN; Instagram_N, com.burbnN.instagramN; TikTok_N, com.zhiliaoapp.musicallyN"
    """
    app_name = get_clone_app_name(clone_number)
    bundle_id = get_clone_bundle_id(clone_number)
    return f"{app_name}, {bundle_id}"


def generate_full_clone_row_apps(clone_number: int) -> str:
    """
    Generate the full apps string for a clone row.
    Includes YouTube_N, Instagram_N, TikTok_N clones.
    """
    if clone_number == 0:
        return BASE_APPS_STRING

    yt_name = f"YouTube_{clone_number}"
    yt_bundle = f"com.google.ios{clone_number}.youtube{clone_number}"

    ig_name = f"Instagram_{clone_number}"
    ig_bundle = f"com.burbn{clone_number}.instagram{clone_number}"

    tt_name = f"TikTok_{clone_number}"
    tt_bundle = f"com.zhiliaoapp{clone_number}.musically{clone_number}"

    return f"{yt_name}, {yt_bundle}; {ig_name}, {ig_bundle}; {tt_name}, {tt_bundle}"


def export_results(results: List[Dict], output_path: str = OUTPUT_CSV):
    """
    Export login results to CSV.

    Args:
        results: List of dicts with keys:
            - clone_number (int)
            - app_name (str)
            - bundle_id (str)
            - account1_username (str)
            - account1_success (bool)
            - account2_username (str)
            - account2_success (bool)
        output_path: Path for the output CSV file.

    CSV Columns:
        - clone_number: The clone index (0 = original, 1-192 = clones)
        - app_entry: "Name, bundle.id" or "Name_N, bundle.id.N"
        - full_apps_string: Full apps line for the profile
        - account1_username: First account username
        - account1_status: login success/fail
        - account2_username: Second account username
        - account2_status: login success/fail
    """
    fieldnames = [
        "clone_number",
        "app_entry",
        "full_apps_string",
        "account1_username",
        "account1_status",
        "account2_username",
        "account2_status",
    ]

    rows = []
    for result in results:
        clone_num = result["clone_number"]
        app_entry = generate_clone_apps_string(clone_num)
        full_apps = generate_full_clone_row_apps(clone_num)

        row = {
            "clone_number": clone_num,
            "app_entry": app_entry,
            "full_apps_string": full_apps,
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
    Export a simplified summary CSV with just the app pattern and usernames.

    Format per row:
        apps_string, username1, username2

    Example:
        "Instagram_1, com.burbn1.instagram1", user1, user2
    """
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["apps_entry", "username_1", "username_2"])

        for result in results:
            clone_num = result["clone_number"]
            app_entry = generate_clone_apps_string(clone_num)
            writer.writerow([
                app_entry,
                result.get("account1_username", ""),
                result.get("account2_username", ""),
            ])

    logger.info(f"Summary exported to: {output_path}")
