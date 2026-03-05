"""
Version checker module for TRCLI.

Checks PyPI for the latest version of trcli and notifies users if an update is available.
Uses a cache file to avoid excessive API calls (24-hour cache TTL).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import requests
except ImportError:
    requests = None

try:
    from packaging import version
except ImportError:
    version = None

from trcli import __version__

# Constants
PYPI_API_URL = "https://pypi.org/pypi/trcli/json"
VERSION_CHECK_INTERVAL = 86400  # 24 hours in seconds
VERSION_CACHE_DIR = Path.home() / ".trcli"
VERSION_CACHE_FILE = VERSION_CACHE_DIR / "version_cache.json"
REQUEST_TIMEOUT = 2  # seconds

logger = logging.getLogger(__name__)


def check_for_updates(current_version: Optional[str] = None) -> Optional[str]:
    """
    Check if a newer version of TRCLI is available on PyPI.

    Args:
        current_version: Current version string. Defaults to trcli.__version__

    Returns:
        Formatted update message if newer version available, None otherwise

    Note:
        This function never raises exceptions - all errors are caught and logged.
    """
    if requests is None or version is None:
        logger.debug("Required dependencies (requests, packaging) not available for version check")
        return None

    if current_version is None:
        current_version = __version__

    try:
        # Check if we need to query PyPI (cache expired or doesn't exist)
        if _is_cache_valid():
            cache_data = _get_cache()
            latest_version = cache_data.get("latest_version")
            if latest_version:
                return _compare_and_format(current_version, latest_version)

        # Cache expired or invalid, query PyPI
        latest_version = _query_pypi()
        if latest_version:
            # Save to cache
            _save_cache({"last_check": datetime.now().isoformat(), "latest_version": latest_version})
            return _compare_and_format(current_version, latest_version)

    except Exception as e:
        logger.debug(f"Version check failed: {e}")

    return None


def _query_pypi() -> Optional[str]:
    """
    Query PyPI API for the latest version of trcli.

    Returns:
        Latest version string from PyPI, or None if query fails
    """
    try:
        logger.debug(f"Querying PyPI API: {PYPI_API_URL}")
        response = requests.get(PYPI_API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        data = response.json()
        latest_version = data.get("info", {}).get("version")

        if latest_version:
            logger.debug(f"Latest version from PyPI: {latest_version}")
            return latest_version
        else:
            logger.debug("Could not extract version from PyPI response")
            return None

    except requests.exceptions.Timeout:
        logger.debug("PyPI API request timed out")
        return None
    except requests.exceptions.ConnectionError:
        logger.debug("Could not connect to PyPI (network issue)")
        return None
    except requests.exceptions.HTTPError as e:
        logger.debug(f"PyPI API returned error: {e}")
        return None
    except json.JSONDecodeError:
        logger.debug("Invalid JSON response from PyPI")
        return None
    except Exception as e:
        logger.debug(f"Unexpected error querying PyPI: {e}")
        return None


def _get_cache() -> Dict[str, Any]:
    """
    Read version cache from disk.

    Returns:
        Cache data dictionary, or empty dict if cache doesn't exist or is invalid
    """
    try:
        if VERSION_CACHE_FILE.exists():
            with open(VERSION_CACHE_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError) as e:
        logger.debug(f"Failed to read version cache: {e}")

    return {}


def _save_cache(data: Dict[str, Any]) -> None:
    """
    Save version cache to disk.

    Args:
        data: Cache data dictionary to save

    Note:
        Creates cache directory if it doesn't exist. Failures are logged but not raised.
    """
    try:
        # Create cache directory if it doesn't exist
        VERSION_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with open(VERSION_CACHE_FILE, "w") as f:
            json.dump(data, f)

        logger.debug(f"Version cache saved to {VERSION_CACHE_FILE}")

    except (IOError, OSError) as e:
        logger.debug(f"Failed to save version cache: {e}")


def _is_cache_valid() -> bool:
    """
    Check if the version cache is valid (exists and not expired).

    Returns:
        True if cache is valid and fresh, False otherwise
    """
    try:
        if not VERSION_CACHE_FILE.exists():
            logger.debug("Version cache does not exist")
            return False

        cache_data = _get_cache()
        if not cache_data or "last_check" not in cache_data:
            logger.debug("Version cache is empty or invalid")
            return False

        last_check_str = cache_data["last_check"]
        last_check = datetime.fromisoformat(last_check_str)

        # Check if cache is still fresh (within 24 hours)
        cache_age = datetime.now() - last_check
        is_valid = cache_age < timedelta(seconds=VERSION_CHECK_INTERVAL)

        if is_valid:
            logger.debug(f"Version cache is valid (age: {cache_age})")
        else:
            logger.debug(f"Version cache expired (age: {cache_age})")

        return is_valid

    except (ValueError, KeyError) as e:
        logger.debug(f"Failed to validate cache: {e}")
        return False


def _compare_and_format(current: str, latest: str) -> Optional[str]:
    """
    Compare current and latest versions, and format update message if newer version available.

    Args:
        current: Current version string
        latest: Latest version string from PyPI

    Returns:
        Formatted update message if latest > current, None otherwise
    """
    try:
        current_ver = version.parse(current)
        latest_ver = version.parse(latest)

        if latest_ver > current_ver:
            return _format_message(current, latest)
        else:
            logger.debug(f"Current version {current} is up to date (latest: {latest})")
            return None

    except Exception as e:
        logger.debug(f"Failed to compare versions: {e}")
        return None


def _format_message(current: str, latest: str) -> str:
    """
    Format the update notification message.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        Formatted multi-line update message
    """
    return (
        f"\n A new version of TestRail CLI is available!\n"
        f"   Current: {current} | Latest: {latest}\n"
        f"   Update with: pip install --upgrade trcli\n"
        f"   Release notes: https://github.com/gurock/trcli/releases\n"
    )
