"""
Unit tests for version_checker module.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from requests.exceptions import Timeout, ConnectionError, HTTPError

from trcli import version_checker
from trcli.version_checker import (
    check_for_updates,
    _query_pypi,
    _get_cache,
    _save_cache,
    _is_cache_valid,
    _compare_and_format,
    _format_message,
    PYPI_API_URL,
    VERSION_CHECK_INTERVAL,
)


@pytest.fixture
def mock_cache_dir(tmp_path):
    """Create a temporary cache directory for testing."""
    cache_dir = tmp_path / ".trcli"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_cache_file(mock_cache_dir):
    """Create a temporary cache file path."""
    return mock_cache_dir / "version_cache.json"


@pytest.fixture(autouse=True)
def patch_cache_paths(mock_cache_dir, mock_cache_file):
    """Automatically patch cache paths for all tests."""
    with patch.object(version_checker, "VERSION_CACHE_DIR", mock_cache_dir), patch.object(
        version_checker, "VERSION_CACHE_FILE", mock_cache_file
    ):
        yield


class TestQueryPyPI:
    """Tests for _query_pypi function."""

    def test_query_pypi_success(self, requests_mock):
        """Test successful PyPI API query."""
        mock_response = {"info": {"version": "1.14.0", "name": "trcli"}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        result = _query_pypi()

        assert result == "1.14.0"

    def test_query_pypi_timeout(self, requests_mock):
        """Test PyPI query with timeout."""
        requests_mock.get(PYPI_API_URL, exc=Timeout)

        result = _query_pypi()

        assert result is None

    def test_query_pypi_connection_error(self, requests_mock):
        """Test PyPI query with connection error."""
        requests_mock.get(PYPI_API_URL, exc=ConnectionError)

        result = _query_pypi()

        assert result is None

    def test_query_pypi_http_error(self, requests_mock):
        """Test PyPI query with HTTP error response."""
        requests_mock.get(PYPI_API_URL, status_code=500)

        result = _query_pypi()

        assert result is None

    def test_query_pypi_invalid_json(self, requests_mock):
        """Test PyPI query with invalid JSON response."""
        requests_mock.get(PYPI_API_URL, text="not json", status_code=200)

        result = _query_pypi()

        assert result is None

    def test_query_pypi_missing_version(self, requests_mock):
        """Test PyPI query when version field is missing."""
        mock_response = {
            "info": {
                "name": "trcli"
                # version field missing
            }
        }
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        result = _query_pypi()

        assert result is None

    def test_query_pypi_empty_info(self, requests_mock):
        """Test PyPI query when info section is empty."""
        mock_response = {"info": {}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        result = _query_pypi()

        assert result is None


class TestCacheManagement:
    """Tests for cache read/write functions."""

    def test_get_cache_empty(self, mock_cache_file):
        """Test reading cache when file doesn't exist."""
        result = _get_cache()

        assert result == {}

    def test_get_cache_valid(self, mock_cache_file):
        """Test reading valid cache file."""
        cache_data = {"last_check": "2026-02-20T10:00:00", "latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        result = _get_cache()

        assert result == cache_data

    def test_get_cache_invalid_json(self, mock_cache_file):
        """Test reading cache with invalid JSON."""
        mock_cache_file.write_text("not json")

        result = _get_cache()

        assert result == {}

    def test_save_cache_success(self, mock_cache_file):
        """Test saving cache successfully."""
        cache_data = {"last_check": "2026-02-20T10:00:00", "latest_version": "1.14.0"}

        _save_cache(cache_data)

        assert mock_cache_file.exists()
        saved_data = json.loads(mock_cache_file.read_text())
        assert saved_data == cache_data

    def test_save_cache_creates_directory(self, tmp_path):
        """Test that save_cache creates directory if it doesn't exist."""
        new_cache_dir = tmp_path / "new_dir" / ".trcli"
        new_cache_file = new_cache_dir / "version_cache.json"

        with patch.object(version_checker, "VERSION_CACHE_DIR", new_cache_dir), patch.object(
            version_checker, "VERSION_CACHE_FILE", new_cache_file
        ):
            cache_data = {"test": "data"}
            _save_cache(cache_data)

            assert new_cache_file.exists()
            assert json.loads(new_cache_file.read_text()) == cache_data

    def test_save_cache_permission_error(self, mock_cache_file):
        """Test save_cache handles permission errors gracefully."""
        cache_data = {"test": "data"}

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # Should not raise exception
            _save_cache(cache_data)


class TestCacheValidation:
    """Tests for _is_cache_valid function."""

    def test_is_cache_valid_no_file(self, mock_cache_file):
        """Test cache validation when file doesn't exist."""
        result = _is_cache_valid()

        assert result is False

    def test_is_cache_valid_empty_cache(self, mock_cache_file):
        """Test cache validation with empty cache data."""
        mock_cache_file.write_text("{}")

        result = _is_cache_valid()

        assert result is False

    def test_is_cache_valid_missing_last_check(self, mock_cache_file):
        """Test cache validation when last_check is missing."""
        cache_data = {"latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        result = _is_cache_valid()

        assert result is False

    def test_is_cache_valid_fresh_cache(self, mock_cache_file):
        """Test cache validation with fresh cache (within 24 hours)."""
        now = datetime.now()
        cache_data = {"last_check": now.isoformat(), "latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        result = _is_cache_valid()

        assert result is True

    def test_is_cache_valid_expired_cache(self, mock_cache_file):
        """Test cache validation with expired cache (over 24 hours old)."""
        old_time = datetime.now() - timedelta(seconds=VERSION_CHECK_INTERVAL + 3600)
        cache_data = {"last_check": old_time.isoformat(), "latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        result = _is_cache_valid()

        assert result is False

    def test_is_cache_valid_invalid_datetime_format(self, mock_cache_file):
        """Test cache validation with invalid datetime format."""
        cache_data = {"last_check": "not a datetime", "latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        result = _is_cache_valid()

        assert result is False


class TestVersionComparison:
    """Tests for version comparison and formatting functions."""

    def test_compare_and_format_newer_version(self):
        """Test comparison when newer version is available."""
        result = _compare_and_format("1.13.1", "1.14.0")

        assert result is not None
        assert "1.13.1" in result
        assert "1.14.0" in result
        assert "pip install --upgrade trcli" in result

    def test_compare_and_format_same_version(self):
        """Test comparison when versions are the same."""
        result = _compare_and_format("1.13.1", "1.13.1")

        assert result is None

    def test_compare_and_format_older_version(self):
        """Test comparison when current version is newer (development version)."""
        result = _compare_and_format("1.14.0", "1.13.1")

        assert result is None

    def test_compare_and_format_major_version_update(self):
        """Test comparison with major version update."""
        result = _compare_and_format("1.13.1", "2.0.0")

        assert result is not None
        assert "1.13.1" in result
        assert "2.0.0" in result

    def test_compare_and_format_invalid_version_format(self):
        """Test comparison with invalid version format."""
        result = _compare_and_format("invalid", "1.14.0")

        assert result is None

    def test_format_message(self):
        """Test message formatting."""
        result = _format_message("1.13.1", "1.14.0")

        assert "1.13.1" in result
        assert "1.14.0" in result
        assert "pip install --upgrade trcli" in result
        assert "https://github.com/gurock/trcli/releases" in result


class TestCheckForUpdates:
    """Tests for main check_for_updates function."""

    def test_check_for_updates_with_newer_version(self, requests_mock, mock_cache_file):
        """Test full flow when newer version is available."""
        mock_response = {"info": {"version": "1.14.0"}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        result = check_for_updates("1.13.1")

        assert result is not None
        assert "1.13.1" in result
        assert "1.14.0" in result
        assert mock_cache_file.exists()

    def test_check_for_updates_with_same_version(self, requests_mock, mock_cache_file):
        """Test full flow when version is up to date."""
        mock_response = {"info": {"version": "1.13.1"}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        result = check_for_updates("1.13.1")

        assert result is None

    def test_check_for_updates_uses_cache(self, requests_mock, mock_cache_file):
        """Test that check_for_updates uses cache when valid."""
        # Setup valid cache
        cache_data = {"last_check": datetime.now().isoformat(), "latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        # Should not make API call
        result = check_for_updates("1.13.1")

        assert result is not None
        assert "1.14.0" in result
        assert not requests_mock.called

    def test_check_for_updates_refreshes_expired_cache(self, requests_mock, mock_cache_file):
        """Test that check_for_updates refreshes expired cache."""
        # Setup expired cache
        old_time = datetime.now() - timedelta(seconds=VERSION_CHECK_INTERVAL + 3600)
        cache_data = {"last_check": old_time.isoformat(), "latest_version": "1.14.0"}
        mock_cache_file.write_text(json.dumps(cache_data))

        # Setup API mock
        mock_response = {"info": {"version": "1.15.0"}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        result = check_for_updates("1.13.1")

        assert result is not None
        assert "1.15.0" in result  # Should use new version from API
        assert requests_mock.called

    def test_check_for_updates_handles_api_failure_gracefully(self, requests_mock, mock_cache_file):
        """Test that check_for_updates handles API failures without crashing."""
        requests_mock.get(PYPI_API_URL, exc=Timeout)

        result = check_for_updates("1.13.1")

        assert result is None  # Should fail gracefully

    def test_check_for_updates_without_requests_library(self, mock_cache_file):
        """Test check_for_updates when requests library is not available."""
        with patch.object(version_checker, "requests", None):
            result = check_for_updates("1.13.1")

            assert result is None

    def test_check_for_updates_without_packaging_library(self, mock_cache_file):
        """Test check_for_updates when packaging library is not available."""
        with patch.object(version_checker, "version", None):
            result = check_for_updates("1.13.1")

            assert result is None

    def test_check_for_updates_uses_default_version(self, requests_mock, mock_cache_file):
        """Test check_for_updates uses __version__ when no version provided."""
        mock_response = {"info": {"version": "1.14.0"}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        with patch("trcli.version_checker.__version__", "1.13.1"):
            result = check_for_updates()  # No version parameter

            assert result is not None
            assert "1.13.1" in result

    def test_check_for_updates_exception_handling(self, requests_mock, mock_cache_file):
        """Test that any unexpected exception is caught and logged."""
        # Setup cache that will cause exception during processing
        mock_cache_file.write_text("invalid json")

        mock_response = {"info": {"version": "1.14.0"}}
        requests_mock.get(PYPI_API_URL, json=mock_response, status_code=200)

        # Should not raise exception
        result = check_for_updates("1.13.1")

        # With invalid cache, should fall back to API call
        assert result is not None
