"""
Data Cleaning and Normalization Layer
Handles messy, inconsistent data from Monday.com boards.
Returns cleaned data alongside a data quality report.
"""

import re
import logging
from datetime import datetime
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Date Normalization
# ---------------------------------------------------------------------------

def normalize_date(value: str) -> str | None:
    """
    Normalize a date value from various formats to ISO format (YYYY-MM-DD).
    Handles: DD/MM/YYYY, MM-DD-YYYY, YYYY-MM-DD, text like "26th Feb 2026",
    or empty/None values.

    Returns ISO date string or None if unparseable.
    """
    if not value or not str(value).strip():
        return None

    value = str(value).strip()

    # Already ISO format from Monday.com
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value

    # Try common explicit formats first (order matters)
    formats = [
        "%Y-%m-%d",           # 2026-02-27
        "%d/%m/%Y",           # 27/02/2026
        "%m/%d/%Y",           # 02/27/2026
        "%d-%m-%Y",           # 27-02-2026
        "%m-%d-%Y",           # 02-27-2026
        "%d %b %Y",           # 27 Feb 2026
        "%d %B %Y",           # 27 February 2026
        "%b %d, %Y",          # Feb 27, 2026
        "%B %d, %Y",          # February 27, 2026
        "%d/%m/%y",           # 27/02/26
        "%m/%d/%y",           # 02/27/26
    ]

    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th, etc.)
    cleaned = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", value, flags=re.IGNORECASE)

    for fmt in formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback to dateutil fuzzy parser
    try:
        parsed = date_parser.parse(cleaned, fuzzy=True, dayfirst=True)
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        logger.warning(f"Could not parse date: '{value}'")
        return None


# ---------------------------------------------------------------------------
# Currency / Number Normalization
# ---------------------------------------------------------------------------

def normalize_currency(value: str) -> float | None:
    """
    Normalize currency/number values to float.
    Handles: "$1,200", "1200.00", "1.2K", "₹1,200", "1.5M", "1.2Cr",
    empty strings, None.

    Returns float or None for unparseable values.
    """
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[₹$€£,\s]", "", value)

    if not cleaned:
        return None

    # Handle K/M/Cr/L suffixes
    multiplier = 1
    suffix_match = re.match(r"^(-?\d+\.?\d*)\s*(K|M|B|Cr|L|Lakh|Lakhs|Crore|Crores)$",
                            cleaned, re.IGNORECASE)
    if suffix_match:
        cleaned = suffix_match.group(1)
        suffix = suffix_match.group(2).upper()
        multipliers = {
            "K": 1_000,
            "M": 1_000_000,
            "B": 1_000_000_000,
            "CR": 10_000_000,
            "CRORE": 10_000_000,
            "CRORES": 10_000_000,
            "L": 100_000,
            "LAKH": 100_000,
            "LAKHS": 100_000,
        }
        multiplier = multipliers.get(suffix, 1)

    try:
        return float(cleaned) * multiplier
    except ValueError:
        logger.warning(f"Could not parse currency/number: '{value}'")
        return None


# ---------------------------------------------------------------------------
# Text Normalization
# ---------------------------------------------------------------------------

def normalize_text(value: str) -> str | None:
    """
    Normalize text values: strip whitespace, standardize casing.
    Handles inconsistent casing like "energy", "Energy", "ENERGY".

    Returns title-cased, trimmed string or None for empty values.
    """
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    # Collapse multiple spaces
    value = re.sub(r"\s+", " ", value)

    # Title case for general text
    return value.strip().title()


# ---------------------------------------------------------------------------
# Status Normalization
# ---------------------------------------------------------------------------

# Canonical status mappings — maps lowercase variants to canonical forms
STATUS_MAPPINGS = {
    # Deal statuses
    "open": "Open",
    "closed": "Closed",
    "closed won": "Closed Won",
    "closed lost": "Closed Lost",
    "closedwon": "Closed Won",
    "closedlost": "Closed Lost",
    "won": "Closed Won",
    "lost": "Closed Lost",

    # Execution statuses
    "not started": "Not Started",
    "notstarted": "Not Started",
    "in progress": "In Progress",
    "inprogress": "In Progress",
    "in_progress": "In Progress",
    "wip": "In Progress",
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "executed until current month": "Executed Until Current Month",

    # Billing statuses
    "partially billed": "Partially Billed",
    "fully billed": "Fully Billed",
    "not billed": "Not Billed",
    "update required": "Update Required",

    # Closure probability
    "high": "High",
    "medium": "Medium",
    "low": "Low",
    "very high": "Very High",
    "very low": "Very Low",

    # Invoice status
    "pending": "Pending",
    "paid": "Paid",
    "overdue": "Overdue",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}


def normalize_status(value: str) -> str | None:
    """
    Normalize status values using canonical mappings.
    Maps common variants to standard labels.

    Returns canonical status string or original title-cased value if no mapping found.
    """
    if value is None:
        return None

    value = str(value).strip()
    if not value:
        return None

    # Look up in canonical mapping
    lookup = value.lower().strip()
    if lookup in STATUS_MAPPINGS:
        return STATUS_MAPPINGS[lookup]

    # If not in mapping, return title-cased original
    return value.strip().title()


