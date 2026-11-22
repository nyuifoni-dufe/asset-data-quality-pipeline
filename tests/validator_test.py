
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

# Allow imports from the project root.
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1])
)

from validator import validate_assets


FIELDS = [
    "asset_id",
    "asset_name",
    "asset_type",
    "owner",
    "purchase_date",
    "purchase_cost",
    "status",
    "serial_number",
]


@pytest.fixture
def sample_asset():
    """Return a valid asset record."""
    return {
        "asset_id": "A001",
        "asset_name": "Dell Laptop",
        "asset_type": "Laptop",
        "owner": "John",
        "purchase_date": "2025-01-10",
        "purchase_cost": "1200",
        "status": "Active",
        "serial_number": "SN1001",
    }


@pytest.fixture
def run_validation(tmp_path):
    """Create a temporary CSV and validate its records."""

    def _run(records):
        csv_path = tmp_path / "test_assets.csv"

        with csv_path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=FIELDS
            )
            writer.writeheader()
            writer.writerows(records)

        return validate_assets(csv_path)

    return _run


def issue_codes(invalid_records):
    """Collect validation error codes."""
    return [
        issue["code"]
        for record in invalid_records
        for issue in record["issues"]
    ]


def test_valid_asset(sample_asset, run_validation):
    """A valid asset should pass validation."""

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert report["summary"]["total_records"] == 1
    assert report["summary"]["valid_records"] == 1
    assert report["summary"]["invalid_records"] == 0
    assert report["summary"]["validation_rate"] == 100.0
    assert len(valid) == 1
    assert len(invalid) == 0


def test_missing_owner(sample_asset, run_validation):
    """Missing required values should be rejected."""

    sample_asset["owner"] = ""

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert len(valid) == 0
    assert len(invalid) == 1
    assert "MISSING_REQUIRED" in issue_codes(invalid)


def test_duplicate_asset_id(
    sample_asset, run_validation
):
    """Duplicate asset IDs should be detected."""

    second = sample_asset.copy()
    second["serial_number"] = "SN1002"

    report, valid, invalid = run_validation(
        [sample_asset, second]
    )

    assert len(invalid) == 2
    assert issue_codes(invalid).count(
        "DUPLICATE_ASSET_ID"
    ) == 2


def test_duplicate_serial_number(
    sample_asset, run_validation
):
    """Duplicate serial numbers should be detected."""

    second = sample_asset.copy()
    second["asset_id"] = "A002"

    report, valid, invalid = run_validation(
        [sample_asset, second]
    )

    assert len(invalid) == 2
    assert issue_codes(invalid).count(
        "DUPLICATE_SERIAL"
    ) == 2


def test_invalid_date(sample_asset, run_validation):
    """Invalid purchase dates should fail."""

    sample_asset["purchase_date"] = "invalid-date"

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert "INVALID_DATE" in issue_codes(invalid)


@pytest.mark.parametrize(
    "purchase_date",
    ["2025-04-10", "4/10/2025", "04-10-2025"]
)
def test_supported_date_formats(
    sample_asset, run_validation, purchase_date
):
    """Supported date formats should pass."""

    sample_asset["purchase_date"] = purchase_date

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert report["summary"]["valid_records"] == 1
    assert len(invalid) == 0


def test_future_date(sample_asset, run_validation):
    """Future purchase dates should be rejected."""

    future_date = date.today() + timedelta(days=30)

    sample_asset["purchase_date"] = (
        future_date.isoformat()
    )

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert "FUTURE_DATE" in issue_codes(invalid)


def test_negative_cost(sample_asset, run_validation):
    """Negative purchase costs should be rejected."""

    sample_asset["purchase_cost"] = "-500"

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert "NEGATIVE_COST" in issue_codes(invalid)


def test_non_numeric_cost(
    sample_asset, run_validation
):
    """Nonnumeric purchase costs should be rejected."""

    sample_asset["purchase_cost"] = "abc"

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert "INVALID_COST" in issue_codes(invalid)


def test_invalid_status(sample_asset, run_validation):
    """Unsupported asset statuses should be rejected."""

    sample_asset["status"] = "Unknown"

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert "INVALID_STATUS" in issue_codes(invalid)


def test_invalid_asset_type(
    sample_asset, run_validation
):
    """Unsupported asset types should be rejected."""

    sample_asset["asset_type"] = "Spaceship"

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    assert "INVALID_TYPE" in issue_codes(invalid)


def test_missing_csv_columns(tmp_path):
    """CSV files missing required columns should fail."""

    csv_path = tmp_path / "missing_columns.csv"

    csv_path.write_text(
        "asset_id,asset_name\nA001,Dell Laptop\n",
        encoding="utf-8"
    )

    with pytest.raises(
        ValueError, match="Missing CSV columns"
    ):
        validate_assets(csv_path)


def test_empty_csv(tmp_path):
    """An empty CSV should raise a header error."""

    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError, match="CSV file has no header"
    ):
        validate_assets(csv_path)


def test_multiple_validation_errors(
    sample_asset, run_validation
):
    """A single asset can contain multiple issues."""

    sample_asset["owner"] = ""
    sample_asset["purchase_cost"] = "-100"
    sample_asset["status"] = "Unknown"

    report, valid, invalid = run_validation(
        [sample_asset]
    )

    codes = issue_codes(invalid)

    assert "MISSING_REQUIRED" in codes
    assert "NEGATIVE_COST" in codes
    assert "INVALID_STATUS" in codes
    assert report["summary"]["total_issues"] == 3
