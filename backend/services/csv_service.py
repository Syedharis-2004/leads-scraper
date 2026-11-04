"""
CSV storage service.

Responsibilities:
  * Create leads.csv automatically if it doesn't exist.
  * Append new leads while preventing duplicates (by website + email).
  * Use file locking for concurrent-safe access.
  * Atomic writes: write to a temp file, then rename (no partial writes).
  * Read leads with search, filter, sort, and pagination.
  * Delete individual leads.
  * Export to CSV / JSON.
"""

import csv
import io
import os
import uuid
from datetime import datetime
from typing import Iterator

from filelock import FileLock

from config.settings import CSV_COLUMNS, LEADS_CSV_PATH, ensure_dirs
from utils.logging_config import logger


# Lock file sits next to the CSV so it is co-located.
_LOCK_PATH = str(LEADS_CSV_PATH) + ".lock"


def _get_lock() -> FileLock:
    return FileLock(_LOCK_PATH, timeout=30)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def init_csv() -> None:
    """Create the CSV file with headers if it doesn't exist."""
    ensure_dirs()
    if LEADS_CSV_PATH.exists():
        return
    with _get_lock():
        with open(LEADS_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
    logger.info(f"Created CSV file: {LEADS_CSV_PATH}")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def _row_to_dict(row: dict) -> dict:
    """Normalise a CSV row dict (strip whitespace, ensure all columns)."""
    return {col: (row.get(col, "") or "").strip() for col in CSV_COLUMNS}


def read_all_leads() -> list[dict]:
    """Return every lead as a list of dicts.  Thread-safe."""
    init_csv()
    leads: list[dict] = []
    with _get_lock():
        with open(LEADS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(_row_to_dict(row))
    return leads


def read_lead(lead_id: str) -> dict | None:
    """Return a single lead by id, or None."""
    for lead in read_all_leads():
        if lead["lead_id"] == lead_id:
            return lead
    return None


def count_leads() -> int:
    """Return the total number of leads (excluding header)."""
    return len(read_all_leads())


def count_leads_today() -> int:
    """Return number of leads generated today."""
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1
        for lead in read_all_leads()
        if lead.get("generated_at", "").startswith(today)
    )


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------
def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _dedup_key(lead: dict) -> tuple[str, str]:
    """
    Return a (website, email) key used for deduplication.
    Both are normalised to lower-case.
    """
    website = _normalize(lead.get("website", ""))
    email = _normalize(lead.get("email", ""))
    # Normalise website to strip protocol / www for comparison
    if website:
        website = website.replace("https://", "").replace("http://", "")
        if website.startswith("www."):
            website = website[4:]
        website = website.rstrip("/")
    return (website, email)


def get_existing_keys() -> set[tuple[str, str]]:
    """Return a set of all existing dedup keys."""
    keys: set[tuple[str, str]] = set()
    for lead in read_all_leads():
        keys.add(_dedup_key(lead))
    return keys


def is_duplicate(lead: dict, existing_keys: set[tuple[str, str]] | None = None) -> bool:
    """Check if *lead* is a duplicate of an existing record."""
    if existing_keys is None:
        existing_keys = get_existing_keys()
    key = _dedup_key(lead)
    # If both website and email are empty, it's not a meaningful dup
    if key == ("", ""):
        return False
    return key in existing_keys


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _new_lead_id() -> str:
    """Generate a unique lead ID."""
    return f"LD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def append_leads(
    new_leads: list[dict],
    search_query: str = "",
    existing_keys: set[tuple[str, str]] | None = None,
) -> tuple[list[dict], int]:
    """
    Append *new_leads* to the CSV, skipping duplicates.

    Returns ``(added, skipped_count)`` where *added* is the list of
    lead dicts that were actually written (with lead_id and generated_at
    filled in).
    """
    init_csv()
    if existing_keys is None:
        existing_keys = get_existing_keys()

    added: list[dict] = []
    skipped = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prepare records
    records_to_write: list[dict] = []
    for raw in new_leads:
        record = {col: str(raw.get(col, "") or "").strip() for col in CSV_COLUMNS}
        # Fill in generated metadata
        record["lead_id"] = record.get("lead_id") or _new_lead_id()
        record["generated_at"] = record.get("generated_at") or now
        record["search_query"] = record.get("search_query") or search_query

        key = _dedup_key(record)
        if key != ("", "") and key in existing_keys:
            skipped += 1
            continue
        existing_keys.add(key)
        records_to_write.append(record)
        added.append(record)

    # Atomic append: write to temp, then replace
    if records_to_write:
        with _get_lock():
            # Read existing content
            with open(LEADS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing = list(reader)
                fieldnames = reader.fieldnames or CSV_COLUMNS

            # Write combined
            tmp_path = str(LEADS_CSV_PATH) + ".tmp"
            with open(tmp_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in existing:
                    writer.writerow(_row_to_dict(row))
                for record in records_to_write:
                    writer.writerow(record)

            # Atomic rename
            os.replace(tmp_path, str(LEADS_CSV_PATH))

    logger.info(f"Appended {len(added)} leads, skipped {skipped} duplicates")
    return added, skipped


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------
def delete_lead(lead_id: str) -> bool:
    """Delete a lead by ID.  Returns True if deleted."""
    init_csv()
    with _get_lock():
        with open(LEADS_CSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or CSV_COLUMNS
            rows = list(reader)

        remaining = [row for row in rows if row.get("lead_id") != lead_id]
        if len(remaining) == len(rows):
            return False  # not found

        tmp_path = str(LEADS_CSV_PATH) + ".tmp"
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in remaining:
                writer.writerow(_row_to_dict(row))

        os.replace(tmp_path, str(LEADS_CSV_PATH))

    logger.info(f"Deleted lead {lead_id}")
    return True


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------
def query_leads(
    search: str = "",
    city: str = "",
    business_type: str = "",
    date_from: str = "",
    date_to: str = "",
    sort_by: str = "generated_at",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    """
    Search, filter, sort, and paginate leads.

    Returns ``(page_leads, total_count)``.
    """
    leads = read_all_leads()

    # Filter
    if search:
        search_lower = search.lower()
        leads = [l for l in leads if search_lower in l.get("company_name", "").lower()]
    if city:
        city_lower = city.lower()
        leads = [l for l in leads if city_lower in l.get("city", "").lower()]
    if business_type:
        bt_lower = business_type.lower()
        leads = [l for l in leads if bt_lower in l.get("business_type", "").lower()]
    if date_from:
        leads = [l for l in leads if l.get("generated_at", "") >= date_from]
    if date_to:
        leads = [l for l in leads if l.get("generated_at", "") <= date_to + " 23:59:59"]

    # Sort
    reverse = sort_order == "desc"
    leads.sort(
        key=lambda l: (l.get(sort_by, "") or "").lower(),
        reverse=reverse,
    )

    total = len(leads)

    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_leads = leads[start:end]

    return page_leads, total


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_csv(search: str = "", city: str = "", business_type: str = "",
               date_from: str = "", date_to: str = "") -> str:
    """Return CSV content as a string (optionally filtered)."""
    leads, _ = query_leads(
        search=search, city=city, business_type=business_type,
        date_from=date_from, date_to=date_to,
        sort_by="generated_at", sort_order="desc",
        page=1, page_size=10_000_000,  # effectively all
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for lead in leads:
        writer.writerow(lead)
    return output.getvalue()


def export_json(search: str = "", city: str = "", business_type: str = "",
                date_from: str = "", date_to: str = "") -> str:
    """Return JSON array of leads (optionally filtered)."""
    import json
    leads, _ = query_leads(
        search=search, city=city, business_type=business_type,
        date_from=date_from, date_to=date_to,
        sort_by="generated_at", sort_order="desc",
        page=1, page_size=10_000_000,
    )
    return json.dumps(leads, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Search history tracking
# ---------------------------------------------------------------------------
def record_search(success: bool) -> None:
    """Record a search attempt in search_history.json for dashboard stats."""
    import json
    history_path = LEADS_CSV_PATH.parent / "search_history.json"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": now, "success": success}
    try:
        history: list[dict] = []
        if history_path.exists():
            history = json.loads(history_path.read_text(encoding="utf-8"))
        history.append(entry)
        # Keep last 1000
        history = history[-1000:]
        history_path.write_text(
            json.dumps(history, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning(f"Failed to record search: {exc}")


def get_search_stats() -> tuple[int, int, int]:
    """Return (total, successful, failed) search counts."""
    import json
    history_path = LEADS_CSV_PATH.parent / "search_history.json"
    try:
        if not history_path.exists():
            return 0, 0, 0
        history = json.loads(history_path.read_text(encoding="utf-8"))
        total = len(history)
        successful = sum(1 for h in history if h.get("success"))
        return total, successful, total - successful
    except Exception:
        return 0, 0, 0
