"""Tests fuer die Ticket-Analyse in der TUI.

Kein Netzwerk: der Abruf wird durch eine Attrappe ersetzt. Geprueft wird die
Verdrahtung - Keyerkennung, Verhalten des Dialogs und das Schreiben der
Datei ueber den Speichern-Dialog.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import current_language, load_locale
from jira_timesheet.models.settings import Settings
from jira_timesheet.models.ticket_lifecycle import TicketLifecycleData
from jira_timesheet.screens.ticket_analysis_screen import TicketAnalysisScreen, ticket_key


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt die Nutzerdateien, damit die echten unberuehrt bleiben."""
    monkeypatch.setattr(Settings, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", tmp_path / "settings.json")
    return tmp_path


@pytest.fixture(autouse=True)
def _sprache() -> Iterator[None]:
    """Laedt die deutsche Sprachdatei und stellt sie danach zurueck.

    Ohne geladene Sprache liefert ``t()`` den Schluessel statt des Textes -
    ein Test auf den angezeigten Text wuerde dann nichts pruefen.
    """
    vorher = current_language()
    load_locale("de")
    yield
    load_locale(vorher)


def _daten() -> TicketLifecycleData:
    """Rohdaten eines kleinen Tickets."""
    return TicketLifecycleData(
        issue={
            "key": "ABC-1",
            "fields": {
                "summary": "Testticket",
                "created": "2026-07-01T09:00:00.000+0200",
                "updated": "2026-07-02T09:00:00.000+0200",
                "issuetype": {"name": "Story"},
                "priority": {"name": "Medium"},
                "status": {"name": "IN ARBEIT"},
                "reporter": {"displayName": "Muster, Erika"},
                "assignee": {"displayName": "Beispiel, Max"},
            },
        },
        changelog=[
            {
                "created": "2026-07-01T10:00:00.000+0200",
                "author": {"displayName": "Beispiel, Max"},
                "items": [{"field": "status", "fromString": "Offen", "toString": "IN ARBEIT"}],
            }
        ],
        comments=[],
    )


class TestTicketKey:
    """Der Key muss aus jeder Schreibweise fallen."""

    @pytest.mark.parametrize(
        "eingabe",
        [
            "ABC-123",
            "abc-123",
            "  ABC-123  ",
            "https://jira.example.com/browse/ABC-123",
            "https://example.atlassian.net/browse/ABC-123?focusedId=1",
        ],
    )
    def test_erkennt_key(self, eingabe: str) -> None:
        assert ticket_key(eingabe) == "ABC-123"

    @pytest.mark.parametrize("eingabe", ["", "kein Ticket", "1234", "https://example.com/"])
    def test_ohne_key_bleibt_leer(self, eingabe: str) -> None:
        assert ticket_key(eingabe) == ""


class TestDialog:
    """Verhalten des Eingabe-Dialogs."""

    async def test_gibt_den_erkannten_key_zurueck(self) -> None:
        from textual.widgets import Input

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            ergebnis: list[str | None] = []
            app.push_screen(TicketAnalysisScreen(), callback=ergebnis.append)
            await pilot.pause()

            feld = app.screen.query_one("#ticket-input", Input)
            feld.value = "https://jira.example.com/browse/ABC-123"
            await pilot.pause()
            # Der Knopf gibt erst frei, wenn ein Key erkennbar ist.
            from textual.widgets import Button

            assert not app.screen.query_one("#ticket-ok", Button).disabled

            await pilot.click("#ticket-ok")
            await pilot.pause()
            assert ergebnis == ["ABC-123"]

    async def test_ohne_key_bleibt_der_dialog_offen(self) -> None:
        from textual.widgets import Button, Input

        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            ergebnis: list[str | None] = []
            app.push_screen(TicketAnalysisScreen(), callback=ergebnis.append)
            await pilot.pause()

            app.screen.query_one("#ticket-input", Input).value = "kein Ticket"
            await pilot.pause()
            assert app.screen.query_one("#ticket-ok", Button).disabled
            assert ergebnis == []

    async def test_abbrechen_gibt_nichts_zurueck(self) -> None:
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            ergebnis: list[str | None] = []
            app.push_screen(TicketAnalysisScreen(), callback=ergebnis.append)
            await pilot.pause()
            await pilot.click("#ticket-cancel")
            await pilot.pause()
            assert ergebnis == [None]


class TestVerdrahtung:
    """Aktion, Binding und das Schreiben der Datei."""

    async def test_binding_liegt_auf_b(self) -> None:
        app = JiraTimesheetApp()
        async with app.run_test():
            aktionen = {
                binding.action
                for liste in app._bindings.key_to_bindings.values()
                for binding in liste
            }
            assert "ticket_report" in aktionen
            belegt = [
                binding.action
                for binding in app._bindings.key_to_bindings.get("b", [])
            ]
            assert belegt == ["ticket_report"]

    async def test_ohne_zugang_kommt_ein_hinweis(self) -> None:
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            app._settings.jira_host = ""
            app._settings.jira_token = ""
            gemeldet: list[str] = []
            app.notify = lambda text, **kwargs: gemeldet.append(str(text))  # type: ignore[assignment]
            app.action_ticket_report()
            await pilot.pause()
            assert gemeldet and "Zugangsdaten" in gemeldet[0]

    async def test_schreibt_die_datei(
        self, tmp_path: Path, blockierte_browser_aufrufe: list[str]
    ) -> None:
        ziel = tmp_path / "ABC-1.html"
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            app._settings.jira_host = "https://example.atlassian.net"
            app._ticket_data = _daten()
            app._do_write_ticket_report(ziel)
            await pilot.pause()

            assert ziel.is_file()
            inhalt = ziel.read_text(encoding="utf-8")
            assert inhalt.startswith("<!doctype html>")
            assert "Testticket" in inhalt
            # Der naechste Speichern-Dialog soll hier starten.
            assert app._last_export_dir == str(ziel.parent)
            # Der Bericht wird zum Ansehen geoeffnet - im Test aber nur
            # vorgemerkt, nie wirklich (Fixture blockierte_browser_aufrufe).
            assert blockierte_browser_aufrufe == [ziel.resolve().as_uri()]

    async def test_abbruch_schreibt_nichts(self, tmp_path: Path) -> None:
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            app._ticket_data = _daten()
            app._do_write_ticket_report(None)
            await pilot.pause()
            assert list(tmp_path.glob("*.html")) == []
            # Der Zwischenspeicher muss auch beim Abbruch geleert werden.
            assert app._ticket_data is None


def test_zeitzone_bleibt_erhalten() -> None:
    """Der Bericht rechnet in der von Jira gelieferten Ortszeit."""
    from jira_timesheet.services.ticket_report.lifecycle import parse_ts

    moment = parse_ts("2026-07-01T09:00:00.000+0200")
    assert moment is not None
    assert moment.utcoffset() == dt.timedelta(hours=2)


def test_client_holt_alle_drei_antworten(monkeypatch: pytest.MonkeyPatch) -> None:
    """Der Client muss Issue, Aenderungen und Kommentare zusammenfuehren."""
    import asyncio

    from jira_timesheet.services.jira_client import JiraClient

    gerufen: list[str] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload
            self.status_code = 200

        def json(self) -> dict[str, Any]:
            return self._payload

    class FakeClient:
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, **kwargs: Any) -> FakeResponse:
            gerufen.append(url)
            if url.endswith("/changelog"):
                return FakeResponse({"values": [{"created": "x"}], "isLast": True})
            if url.endswith("/comment"):
                return FakeResponse({"comments": [{"created": "y"}]})
            return FakeResponse({"key": "ABC-1", "fields": {}})

    monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(JiraClient, "_check_response", lambda self, r, u: None)

    client = JiraClient(host="https://example.atlassian.net", email="a@b.de", token="x")
    daten = asyncio.run(client.get_ticket_lifecycle("ABC-1"))

    assert daten.key == "ABC-1"
    assert len(daten.changelog) == 1
    assert len(daten.comments) == 1


class TestKontextmenue:
    """Aus dem Rechtsklick auf eine Zeile heraus."""

    def _eintrag(self) -> Any:
        from datetime import date

        from jira_timesheet.models.timesheet import WorklogEntry

        return WorklogEntry(
            date=date(2026, 7, 1),
            ticket="ABC-123",
            summary="Testticket",
            author="Erika Muster",
            budget="",
            hours=1.0,
        )

    async def test_startet_die_analyse_fuer_die_zeile(self) -> None:
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            gerufen: list[str] = []
            app._fetch_ticket_report = lambda key: gerufen.append(key)  # type: ignore[assignment]
            app._menu_entry = self._eintrag()
            app._on_context_menu("ticket_report")
            await pilot.pause()
            assert gerufen == ["ABC-123"]

    async def test_ohne_ticket_passiert_nichts(self) -> None:
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            gerufen: list[str] = []
            app._fetch_ticket_report = lambda key: gerufen.append(key)  # type: ignore[assignment]
            app._menu_entry = None
            app._on_context_menu("ticket_report")
            await pilot.pause()
            assert gerufen == []