# ---------------------------------------------------------------------------
# Column type classification (heuristic)
# ---------------------------------------------------------------------------

# Columns known to contain date values
DATE_COLUMNS = {
    "close date (a)", "tentative close date", "created date",
    "data delivery date", "date of po/loi", "probable start date",
    "probable end date", "last invoice date", "collection date",
}

# Columns known to contain numeric/currency values
NUMERIC_COLUMNS = {
    "masked deal value",
    "amount in rupees (excl of gst) (masked)",
    "amount in rupees (incl of gst) (masked)",
    "billed value in rupees (excl of gst.) (masked)",
    "billed value in rupees (incl of gst.) (masked)",
    "collected amount in rupees (incl of gst.) (masked)",
    "amount to be billed in rs. (exl. of gst) (masked)",
    "amount to be billed in rs. (incl. of gst) (masked)",
    "amount receivable (masked)",
    "quantity by ops", "quantity billed (till date)",
    "balance in quantity",
}

# Columns known to contain status values
STATUS_COLUMNS = {
    "deal status", "deal stage", "closure probability",
    "execution status", "billing status", "invoice status",
    "wo status (billed)", "collection status",
    "nature of work", "document type", "type of work",
    "ar priority account", "product deal",
    "actual billing month", "owner code",
    "bd/kam personnel code",
    "is any skylark software platform part of the client deliverables in this deal?",
    "last executed month of recurring project",
}

# Columns to normalize as general text (sector, names, etc.)
TEXT_COLUMNS = {
    "sector/service", "sector",
    "expected billing month", "actual collection month",
}


# ---------------------------------------------------------------------------
# Master cleaning function
# ---------------------------------------------------------------------------

def clean_board_data(items: list[dict]) -> tuple[list[dict], dict]:
    """
    Apply all normalizations across all fields in board data.

    Args:
        items: Raw list of item dicts from monday_client.get_all_items()

    Returns:
        (cleaned_items, quality_report) where quality_report summarizes
        data quality issues found during cleaning.
    """
    quality_report = {
        "total_items": len(items),
        "missing_values": 0,
        "unparseable_dates": 0,
        "unparseable_numbers": 0,
        "normalized_statuses": 0,
        "normalized_text": 0,
        "issues": [],
    }

    cleaned_items = []

    for item in items:
        cleaned_item = {
            "id": item.get("id"),
            "name": item.get("name"),
            "group": item.get("group", {}),
            "columns": {},
        }

        for col_title, raw_value in item.get("columns", {}).items():
            col_key = col_title.lower().strip()

            if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
                quality_report["missing_values"] += 1
                cleaned_item["columns"][col_title] = None
                continue

            # Apply appropriate normalization based on column type
            if col_key in DATE_COLUMNS:
                normalized = normalize_date(raw_value)
                if normalized is None and raw_value:
                    quality_report["unparseable_dates"] += 1
                    quality_report["issues"].append(
                        f"Unparseable date in '{col_title}' for item '{item.get('name', 'unknown')}': '{raw_value}'"
                    )
                cleaned_item["columns"][col_title] = normalized

            elif col_key in NUMERIC_COLUMNS:
                normalized = normalize_currency(raw_value)
                if normalized is None and raw_value:
                    quality_report["unparseable_numbers"] += 1
                    quality_report["issues"].append(
                        f"Unparseable number in '{col_title}' for item '{item.get('name', 'unknown')}': '{raw_value}'"
                    )
                cleaned_item["columns"][col_title] = normalized

            elif col_key in STATUS_COLUMNS:
                normalized = normalize_status(raw_value)
                if normalized != raw_value:
                    quality_report["normalized_statuses"] += 1
                cleaned_item["columns"][col_title] = normalized

            elif col_key in TEXT_COLUMNS:
                normalized = normalize_text(raw_value)
                if normalized != raw_value:
                    quality_report["normalized_text"] += 1
                cleaned_item["columns"][col_title] = normalized

            else:
                # Keep as-is for unclassified columns
                cleaned_item["columns"][col_title] = raw_value

        cleaned_items.append(cleaned_item)

    # Cap the issues list to avoid huge payloads
    if len(quality_report["issues"]) > 20:
        total = len(quality_report["issues"])
        quality_report["issues"] = quality_report["issues"][:20]
        quality_report["issues"].append(f"... and {total - 20} more issues")

    # Summary line
    total_issues = (
        quality_report["missing_values"]
        + quality_report["unparseable_dates"]
        + quality_report["unparseable_numbers"]
    )
    quality_report["summary"] = (
        f"{total_issues} data quality issues found across {quality_report['total_items']} items: "
        f"{quality_report['missing_values']} missing values, "
        f"{quality_report['unparseable_dates']} unparseable dates, "
        f"{quality_report['unparseable_numbers']} unparseable numbers."
    )

    return cleaned_items, quality_report
