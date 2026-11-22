import argparse
import csv
import json
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_FIELDS = [
    "asset_id",
    "asset_name",
    "asset_type",
    "owner",
    "purchase_date",
    "purchase_cost",
    "status",
    "serial_number",
]

VALID_TYPES = {
    "Laptop", "Printer", "Network",
    "Monitor", "Server", "Desktop"
}

VALID_STATUSES = {
    "Active", "Inactive", "Maintenance", "Retired"
}

def validate_assets(input_path):
    # Reading asset records
    with open(input_path, "r", encoding="utf-8-sig",
              newline="") as file:

        print("Reading file:", input_path)

        reader = csv.DictReader(file)

        print("Detected columns:", reader.fieldnames)

        if not reader.fieldnames:
            raise ValueError("CSV file has no header.")

        missing = set(REQUIRED_FIELDS) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing CSV columns: {sorted(missing)}"
            )

        # Preserve original CSV line numbers
        records = []
        for row in reader:
            line = reader.line_num
            if None in row:
                raise ValueError(
                    f"Extra columns detected near line {line}"
                )
            records.append((line, row))

    today = date.today()

    # Count identifiers for duplicate detection
    id_counts = Counter(
        (row["asset_id"] or "").strip()
        for _, row in records
        if (row["asset_id"] or "").strip()
    )

    serial_counts = Counter(
        (row["serial_number"] or "").strip().upper()
        for _, row in records
        if (row["serial_number"] or "").strip()
    )

    valid_records = []
    invalid_records = []
    all_issues = []

    for line, row in records:
        issues = []

        # 1. Required fields
        for field in REQUIRED_FIELDS:
            if not (row[field] or "").strip():
                issues.append({
                    "field": field,
                    "code": "MISSING_REQUIRED",
                    "message": f"{field} is required"
                })

        asset_id = (row["asset_id"] or "").strip()
        serial = (row["serial_number"] or "").strip()
        asset_type = (row["asset_type"] or "").strip()
        status = (row["status"] or "").strip()
        purchase_date = (row["purchase_date"] or "").strip()
        purchase_cost = (row["purchase_cost"] or "").strip()

        # 2. Duplicate asset IDs
        if asset_id and id_counts[asset_id] > 1:
            issues.append({
                "field": "asset_id",
                "code": "DUPLICATE_ASSET_ID",
                "message": f"Duplicate asset ID: {asset_id}"
            })

        # 3. Duplicate serial numbers
        if serial and serial_counts[serial.upper()] > 1:
            issues.append({
                "field": "serial_number",
                "code": "DUPLICATE_SERIAL",
                "message": f"Duplicate serial number: {serial}"
            })

        # 4. Allowed asset types
        if asset_type and asset_type not in VALID_TYPES:
            issues.append({
                "field": "asset_type",
                "code": "INVALID_TYPE",
                "message": f"Unsupported asset type: {asset_type}"
            })

        # 5. Allowed statuses
        if status and status not in VALID_STATUSES:
            issues.append({
                "field": "status",
                "code": "INVALID_STATUS",
                "message": f"Unsupported status: {status}"
            })
            print(f"Asset: {asset_id}, Purchase Date: {repr(purchase_date)}")

        # 6. Purchase date validation
        if purchase_date:

            date_formats = [
                "%Y-%m-%d",  # 2025-04-10
                "%m/%d/%Y",  # 4/10/2025
                "%m-%d-%Y",  # 04-10-2025
            ]

            parsed_date = None

            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(
                        purchase_date.strip(), fmt
                    ).date()
                    break
                except ValueError:
                    continue

            if parsed_date is None:
                issues.append({
                    "field": "purchase_date",
                    "code": "INVALID_DATE",
                    "message": f"Invalid purchase date: {purchase_date}"
                })

            elif parsed_date > date.today():
                issues.append({
                    "field": "purchase_date",
                    "code": "FUTURE_DATE",
                    "message": "Purchase date is in the future"
                })

        # 7. Purchase cost
        if purchase_cost:
            try:
                cost = Decimal(purchase_cost)

                if not cost.is_finite():
                    raise InvalidOperation

                if cost < 0:
                    issues.append({
                        "field": "purchase_cost",
                        "code": "NEGATIVE_COST",
                        "message": "Purchase cost cannot be negative"
                    })
            except InvalidOperation:
                issues.append({
                    "field": "purchase_cost",
                    "code": "INVALID_COST",
                    "message": "Purchase cost must be numeric"
                })

        if issues:
            invalid_records.append({
                "line": line,
                "record": row,
                "issues": issues
            })

            for issue in issues:
                all_issues.append({
                    "line": line,
                    "asset_id": asset_id,
                    **issue
                })
        else:
            valid_records.append(row)

    total = len(records)
    failed = len(invalid_records)
    passed = len(valid_records)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_path),
        "summary": {
            "total_records": total,
            "valid_records": passed,
            "invalid_records": failed,
            "validation_rate": round(
                passed / total * 100, 2
            ) if total else 0.0,
            "total_issues": len(all_issues),
            "issues_by_type": dict(Counter(
                item["code"] for item in all_issues
            ))
        },
        "issues": all_issues
    }

    return report, valid_records, invalid_records


def save_csv(path, rows, fieldnames):
    with open(path, "w", encoding="utf-8",
              newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Validate asset inventory data"
    )
    parser.add_argument(
        "input_file",
        help="Path to asset CSV file"
    )
    parser.add_argument(
        "--output",
        default="reports",
        help="Output directory"
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    report, valid, invalid = validate_assets(args.input_file)

    # JSON quality report
    report_file = output_dir / "validation_report.json"
    report_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    # Valid asset records
    save_csv(
        output_dir / "valid_assets.csv",
        valid,
        REQUIRED_FIELDS
    )

    # Invalid asset records with issue descriptions
    invalid_rows = []
    for entry in invalid:
        row = dict(entry["record"])
        row["source_line"] = entry["line"]
        row["validation_errors"] = " | ".join(
            issue["message"] for issue in entry["issues"]
        )
        invalid_rows.append(row)

    save_csv(
        output_dir / "invalid_assets.csv",
        invalid_rows,
        REQUIRED_FIELDS + ["source_line", "validation_errors"]
    )

    summary = report["summary"]

    print("\n========== ASSET DATA QUALITY REPORT ==========")
    print(f"Total records   : {summary['total_records']}")
    print(f"Valid records   : {summary['valid_records']}")
    print(f"Invalid records : {summary['invalid_records']}")
    print(f"Validation rate : {summary['validation_rate']}%")
    print(f"Total issues    : {summary['total_issues']}")

    print("\nIssues by type:")
    for code, count in summary["issues_by_type"].items():
        print(f"  {code}: {count}")

    print(f"\nReports saved in: {output_dir.resolve()}")

    # Nonzero exit code allows ETL jobs to detect failure
    return 1 if summary["invalid_records"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
