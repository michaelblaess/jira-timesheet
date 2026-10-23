"""Abgleich abgeschlossener Monate mit dem Cache.

Anlass: Jira archiviert alte, abgeschlossene Tickets. Ohne Abgleich zeigte die
Jahresansicht den Januar 2026 mit 92,75 h statt 161,25 h.
"""

from __future__ import annotations

import asyncio
from datetime import date

import pytest

from jira_timesheet.models.timesheet import WorklogEntry
from jira_timesheet.services import cache_service
from jira_timesheet.services.cache_service import CacheService
from jira_timesheet.services.month_cache import (
    months_between,
    reconcile,
)

MAIL = "person@beispiel.de"
# Ein Monat, der sicher abgeschlossen ist, und einer, der es sicher nicht ist.
ALT_ERSTER, ALT_LETZTER = date(2025, 2, 1), date(2025, 2, 28)
ZUKUNFT = date(2099, 5, 1)


def _eintrag(ticket: str, tag: date, stunden: float = 1.0) -> WorklogEntry:
    return WorklogEntry(date=tag, ticket=ticket, summary="x", author=MAIL, budget="", hours=stunden)


def _sichtbarkeit(antworten: dict[str, bool | None]) -> tuple[list[str], object]:
    gefragt: list[str] = []

    async def frage(key: str) -> bool | None:
        gefragt.append(key)
        return antworten.get(key, True)

    return gefragt, frage


def _abgleich(
    fresh: list[WorklogEntry], antworten: dict[str, bool | None], first: date = ALT_ERSTER, last: date = ALT_LETZTER
) -> tuple[list[WorklogEntry], list[str], object]:
    gefragt, frage = _sichtbarkeit(antworten)
    ergebnis = asyncio.run(reconcile(fresh, first, last, MAIL, frage))  # type: ignore[arg-type]
    return ergebnis.entries, gefragt, ergebnis


class TestAbgleich:
    def test_archiviertes_ticket_bleibt_aus_dem_cache(self) -> None:
        CacheService.save(2025, 2, MAIL, [_eintrag("A-1", date(2025, 2, 3), 4), _eintrag("A-2", date(2025, 2, 4), 2)])
        eintraege, gefragt, ergebnis = _abgleich([_eintrag("A-1", date(2025, 2, 3), 4)], {"A-2": False})
        assert sorted(e.ticket for e in eintraege) == ["A-1", "A-2"]
        assert gefragt == ["A-2"]
        assert ergebnis.rescued[0].tickets == ["A-2"]  # type: ignore[attr-defined]
        assert ergebnis.rescued[0].hours == 2  # type: ignore[attr-defined]

    def test_sichtbares_ticket_ohne_buchung_gilt_als_entfernt(self) -> None:
        CacheService.save(2025, 2, MAIL, [_eintrag("A-1", date(2025, 2, 3)), _eintrag("A-2", date(2025, 2, 4))])
        eintraege, _gefragt, ergebnis = _abgleich([_eintrag("A-1", date(2025, 2, 3))], {"A-2": True})
        assert [e.ticket for e in eintraege] == ["A-1"]
        assert ergebnis.rescued == []  # type: ignore[attr-defined]

    def test_unklare_sichtbarkeit_behaelt_die_buchung(self) -> None:
        CacheService.save(2025, 2, MAIL, [_eintrag("A-2", date(2025, 2, 4))])
        eintraege, _gefragt, ergebnis = _abgleich([], {"A-2": None})
        assert [e.ticket for e in eintraege] == ["A-2"]
        assert ergebnis.rescued[0].unclear == ["A-2"]  # type: ignore[attr-defined]

    def test_fehler_bei_der_pruefung_behaelt_die_buchung(self) -> None:
        CacheService.save(2025, 2, MAIL, [_eintrag("A-2", date(2025, 2, 4))])

        async def kaputt(_key: str) -> bool | None:
            raise RuntimeError("Netz weg")

        ergebnis = asyncio.run(reconcile([], ALT_ERSTER, ALT_LETZTER, MAIL, kaputt))
        assert [e.ticket for e in ergebnis.entries] == ["A-2"]

    def test_der_cache_wird_nicht_verkleinert(self) -> None:
        """Genau das passiert in der TUI bei F5 - hier darf es nicht passieren."""
        CacheService.save(2025, 2, MAIL, [_eintrag("A-1", date(2025, 2, 3)), _eintrag("A-2", date(2025, 2, 4))])
        _abgleich([_eintrag("A-1", date(2025, 2, 3))], {"A-2": False})
        assert sorted(e.ticket for e in CacheService.load(2025, 2, MAIL)) == ["A-1", "A-2"]

    def test_vor_dem_schreiben_bleibt_eine_sicherung(self) -> None:
        CacheService.save(2025, 2, MAIL, [_eintrag("A-1", date(2025, 2, 3), 7)])
        _abgleich([_eintrag("A-1", date(2025, 2, 3), 8)], {})
        sicherung = CacheService._cache_path(2025, 2, MAIL).with_suffix(".json.bak")
        assert sicherung.is_file()
        assert '"hours": 7' in sicherung.read_text(encoding="utf-8")

    def test_ein_neuer_monat_landet_im_cache(self) -> None:
        _abgleich([_eintrag("A-1", date(2025, 2, 3))], {})
        assert [e.ticket for e in CacheService.load(2025, 2, MAIL)] == ["A-1"]

    def test_ein_offener_monat_bleibt_unberuehrt(self) -> None:
        letzter = date(2099, 5, 31)
        eintraege, gefragt, _ = _abgleich([_eintrag("A-1", ZUKUNFT)], {}, ZUKUNFT, letzter)
        assert [e.ticket for e in eintraege] == ["A-1"]
        assert gefragt == []
        assert CacheService.load(2099, 5, MAIL) == []

    def test_ein_angeschnittener_monat_wird_nicht_abgeglichen(self) -> None:
        CacheService.save(2025, 2, MAIL, [_eintrag("A-2", date(2025, 2, 20))])
        eintraege, gefragt, _ = _abgleich([], {"A-2": False}, date(2025, 2, 10), date(2025, 2, 28))
        assert eintraege == []
        assert gefragt == []

    def test_ein_ticket_wird_nur_einmal_gefragt(self) -> None:
        CacheService.save(2025, 1, MAIL, [_eintrag("A-2", date(2025, 1, 4))])
        CacheService.save(2025, 2, MAIL, [_eintrag("A-2", date(2025, 2, 4))])
        _eintraege, gefragt, _ = _abgleich([], {"A-2": False}, date(2025, 1, 1), ALT_LETZTER)
        assert gefragt == ["A-2"]


