import json

from documind_mcp import enterprise_tools as tools


def test_lookup_ticket_is_case_insensitive():
    assert tools.lookup_ticket(" it-1001 ")["title"].startswith("VPN")


def test_lookup_unknown_ticket_returns_error():
    assert "error" in tools.lookup_ticket("IT-9999")


def test_search_tickets_filters():
    open_it = tools.search_tickets(status="open", assignee="priya")
    assert [t["ticket_id"] for t in open_it] == ["IT-1001"]

    by_keyword = tools.search_tickets(keyword="laptop")
    assert [t["ticket_id"] for t in by_keyword] == ["IT-1002"]

    assert tools.search_tickets(status="nonexistent") == []


def test_search_tickets_limit_is_clamped():
    assert len(tools.search_tickets(limit=2)) == 2
    assert len(tools.search_tickets(limit=-5)) == 1


def test_find_employee_by_name_and_department():
    assert [e["name"] for e in tools.find_employee("asha")] == ["Asha Verma"]

    it_staff = tools.find_employee("", department="it")
    assert {e["department"] for e in it_staff} == {"IT"}
    assert len(it_staff) == 3

    assert tools.find_employee("nobody-here") == []


def test_send_notification_writes_to_mock_outbox(tmp_path):
    outbox = tmp_path / "out" / "outbox.jsonl"

    result = tools.send_notification(
        "Asha.Verma@example.com", "Hello", "Please review ticket HR-2001.", outbox
    )

    assert result["status"].startswith("queued")
    lines = outbox.read_text().strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["to"] == "asha.verma@example.com"


def test_send_notification_rejects_bad_input(tmp_path):
    outbox = tmp_path / "outbox.jsonl"

    unknown = tools.send_notification("x@evil.com", "Hi", "Hi", outbox)
    blank = tools.send_notification("asha.verma@example.com", " ", "Hi", outbox)
    too_long = tools.send_notification(
        "asha.verma@example.com", "Hi", "x" * 5000, outbox
    )

    assert all("error" in r for r in (unknown, blank, too_long))
    assert not outbox.exists()
