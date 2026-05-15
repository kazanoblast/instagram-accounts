"""
Discover Instagram clone apps installed on the iOS device.

Supports multiple discovery methods:
  1. Appium session: `mobile: listApps` (real device only)
  2. ideviceinstaller CLI (real device, requires libimobiledevice)
  3. xcrun simctl (simulator only)
  4. Manual CSV file (fallback: user provides bundle IDs)

Each discovered app is returned as:
    {"app_name": "SomeInsta", "bundle_id": "com.xyz.someapp"}
"""

import csv
import json
import logging
import re
import subprocess
from typing import List, Dict, Optional

from appium import webdriver
from appium.options.common import AppiumOptions

from config import (
    APPIUM_URL,
    INSTAGRAM_BUNDLE_ID,
    IMPLICIT_WAIT,
    get_appium_capabilities,
)

logger = logging.getLogger(__name__)

# Keywords that typically identify Instagram clone apps.
# Extend this list based on the naming conventions of your clones.
INSTAGRAM_KEYWORDS = [
    "instagram",
    "insta",
    "gram",
    "burbn",
]


def _matches_instagram(bundle_id: str, app_name: str = "") -> bool:
    """
    Check if a bundle ID or app name looks like an Instagram clone.
    Excludes the original Instagram app.
    """
    combined = f"{bundle_id} {app_name}".lower()
    if bundle_id == INSTAGRAM_BUNDLE_ID:
        return False
    return any(kw in combined for kw in INSTAGRAM_KEYWORDS)


# ---------------------------------------------------------------------------
# Method 1: Appium `mobile: listApps` (real device)
# ---------------------------------------------------------------------------

def discover_via_appium(
    udid: Optional[str] = None,
    extra_caps: Optional[dict] = None,
) -> List[Dict[str, str]]:
    """
    Start a lightweight Appium session (using Settings app) and call
    `mobile: listApps` to enumerate all user-installed apps.

    Returns a list of {"app_name": ..., "bundle_id": ...} dicts for
    every app that looks like an Instagram clone.
    """
    # Use the Settings app so we don't need any specific app installed
    caps = {
        "platformName": "iOS",
        "appium:automationName": "XCUITest",
        "appium:deviceName": "iPhone",
        "appium:bundleId": "com.apple.Preferences",
        "appium:noReset": True,
        "appium:newCommandTimeout": 120,
    }
    if udid:
        caps["appium:udid"] = udid
    if extra_caps:
        caps.update(extra_caps)

    options = AppiumOptions()
    for k, v in caps.items():
        options.set_capability(k, v)

    driver = None
    try:
        driver = webdriver.Remote(APPIUM_URL, options=options)
        driver.implicitly_wait(IMPLICIT_WAIT)

        # mobile: listApps returns list of dicts with bundle-id keys
        apps = driver.execute_script("mobile: listApps", {"applicationType": "User"})

        clones: List[Dict[str, str]] = []
        for app_info in apps:
            bid = app_info.get("CFBundleIdentifier", "")
            name = app_info.get("CFBundleDisplayName", "") or app_info.get("CFBundleName", "")
            if _matches_instagram(bid, name):
                clones.append({"app_name": name, "bundle_id": bid})

        logger.info(f"Appium discovery found {len(clones)} Instagram clones.")
        return clones

    except Exception as e:
        logger.error(f"Appium discovery failed: {e}")
        return []
    finally:
        if driver:
            driver.quit()


# ---------------------------------------------------------------------------
# Method 2: ideviceinstaller (real device CLI)
# ---------------------------------------------------------------------------

