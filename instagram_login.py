"""
Instagram login automation using Appium.
Handles launching Instagram clones and logging in accounts.
"""

import time
import logging
from typing import Optional

from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

from config import (
    APPIUM_URL,
    IMPLICIT_WAIT,
    EXPLICIT_WAIT,
    LOGIN_DELAY,
    get_appium_capabilities,
)

logger = logging.getLogger(__name__)


class InstagramAutomation:
    """Handles Appium-based Instagram login automation."""

    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None

    def start_session(self, bundle_id: str) -> bool:
        """
        Start an Appium session for the given Instagram bundle ID.
        Returns True if session started successfully.
        """
        try:
            caps = get_appium_capabilities(bundle_id)
            options = AppiumOptions()
            for key, value in caps.items():
                options.set_capability(key, value)

            self.driver = webdriver.Remote(APPIUM_URL, options=options)
            self.driver.implicitly_wait(IMPLICIT_WAIT)
            logger.info(f"Started Appium session for bundle: {bundle_id}")
            time.sleep(3)  # Wait for app to fully load
            return True
        except WebDriverException as e:
            logger.error(f"Failed to start session for {bundle_id}: {e}")
            return False

    def quit_session(self):
        """Quit the current Appium session."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Appium session closed.")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self.driver = None

    def _wait_and_find(self, by, value, timeout=EXPLICIT_WAIT):
        """Wait for an element and return it."""
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))

    def _wait_and_click(self, by, value, timeout=EXPLICIT_WAIT):
        """Wait for an element to be clickable and click it."""
        wait = WebDriverWait(self.driver, timeout)
        element = wait.until(EC.element_to_be_clickable((by, value)))
        element.click()
        return element

    def _is_logged_in(self) -> bool:
        """Check if an account is currently logged in."""
        try:
            # Look for the home tab or profile tab indicating logged-in state
            self.driver.find_element(
                AppiumBy.ACCESSIBILITY_ID, "Home"
            )
            return True
        except NoSuchElementException:
            return False

    def _navigate_to_login_screen(self) -> bool:
        """
        Navigate to the login screen from the initial Instagram screen.
        Returns True if login screen is reached.
        """
        try:
            # Try tapping "Log in" if on the welcome screen
            try:
                self._wait_and_click(
                    AppiumBy.ACCESSIBILITY_ID, "Log in", timeout=10
                )
                time.sleep(2)
                return True
            except TimeoutException:
                pass

            # Alternative: look for "Log into another account" or similar
            try:
                self._wait_and_click(
                    AppiumBy.ACCESSIBILITY_ID,
                    "Log Into Another Account",
                    timeout=5,
                )
                time.sleep(2)
                return True
            except TimeoutException:
                pass

            # If already on login screen (username field visible)
            try:
                self.driver.find_element(
                    AppiumBy.ACCESSIBILITY_ID, "Username"
                )
                return True
            except NoSuchElementException:
                pass

            logger.warning("Could not navigate to login screen.")
            return False

        except Exception as e:
            logger.error(f"Error navigating to login: {e}")
            return False

    def _perform_login(self, username: str, password: str) -> bool:
        """
        Perform the actual login with username and password.
        Returns True if login was successful.
        """
        try:
            # Find and fill username field
            username_field = self._wait_and_find(
                AppiumBy.ACCESSIBILITY_ID, "Username"
            )
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(1)

            # Find and fill password field
            password_field = self._wait_and_find(
                AppiumBy.ACCESSIBILITY_ID, "Password"
            )
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(1)

            # Tap Log In button
            self._wait_and_click(AppiumBy.ACCESSIBILITY_ID, "Log in")
            time.sleep(LOGIN_DELAY)

            # Handle potential "Save Login Info" popup
            self._dismiss_save_login_popup()

            # Handle potential "Turn on Notifications" popup
            self._dismiss_notifications_popup()

            # Verify login success
            if self._is_logged_in():
                logger.info(f"Successfully logged in: {username}")
                return True
            else:
                logger.warning(f"Login may have failed for: {username}")
                return False

        except TimeoutException as e:
            logger.error(f"Timeout during login for {username}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during login for {username}: {e}")
            return False

    def _dismiss_save_login_popup(self):
        """Dismiss the 'Save Login Info' popup if it appears."""
        try:
            self._wait_and_click(
                AppiumBy.ACCESSIBILITY_ID, "Save", timeout=5
            )
            time.sleep(1)
        except TimeoutException:
            # Try "Not Now" as alternative
            try:
                self._wait_and_click(
                    AppiumBy.ACCESSIBILITY_ID, "Not Now", timeout=3
                )
                time.sleep(1)
            except TimeoutException:
                pass

    def _dismiss_notifications_popup(self):
        """Dismiss the notifications prompt if it appears."""
        try:
            self._wait_and_click(
                AppiumBy.ACCESSIBILITY_ID, "Not Now", timeout=5
            )
            time.sleep(1)
        except TimeoutException:
            pass

    def _switch_to_add_account(self) -> bool:
        """
        Navigate to add a second account (multi-account feature).
        Returns True if ready to add another account.
        """
        try:
            # Go to profile tab
            self._wait_and_click(
                AppiumBy.ACCESSIBILITY_ID, "Profile", timeout=10
            )
            time.sleep(2)

            # Tap the username/dropdown at the top to open account switcher
            try:
                # Look for the dropdown arrow or username at top
                self._wait_and_click(
                    AppiumBy.ACCESSIBILITY_ID,
                    "Account Switcher",
                    timeout=5,
                )
            except TimeoutException:
                # Try tapping username directly
                try:
                    username_header = self.driver.find_element(
                        AppiumBy.XPATH,
                        '//XCUIElementTypeButton[contains(@name, "chevron")]',
                    )
                    username_header.click()
                except NoSuchElementException:
                    logger.warning("Could not find account switcher.")
                    return False

            time.sleep(2)

            # Tap "Add Account" or "Log Into Another Account"
            try:
                self._wait_and_click(
                    AppiumBy.ACCESSIBILITY_ID, "Add account", timeout=5
                )
            except TimeoutException:
                try:
                    self._wait_and_click(
                        AppiumBy.ACCESSIBILITY_ID,
                        "Log Into Another Account",
                        timeout=5,
                    )
                except TimeoutException:
                    logger.warning("Could not find 'Add Account' option.")
                    return False

            time.sleep(2)

            # Should now be on login screen
            try:
                # Tap "Log in" if presented with options
                self._wait_and_click(
                    AppiumBy.ACCESSIBILITY_ID, "Log in", timeout=5
                )
                time.sleep(2)
            except TimeoutException:
                pass

            return True

        except Exception as e:
            logger.error(f"Error switching to add account: {e}")
            return False

    def login_accounts(
        self, bundle_id: str, account1: dict, account2: dict
    ) -> dict:
        """
        Log in two accounts into the specified Instagram clone.

        Args:
            bundle_id: The bundle ID of the Instagram clone
            account1: Dict with 'username' and 'password' keys
            account2: Dict with 'username' and 'password' keys

        Returns:
            Dict with login results for both accounts
        """
        results = {
            "account1_username": account1["username"],
            "account1_success": False,
            "account2_username": account2["username"],
            "account2_success": False,
        }

        # Start session
        if not self.start_session(bundle_id):
            logger.error(f"Could not start session for {bundle_id}")
            return results

        try:
            # Login first account
            logger.info(
                f"Logging in account 1: {account1['username']} "
                f"into {bundle_id}"
            )

            if self._is_logged_in():
                # App already has a logged-in account, go to add account
                if self._switch_to_add_account():
                    results["account1_success"] = self._perform_login(
                        account1["username"], account1["password"]
                    )
            else:
                # Fresh app, navigate to login
                if self._navigate_to_login_screen():
                    results["account1_success"] = self._perform_login(
                        account1["username"], account1["password"]
                    )

            time.sleep(3)

            # Login second account
            logger.info(
                f"Logging in account 2: {account2['username']} "
                f"into {bundle_id}"
            )

            if results["account1_success"]:
                # First login succeeded, add second account
                if self._switch_to_add_account():
                    results["account2_success"] = self._perform_login(
                        account2["username"], account2["password"]
                    )
            else:
                # First login failed, try login screen again
                if self._navigate_to_login_screen():
                    results["account2_success"] = self._perform_login(
                        account2["username"], account2["password"]
                    )

        finally:
            self.quit_session()

        return results
