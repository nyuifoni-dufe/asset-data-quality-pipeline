# Asset Data Quality Validator

A command-line Python application that checks CSV-based IT asset inventory records for data quality problems, separates passing and failing records, and generates an easy-to-review validation report.

## Features

- Checks required asset fields for missing or blank values.
- Flags duplicate asset IDs and serial numbers (including every record involved in a duplicate).
- Validates supported asset types and statuses.
- Checks purchase dates, including invalid dates and dates in the future.
- Rejects nonnumeric or negative purchase costs.
- Exports valid and invalid asset records to separate CSV files.
- Produces a JSON report with record counts, pass rate, issue counts, and details per issue.
- Returns a nonzero exit code when records fail validation, useful for automated workflows.

## Technologies

- Python 3 (standard library only)
- CSV for input and record-level exports
- JSON for the summary and detailed issue report
- VS Code or any terminal for execution

No third-party Python packages are required.

## Project Structure

```text
AssetsV/
├── validator.py
├── assets.csv
├── README.md
└── reports/                     # Created when the script runs
    ├── validation_report.json
    ├── valid_assets.csv
    └── invalid_assets.csv
```

## Input CSV Format

The file `assets.csv` must contain these column names:

| Column | Description | Rule |
| --- | --- | --- |
| `asset_id` | Unique asset identifier | Required; must be unique |
| `asset_name` | Asset description or name | Required |
| `asset_type` | Type of equipment | Required; allowed values below |
| `owner` | Person responsible for the asset | Required |
| `purchase_date` | Date the asset was purchased | Required; valid date; not in the future |
| `purchase_cost` | Purchase amount | Required; numeric; nonnegative |
| `status` | Current asset status | Required; allowed values below |
| `serial_number` | Unique equipment serial number | Required; must be unique |

Supported asset types: `Laptop`, `Printer`, `Network`, `Monitor`, `Server`, `Desktop`.

Supported statuses: `Active`, `Inactive`, `Maintenance`, `Retired`.

The updated date validation logic accepts `YYYY-MM-DD`, `M/D/YYYY` (including zero-padded dates), and `MM-DD-YYYY`. These are accepted **input formats**; date strings are not automatically standardized in the exported CSV files.

Example:

```csv
asset_id,asset_name,asset_type,owner,purchase_date,purchase_cost,status,serial_number
A001,Dell Laptop,Laptop,John,2025-01-10,1200,Active,SN1001
A002,HP Printer,Printer,Sarah,4/10/2025,450,Active,SN1002
```

**Important:** Place the header on the first nonblank line. A leading blank line caused a CSV header detection error during development.

## How to Run

1. Open the `AssetsV` folder in VS Code.
2. Open **Terminal → New Terminal**.
3. Confirm that `validator.py` and `assets.csv` are in the folder.
4. Run:

   ```powershell
   python validator.py assets.csv
   ```

   If your environment uses the Windows Python launcher, run:

   ```powershell
   py validator.py assets.csv
   ```

5. To choose a different report directory:

   ```powershell
   python validator.py assets.csv --output quality_reports
   ```

The default report directory is `reports/`, created automatically if needed. Reports are overwritten on subsequent runs using the same output directory.

## Validation Rules

| Check | Example problem | Issue code |
| --- | --- | --- |
| Required field | Missing owner | `MISSING_REQUIRED` |
| Asset ID uniqueness | Same `asset_id` on multiple records | `DUPLICATE_ASSET_ID` |
| Serial uniqueness | Same serial on multiple records | `DUPLICATE_SERIAL` |
| Asset type | Unsupported type | `INVALID_TYPE` |
| Asset status | `Unknown` | `INVALID_STATUS` |
| Date parsing | `invalid-date` | `INVALID_DATE` |
| Date range | Purchase date after today | `FUTURE_DATE` |
| Cost type | `not-a-number` | `INVALID_COST` |
| Cost range | `-150` | `NEGATIVE_COST` |

One record may contain multiple issues. The report's **total issues** can therefore exceed its **invalid records** count.

## Output Files

### `reports/validation_report.json`

Contains the generation timestamp, source filename, summary metrics, issue totals by type, and a detailed list of issues with asset IDs and source line numbers.

### `reports/valid_assets.csv`

Contains only records that passed all validation checks.

### `reports/invalid_assets.csv`

Contains failing records plus a `source_line` column and a `validation_errors` column explaining what went wrong.

## Sample Results

For the eight-record test dataset used during development, the successful run produced:

```text
========== ASSET DATA QUALITY REPORT ==========
Total records   : 8
Valid records   : 1
Invalid records : 7
Validation rate : 12.5%
Total issues    : 8

Issues by type:
  DUPLICATE_SERIAL: 2
  DUPLICATE_ASSET_ID: 2
  MISSING_REQUIRED: 1
  NEGATIVE_COST: 1
  INVALID_DATE: 1
  INVALID_STATUS: 1
```

These are deliberate data quality failures in the sample records, not evidence that the validator failed to run.

## Troubleshooting

**`ValueError: CSV file has no header.`**

Make sure `assets.csv` contains a header row and does not begin with a blank line. Inspect the file in PowerShell:

```powershell
Get-Content .\assets.csv
```

**Every purchase date is flagged as invalid.**

Check the actual source formats. The original sample included date values in `M/D/YYYY`; use the updated multi-format date parser rather than a strict `YYYY-MM-DD` parser.

**The terminal shows an error or nonzero exit status even though reports were created.**

The script intentionally exits with status code `1` if any records failed validation, allowing an automated pipeline to detect dirty input. It exits with `0` when every record passes.

**Need to find an individual error?**

Open `reports/invalid_assets.csv` or run:

```powershell
Import-Csv .\reports\invalid_assets.csv | Format-Table -AutoSize
```

## Future Enhancements

- Load validated assets into SQL Server or Azure SQL Database.
- Store invalid records in a quarantine table for correction and reprocessing.
- Normalize purchase dates to a single output format.
- Calculate completeness, uniqueness, and validity quality scores.
- Generate an HTML dashboard and integrate validation into Azure Data Factory or Databricks pipelines.

## Project Goal

Demonstrate a practical data engineering quality-control step: ingest asset inventory data, apply repeatable validation rules, isolate unreliable records, and produce traceable quality metrics before downstream processing.