def discover_via_ideviceinstaller(
    udid: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Use `ideviceinstaller -l` to list installed apps.
    Requires libimobiledevice to be installed (`brew install libimobiledevice`).
    """
    cmd = ["ideviceinstaller", "-l", "-o", "list_all"]
    if udid:
        cmd.extend(["-u", udid])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logger.error(f"ideviceinstaller failed: {result.stderr}")
            return []

        clones: List[Dict[str, str]] = []
        for line in result.stdout.strip().splitlines():
            # Format: "com.example.app, Version - DisplayName"
            # or just "com.example.app"
            line = line.strip()
            if not line or line.startswith("Total") or line.startswith("CFBundle"):
                continue

            parts = line.split(",", 1)
            bid = parts[0].strip()
            name = ""
            if len(parts) > 1:
                # Try to extract display name after the version
                rest = parts[1].strip()
                name_match = re.search(r'- (.+)$', rest)
                if name_match:
                    name = name_match.group(1).strip().strip('"')

            if _matches_instagram(bid, name):
                clones.append({
                    "app_name": name or bid,
                    "bundle_id": bid,
                })

        logger.info(
            f"ideviceinstaller discovery found {len(clones)} Instagram clones."
        )
        return clones

    except FileNotFoundError:
        logger.error(
            "ideviceinstaller not found. "
            "Install with: brew install libimobiledevice"
        )
        return []
    except subprocess.TimeoutExpired:
        logger.error("ideviceinstaller timed out.")
        return []


# ---------------------------------------------------------------------------
# Method 3: xcrun simctl (simulator)
# ---------------------------------------------------------------------------

def discover_via_simctl(
    device_udid: str = "booted",
) -> List[Dict[str, str]]:
    """
    Use `xcrun simctl listapps` to enumerate apps on a simulator.
    """
    cmd = ["xcrun", "simctl", "listapps", device_udid]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            logger.error(f"simctl listapps failed: {result.stderr}")
            return []

        # Output is a plist; convert to JSON via plutil
        plutil_result = subprocess.run(
            ["plutil", "-convert", "json", "-o", "-", "-"],
            input=result.stdout,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if plutil_result.returncode != 0:
            logger.error(f"plutil conversion failed: {plutil_result.stderr}")
            return []

        apps_dict = json.loads(plutil_result.stdout)
        clones: List[Dict[str, str]] = []

        for bid, info in apps_dict.items():
            name = info.get("CFBundleDisplayName", "") or info.get("CFBundleName", "")
            if _matches_instagram(bid, name):
                clones.append({"app_name": name or bid, "bundle_id": bid})

        logger.info(f"simctl discovery found {len(clones)} Instagram clones.")
        return clones

    except FileNotFoundError:
        logger.error("xcrun not found. Are Xcode CLI tools installed?")
        return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        logger.error(f"simctl discovery error: {e}")
        return []


# ---------------------------------------------------------------------------
# Method 4: Manual CSV fallback
# ---------------------------------------------------------------------------

def discover_via_csv(filepath: str) -> List[Dict[str, str]]:
    """
    Load clone bundle IDs from a CSV file.
    Expected columns: app_name, bundle_id
    """
    clones: List[Dict[str, str]] = []
    try:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                bid = row.get("bundle_id", "").strip()
                name = row.get("app_name", "").strip()
                if bid:
                    clones.append({"app_name": name or bid, "bundle_id": bid})

        logger.info(f"CSV discovery loaded {len(clones)} clones from {filepath}.")
        return clones

    except FileNotFoundError:
        logger.error(f"Clone list CSV not found: {filepath}")
        return []
    except Exception as e:
        logger.error(f"Error reading clone CSV: {e}")
        return []


# ---------------------------------------------------------------------------
# Unified discovery
# ---------------------------------------------------------------------------

def discover_instagram_clones(
    method: str = "auto",
    udid: Optional[str] = None,
    csv_path: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Discover Instagram clone apps using the specified method.

    Args:
        method: One of "appium", "ideviceinstaller", "simctl", "csv", "auto".
                "auto" tries appium -> ideviceinstaller -> simctl in order.
        udid: Device UDID (optional, used by appium/ideviceinstaller/simctl).
        csv_path: Path to a CSV with app_name,bundle_id columns (for "csv" method).

    Returns:
        Sorted list of {"app_name": ..., "bundle_id": ...} dicts.
    """
    clones: List[Dict[str, str]] = []

    if method == "csv":
        if not csv_path:
            logger.error("csv_path is required for CSV discovery method.")
            return []
        clones = discover_via_csv(csv_path)

    elif method == "appium":
        clones = discover_via_appium(udid=udid)

    elif method == "ideviceinstaller":
        clones = discover_via_ideviceinstaller(udid=udid)

    elif method == "simctl":
        clones = discover_via_simctl(device_udid=udid or "booted")

    elif method == "auto":
        # Try methods in order of preference
        logger.info("Auto-discovering Instagram clones...")

        clones = discover_via_appium(udid=udid)
        if clones:
            return sorted(clones, key=lambda c: c["bundle_id"])

        logger.info("Appium method failed, trying ideviceinstaller...")
        clones = discover_via_ideviceinstaller(udid=udid)
        if clones:
            return sorted(clones, key=lambda c: c["bundle_id"])

        logger.info("ideviceinstaller failed, trying simctl...")
        clones = discover_via_simctl(device_udid=udid or "booted")
        if clones:
            return sorted(clones, key=lambda c: c["bundle_id"])

        logger.warning("All auto-discovery methods failed.")
    else:
        logger.error(f"Unknown discovery method: {method}")

    # Sort by bundle ID for consistent ordering
    return sorted(clones, key=lambda c: c["bundle_id"])
