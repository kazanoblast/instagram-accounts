"""
Configuration for Appium Instagram automation.
"""

# Appium server settings
APPIUM_HOST = "http://127.0.0.1"
APPIUM_PORT = 4723
APPIUM_URL = f"{APPIUM_HOST}:{APPIUM_PORT}"

# Device capabilities
DEVICE_NAME = "iPhone"  # Change to your device name
PLATFORM_NAME = "iOS"
PLATFORM_VERSION = "17.0"  # Change to your iOS version
UDID = ""  # Set your device UDID here

# Instagram original app package
INSTAGRAM_BUNDLE_ID = "com.burbn.instagram"

# Number of clones
TOTAL_CLONES = 192
ACCOUNTS_PER_CLONE = 2

# Input/Output files
INPUT_SPREADSHEET = "accounts.csv"
OUTPUT_CSV = "output_results.csv"

# Timeouts (seconds)
IMPLICIT_WAIT = 10
EXPLICIT_WAIT = 30
LOGIN_DELAY = 5  # Delay between login attempts


def get_clone_bundle_id(clone_number: int) -> str:
    """
    Generate bundle ID for Instagram clone N.
    Pattern: com.burbn{n}.instagram{n}
    Original: com.burbn.instagram
    Clone 1:  com.burbn1.instagram1
    Clone 2:  com.burbn2.instagram2
    """
    if clone_number == 0:
        return INSTAGRAM_BUNDLE_ID
    return f"com.burbn{clone_number}.instagram{clone_number}"


def get_clone_app_name(clone_number: int) -> str:
    """
    Generate app name for Instagram clone N.
    Pattern: Instagram_N
    Original: Instagram
    Clone 1:  Instagram_1
    """
    if clone_number == 0:
        return "Instagram"
    return f"Instagram_{clone_number}"


def get_appium_capabilities(bundle_id: str) -> dict:
    """
    Return Appium desired capabilities for a given Instagram bundle ID.
    """
    caps = {
        "platformName": PLATFORM_NAME,
        "appium:automationName": "XCUITest",
        "appium:deviceName": DEVICE_NAME,
        "appium:platformVersion": PLATFORM_VERSION,
        "appium:bundleId": bundle_id,
        "appium:noReset": True,
        "appium:newCommandTimeout": 300,
    }
    if UDID:
        caps["appium:udid"] = UDID
    return caps
