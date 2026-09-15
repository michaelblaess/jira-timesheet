"""Tests fuer die angezeigten Luecken: nur vergangene Arbeitstage fehlen.

Die Gruende kommen aus HolidayService selbst und nicht aus einer Konstante
im Test - sonst koennten Test und Code denselben falschen Marker teilen und
trotzdem gruen sein.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest

from jira_timesheet.app import visible_missing_days
from jira_timesheet.i18n import load_locale
from jira_timesheet.services.holiday_service import HolidayService

# Stichtag Mittwoch 16.09.2026, fest verdrahtet - ein Test darf nicht am Kalender haengen.
TODAY = date(2026, 9, 16)


@pytest.fixture(autouse=True, params=["de", "en"])
def _sprache(request: pytest.FixtureRequest) -> Iterator[None]:
    """Laedt jedes Sprachpaket einmal.

    Der Luecken-Marker steckt im uebersetzten Text. Ohne geladenes Paket
    liefert t() nur den Schluessel, und der traegt keinen Marker.
    """
    load_locale(request.param)
    yield
    load_locale("de")


def _missing(day: date) -> tuple[date, str]:
    """Der Eintrag, den HolidayService fuer einen ungebuchten Tag liefert."""
    found = HolidayService("SN").get_missing_workdays(day, day, set())
    assert len(found) == 1
    return found[0]


def test_vergangene_luecke_bleibt() -> None:
    gestern = _missing(date(2026, 9, 15))
    assert visible_missing_days([gestern], TODAY) == [gestern]


def test_heute_fehlt_noch_nichts() -> None:
    assert visible_missing_days([_missing(TODAY)], TODAY) == []


def test_kommende_tage_fehlen_nicht() -> None:
    kommende = [_missing(date(2026, 9, 17)), _missing(date(2026, 9, 30))]
    assert visible_missing_days(kommende, TODAY) == []


def test_kuenftiger_feiertag_bleibt_stehen() -> None:
    # 25.12.2026 ist ein Freitag, faellt also nicht als Wochenende heraus.
    weihnachten = _missing(date(2026, 12, 25))
    assert visible_missing_days([weihnachten], TODAY) == [weihnachten]


def test_reihenfolge_bleibt_erhalten() -> None:
    eingabe = [
        _missing(date(2026, 9, 1)),
        _missing(date(2026, 9, 2)),
        _missing(date(2026, 9, 17)),
        _missing(date(2026, 12, 25)),
    ]
    assert visible_missing_days(eingabe, TODAY) == [eingabe[0], eingabe[1], eingabe[3]]
