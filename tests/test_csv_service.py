"""
Tests for the CSV storage service.

Covers:
  - CSV file creation
  - Appending leads
  - Duplicate detection (by website + email)
  - Concurrent writes (thread safety)
  - Querying / filtering / sorting / pagination
  - Deletion
  - Export
"""

import csv
import threading
from pathlib import Path

import pytest

from services import csv_service


def test_csv_creation(temp_data_dir):
    """CSV file is created with correct headers when it doesn't exist."""
    csv_service.init_csv()
    csv_path = temp_data_dir / "leads.csv"
    assert csv_path.exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == csv_service.CSV_COLUMNS
        assert len(list(reader)) == 0  # no data yet


def test_append_leads(temp_data_dir):
    """Appending leads writes them to the CSV."""
    csv_service.init_csv()
    leads = [
        {"company_name": "Acme Corp", "website": "https://acme.com", "email": "info@acme.com"},
        {"company_name": "Beta Inc", "website": "https://beta.com", "email": "hello@beta.com"},
    ]
    added, skipped = csv_service.append_leads(leads, search_query="test query")

    assert len(added) == 2
    assert skipped == 0
    all_leads = csv_service.read_all_leads()
    assert len(all_leads) == 2
    assert all_leads[0]["company_name"] == "Acme Corp"
    assert all_leads[0]["lead_id"].startswith("LD-")
    assert all_leads[0]["generated_at"] != ""
    assert all_leads[0]["search_query"] == "test query"


def test_duplicate_detection(temp_data_dir):
    """Leads with the same website+email are detected as duplicates."""
    csv_service.init_csv()
    lead = {"company_name": "Acme", "website": "https://acme.com", "email": "info@acme.com"}
    added, _ = csv_service.append_leads([lead])
    assert len(added) == 1

    # Same website + email = duplicate
    dup = {"company_name": "Acme LLC", "website": "https://acme.com", "email": "info@acme.com"}
    added, skipped = csv_service.append_leads([dup])
    assert len(added) == 0
    assert skipped == 1

    # Same website, different email = NOT a duplicate
    non_dup = {"company_name": "Acme Corp", "website": "https://acme.com", "email": "sales@acme.com"}
    added, skipped = csv_service.append_leads([non_dup])
    assert len(added) == 1
    assert skipped == 0


def test_duplicate_website_normalisation(temp_data_dir):
    """www. prefix and trailing slash are normalised for dedup."""
    csv_service.init_csv()
    csv_service.append_leads([{"website": "https://www.acme.com/", "email": "a@acme.com"}])
    added, skipped = csv_service.append_leads([
        {"website": "https://acme.com", "email": "a@acme.com"}
    ])
    assert len(added) == 0
    assert skipped == 1  # normalised to same key


def test_empty_lead_not_duplicate(temp_data_dir):
    """A lead with no website and no email is never a duplicate."""
    csv_service.init_csv()
    csv_service.append_leads([{"company_name": "Lead A"}])
    added, skipped = csv_service.append_leads([{"company_name": "Lead B"}])
    assert len(added) == 1
    assert skipped == 0


def test_query_leads_search(temp_data_dir):
    """Search filters by company name."""
    csv_service.init_csv()
    csv_service.append_leads([
        {"company_name": "Acme Corp", "city": "Karachi"},
        {"company_name": "Beta Inc", "city": "Lahore"},
        {"company_name": "Gamma LLC", "city": "Karachi"},
    ])
    results, total = csv_service.query_leads(search="acme")
    assert total == 1
    assert results[0]["company_name"] == "Acme Corp"


def test_query_leads_filter_city(temp_data_dir):
    """Filter by city."""
    csv_service.init_csv()
    csv_service.append_leads([
        {"company_name": "Acme", "city": "Karachi"},
        {"company_name": "Beta", "city": "Lahore"},
        {"company_name": "Gamma", "city": "Karachi"},
    ])
    results, total = csv_service.query_leads(city="Karachi")
    assert total == 2


def test_query_leads_sort(temp_data_dir):
    """Sorting by company_name ascending."""
    csv_service.init_csv()
    csv_service.append_leads([
        {"company_name": "Zeta"},
        {"company_name": "Alpha"},
        {"company_name": "Mid"},
    ])
    results, _ = csv_service.query_leads(sort_by="company_name", sort_order="asc", page_size=10)
    assert results[0]["company_name"] == "Alpha"
    assert results[2]["company_name"] == "Zeta"


def test_query_leads_pagination(temp_data_dir):
    """Pagination returns correct page slice."""
    csv_service.init_csv()
    leads = [{"company_name": f"Company {i}"} for i in range(25)]
    csv_service.append_leads(leads)
    page1, total = csv_service.query_leads(page=1, page_size=10)
    page2, _ = csv_service.query_leads(page=2, page_size=10)
    assert total == 25
    assert len(page1) == 10
    assert len(page2) == 10
    assert page1[0]["company_name"] != page2[0]["company_name"]


def test_delete_lead(temp_data_dir):
    """Deleting a lead removes it from the CSV."""
    csv_service.init_csv()
    added, _ = csv_service.append_leads([{"company_name": "Acme", "website": "https://acme.com"}])
    lead_id = added[0]["lead_id"]

    assert csv_service.delete_lead(lead_id) is True
    assert len(csv_service.read_all_leads()) == 0
    assert csv_service.delete_lead(lead_id) is False  # already deleted


def test_count_leads_and_today(temp_data_dir):
    """count_leads and count_leads_today return correct counts."""
    csv_service.init_csv()
    csv_service.append_leads([
        {"company_name": "A"},
        {"company_name": "B"},
        {"company_name": "C"},
    ])
    assert csv_service.count_leads() == 3
    assert csv_service.count_leads_today() == 3  # all generated just now


def test_export_csv(temp_data_dir):
    """Export returns CSV-formatted string."""
    csv_service.init_csv()
    csv_service.append_leads([{"company_name": "Acme", "city": "Karachi"}])
    csv_str = csv_service.export_csv()
    assert "company_name" in csv_str
    assert "Acme" in csv_str
    assert "Karachi" in csv_str


def test_concurrent_writes(temp_data_dir):
    """Multiple threads appending leads simultaneously don't corrupt the CSV."""
    csv_service.init_csv()

    def append_batch(start: int):
        leads = [{"company_name": f"Company {start + i}", "email": f"email{start + i}@test.com"}
                 for i in range(10)]
        csv_service.append_leads(leads)

    threads = [threading.Thread(target=append_batch, args=(i * 10,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    all_leads = csv_service.read_all_leads()
    assert len(all_leads) == 50
    # All lead_ids should be unique
    ids = [l["lead_id"] for l in all_leads]
    assert len(set(ids)) == 50


def test_search_history(temp_data_dir):
    """Search history is recorded and stats are returned."""
    csv_service.record_search(success=True)
    csv_service.record_search(success=True)
    csv_service.record_search(success=False)
    total, successful, failed = csv_service.get_search_stats()
    assert total == 3
    assert successful == 2
    assert failed == 1
