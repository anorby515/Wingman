"""Tests for helper functions in backend/ticketmaster.py."""

from backend.ticketmaster import format_show_date, name_matches


class TestNameMatches:
    def test_exact_match(self):
        assert name_matches("Caamp", ["Caamp"]) is True

    def test_case_insensitive(self):
        assert name_matches("caamp", ["CAAMP"]) is True

    def test_substring_match(self):
        assert name_matches("Tyler Childers", ["Tyler Childers & The Food Stamps"]) is True

    def test_no_match(self):
        assert name_matches("Zach Bryan", ["Bryan Adams"]) is False

    def test_empty_list(self):
        assert name_matches("Caamp", []) is False

    def test_partial_overlap(self):
        assert name_matches("Hozier", ["Hozier"]) is True


class TestFormatShowDate:
    def test_valid_date(self):
        assert format_show_date("2026-07-15") == "Jul 15, 2026"

    def test_another_date(self):
        assert format_show_date("2026-01-01") == "Jan 1, 2026"

    def test_invalid_date_passthrough(self):
        assert format_show_date("not-a-date") == "not-a-date"

    def test_empty_string(self):
        assert format_show_date("") == ""