class TestMonate:
    def test_ueber_den_jahreswechsel(self) -> None:
        assert months_between(date(2025, 11, 5), date(2026, 2, 1)) == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]


def test_der_cache_liegt_im_testordner() -> None:
    """Die Isolierung aus conftest.py - sonst liest ein Test den echten Cache."""
    assert ".jira-timesheet" not in str(cache_service.CACHE_DIR)


@pytest.fixture(autouse=True)
def _leerer_cache() -> None:
    cache_service.CACHE_DIR.mkdir(parents=True, exist_ok=True)


class TestF5InDerTui:
    """F5 holte bis v1.25 frisch ab und schrieb den Live-Stand in den Cache.

    Jetzt laeuft auch der App-Weg ueber den Abgleich - gerettete Buchungen
    ueberleben den Refresh.
    """

    def test_refresh_behaelt_das_archivierte_ticket(self) -> None:
        from types import SimpleNamespace

        from jira_timesheet.app import JiraTimesheetApp

        CacheService.save(2025, 2, MAIL, [_eintrag("A-1", date(2025, 2, 3)), _eintrag("A-2", date(2025, 2, 4), 5)])
        protokoll: list[str] = []

        async def unsichtbar(_key: str) -> bool | None:
            return False

        app = SimpleNamespace(settings=None, _settings=SimpleNamespace(email=MAIL), _write_log=protokoll.append)
        client = SimpleNamespace(is_issue_visible=unsichtbar)
        eintraege = asyncio.run(
            JiraTimesheetApp._reconcile_with_cache(
                app,  # type: ignore[arg-type]
                client,  # type: ignore[arg-type]
                [_eintrag("A-1", date(2025, 2, 3))],
                ALT_ERSTER,
                ALT_LETZTER,
            )
        )
        assert sorted(e.ticket for e in eintraege) == ["A-1", "A-2"]
        assert sorted(e.ticket for e in CacheService.load(2025, 2, MAIL)) == ["A-1", "A-2"]
        assert len(protokoll) == 1
