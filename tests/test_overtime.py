"""Mehrarbeit in Jahres- und Monatsansicht sichtbar machen."""

from __future__ import annotations

from datetime import date

import pytest
from textual.app import App, ComposeResult

from jira_timesheet.i18n import load_locale
from jira_timesheet.models.timesheet import Timesheet, TimesheetDay, WorklogEntry
from jira_timesheet.widgets.calendar_view import CalendarView, DayTile, WeekSummaryTile
from jira_timesheet.widgets.overtime import BAR_MARKER, format_delta, hours_bar, is_over
from jira_timesheet.widgets.year_panel import MonthTile


@pytest.fixture(autouse=True)
def _deutsch() -> None:
    load_locale("de")


class TestBalken:
    def test_unter_soll_ohne_marke(self) -> None:
        balken = hours_bar(80.0, 160.0, 18, "green", "magenta").plain
        assert len(balken) == 18
        assert BAR_MARKER not in balken

    def test_genau_soll_ist_keine_mehrarbeit(self) -> None:
        assert not is_over(160.0, 160.0)
        assert BAR_MARKER not in hours_bar(160.0, 160.0, 18, "green", "magenta").plain

    def test_mehrarbeit_mit_marke_und_ueberhang(self) -> None:
        balken = hours_bar(200.5, 176.0, 18, "green", "magenta").plain
        assert len(balken) == 18
        links, rechts = balken.split(BAR_MARKER)
        assert links and rechts
        assert set(links) == {"█"} and set(rechts) == {"█"}

    def test_knappe_mehrarbeit_bleibt_sichtbar(self) -> None:
        balken = hours_bar(176.25, 176.0, 18, "green", "magenta").plain
        assert balken.endswith(f"{BAR_MARKER}█")

    def test_abweichung_mit_vorzeichen(self) -> None:
        assert format_delta(47.75, 40.0) == "+7,75h"
        assert format_delta(38.0, 40.0) == "-2,00h"


class TestJahreskachel:
    def _kachel(self, ist: float, soll: float) -> str:
        return (
            MonthTile(month=10, year=2026, actual_hours=ist, target_hours=soll, working_days=21, target_days=22)
            .render()
            .plain
        )

    def test_prozent_nicht_gedeckelt(self) -> None:
        text = self._kachel(200.5, 176.0)
        assert "114%" in text
        assert "+24,5h" in text
        assert BAR_MARKER in text

    def test_unter_soll_ohne_abweichung(self) -> None:
        text = self._kachel(134.2, 176.0)
        assert "76%" in text
        assert "+" not in text
        assert BAR_MARKER not in text


class TestWochenkachel:
    def test_mehrarbeit_zeigt_abweichung(self) -> None:
        text = WeekSummaryTile(week_hours=47.75, week_number=41, target_hours=40.0).render().plain
        assert "+7,75h" in text

    def test_wochenstunden_bleiben_gruen(self) -> None:
        text = WeekSummaryTile(week_hours=54.0, week_number=42, target_hours=40.0).render()
        stile = {text.plain[s.start : s.end].strip(): str(s.style) for s in text.spans}
        assert stile["54,00h"] == "bold green"
        assert stile["+14,00h"] == "dim"

    def test_unter_soll_zeigt_fehlende_stunden(self) -> None:
        text = WeekSummaryTile(week_hours=37.75, week_number=44, target_hours=40.0).render().plain
        assert "-2,25h" in text

    async def test_abweichung_bricht_nicht_um(self) -> None:
        ts = Timesheet(developer="x", email="", date_from=date(2025, 10, 1), date_to=date(2025, 10, 31))
        app = _Kalender()
        async with app.run_test(size=(160, 50)) as pilot:
            cal = app.query_one(CalendarView)
            cal.load_timesheet(ts)
            await pilot.pause()
            kachel = cal.query(WeekSummaryTile).first()
            assert kachel.content_region.width >= len("+14,00h")

    def test_ohne_mehrarbeit_keine_abweichung(self) -> None:
        text = WeekSummaryTile(week_hours=40.0, week_number=41, target_hours=40.0).render().plain
        assert "+" not in text


class TestTageskachel:
    def test_feiertag_hat_kein_soll(self) -> None:
        # Freitag 31.10.2025: als Arbeitstag unter Soll, als Feiertag erfuellt.
        tag = date(2025, 10, 31)
        eintrag = WorklogEntry(date=tag, ticket="ABC-1", summary="x", author="x", budget="", hours=2.0)
        data = TimesheetDay(date=tag, entries=[eintrag])
        assert _stil_der_stunden(DayTile(day_date=tag, day_data=data)) == "bold yellow"
        assert _stil_der_stunden(DayTile(day_date=tag, day_data=data, is_holiday=True)) == "bold green"


def _stil_der_stunden(tile: DayTile) -> str:
    text = tile.render()
    for span in text.spans:
        if text.plain[span.start : span.end].endswith("h"):
            return str(span.style)
    raise AssertionError("keine Stundenangabe gerendert")


class _Kalender(App[None]):
    def compose(self) -> ComposeResult:
        yield CalendarView(hours_per_day=8.0)


async def test_wochensoll_folgt_den_arbeitstagen_im_monat() -> None:
    """Oktober 2025: KW 40 beginnt am Mittwoch, der Reformationstag (Fr 31.10.) zaehlt nicht."""
    ts = Timesheet(developer="x", email="", date_from=date(2025, 10, 1), date_to=date(2025, 10, 31))
    app = _Kalender()
    async with app.run_test(size=(160, 50)) as pilot:
        cal = app.query_one(CalendarView)
        cal.load_timesheet(ts, holidays={date(2025, 10, 31)})
        await pilot.pause()
        soll = [k.target_hours for k in cal.query(WeekSummaryTile)]
    assert soll == [24.0, 40.0, 40.0, 40.0, 32.0]
