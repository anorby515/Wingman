"""Tests for helper functions in backend/main.py."""

from backend.main import _format_show_date, _name_matches


class TestNameMatches:
    def test_exact_match(self):
        assert _name_matches("Caamp", ["Caamp"]) is True

    def test_case_insensitive(self):
        assert _name_matches("caamp", ["CAAMP"]) is True

    def test_substring_match(self):
        assert _name_matches("Tyler Childers", ["Tyler Childers & The Food Stamps"]) is True

    def test_no_match(self):
        assert _name_matches("Zach Bryan", ["Bryan Adams"]) is False

    def test_empty_list(self):
        assert _name_matches("Caamp", []) is False

    def test_partial_overlap(self):
        # "Hozier" should match attraction "Hozier"
        assert _name_matches("Hozier", ["Hozier"]) is True


class TestFormatShowDate:
    def test_valid_date(self):
        assert _format_show_date("2026-07-15") == "Jul 15, 2026"

    def test_another_date(self):
        assert _format_show_date("2026-01-01") == "Jan 1, 2026"

    def test_invalid_date_passthrough(self):
        assert _format_show_date("not-a-date") == "not-a-date"

    def test_empty_string(self):
        assert _format_show_date("") == ""
