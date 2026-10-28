"""Die Wochensummen-Kachel im Monatskalender nennt ihre Kalenderwoche."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from jira_timesheet.i18n import load_locale
from jira_timesheet.widgets.calendar_view import CalendarView, WeekSummaryTile


@pytest.fixture(params=["de", "en"])
def lang(request: pytest.FixtureRequest) -> Iterator[str]:
    load_locale(request.param)
    yield request.param
    load_locale("de")


def test_kachel_nennt_die_kw(lang: str) -> None:
    text = WeekSummaryTile(week_hours=47.75, week_number=41).render().plain
    erwartet = "KW 41" if lang == "de" else "Week 41"
    assert text.splitlines()[0] == erwartet
    assert "47,75h" in text or "47.75h" in text


def test_ohne_kw_bleibt_die_kachel_wie_bisher() -> None:
    load_locale("de")
    assert "\n" not in WeekSummaryTile(week_hours=8.0).render().plain


def test_wochen_beginnen_montags_mit_der_iso_kw() -> None:
    from datetime import date

    weeks = CalendarView._build_weeks(date(2026, 10, 1), date(2026, 10, 31))
    assert [w[0].isocalendar().week for w in weeks] == [40, 41, 42, 43, 44]
