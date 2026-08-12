"""Tests fuer die Jahresansicht als Reiter.

Bis v1.19.0 war die Jahresansicht ein Modal, das die Taste "j" oeffnete und
das seine Zahlen fertig in den Konstruktor bekam. Als Reiter muss sie drei
Dinge koennen, die ein Modal nicht brauchte: beim ERSTEN Ansehen laden statt
beim Start, den Stand behalten statt ihn bei jedem Oeffnen neu aufzubauen, und
ihn verwerfen, wenn sich darunter etwas aendert (Jahr, Einstellungen, manuelle
Buchung). Genau das halten diese Tests fest.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from textual.widgets import TabbedContent

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import load_locale
from jira_timesheet.models.settings import Settings
from jira_timesheet.models.timesheet import WorklogEntry
from jira_timesheet.services import cache_service
from jira_timesheet.services.manual_entry_service import ManualEntryService
from jira_timesheet.widgets.summary_panel import SummaryPanel
from jira_timesheet.widgets.year_panel import MonthTile, YearPanel

# Reissleine, keine erwartete Dauer: wird sie erreicht, haengt etwas.
_GEDULD_SECONDS = 10.0

_JAHR = 2026


class FakeJiraClient:
    """Liefert je Zeitraum genau eine Buchung und zaehlt die Abrufe mit."""

    calls: list[tuple[date, date]] = []

    def __init__(self, **kwargs: Any) -> None:
        pass

    @classmethod
    def reset(cls) -> None:
        cls.calls = []

    async def get_worklogs(self, date_from: date, date_to: date) -> list[WorklogEntry]:
        FakeJiraClient.calls.append((date_from, date_to))
        return [
            WorklogEntry(
                date=date_from,
                ticket="PROJ-1",
                summary="Arbeit",
                author="Tester",
                budget="",
                hours=8.0,
            )
        ]


async def _warte_bis(pilot: Any, bedingung: Callable[[], bool], was: str) -> None:
    """Wartet auf einen ZUSTAND statt auf eine Zeitspanne."""
    grenze = time.monotonic() + _GEDULD_SECONDS
    while not bedingung():
        if time.monotonic() > grenze:
            raise AssertionError(f"{was} - nach {_GEDULD_SECONDS} s nicht eingetreten")
        await pilot.pause()


async def _beruhigen(pilot: Any) -> None:
    """Mehrere Loop-Durchlaeufe fuer die Frage "kommt da noch etwas?"."""
    for _ in range(20):
        await pilot.pause()


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt Einstellungen, Cache und Datenbank nach tmp_path."""
    load_locale("de")
    monkeypatch.setattr(Settings, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(ManualEntryService, "db_path", tmp_path / "manual-entries.db")
    monkeypatch.setattr(cache_service, "CACHE_DIR", tmp_path / "cache")
    FakeJiraClient.reset()
    return tmp_path


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> JiraTimesheetApp:
    """Eine startklare App mit vorgetaeuschtem Jira-Zugang."""
    monkeypatch.setattr("jira_timesheet.app.JiraClient", FakeJiraClient)
    monkeypatch.setattr(JiraTimesheetApp, "_ask_disclaimer", lambda self: None)

    instance = JiraTimesheetApp()
    instance._settings.jira_host = "https://example.atlassian.net"
    instance._settings.email = "test@example.com"
    instance._settings.jira_token = "geheim"
    instance._settings.year = _JAHR
    return instance


def _markup_frei(text: str) -> bool:
    """True, wenn Rich beim Rendern nichts wegnimmt - also kein Markup drinsteckt.

    Bewusst nicht ueber ein selbstgebautes Klammer-Muster: die Frage ist genau,
    ob RICH etwas als Auszeichnung liest, und das beantwortet nur Rich selbst.
    """
    from rich.markup import render

    try:
        return render(text).plain == text
    except Exception:
        return False


@pytest.fixture
def meldungen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Zeichnet jede Meldung auf, die im Jahres-Reiter landet."""
    aufgezeichnet: list[str] = []
    echt = YearPanel.show_message

    def merken(self: YearPanel, message: str) -> None:
        aufgezeichnet.append(message)
        echt(self, message)

    monkeypatch.setattr(YearPanel, "show_message", merken)
    return aufgezeichnet


def _tabs(app: JiraTimesheetApp) -> list[str]:
    """Die Reiter-Kennungen in ihrer Reihenfolge."""
    return [pane.id or "" for pane in app.query_one("#view-tabs", TabbedContent).query("TabPane")]


async def test_jahresansicht_ist_der_dritte_reiter(app: JiraTimesheetApp) -> None:
    """Sie steht direkt hinter dem Kalender - wie in der Qt-Fassung."""
    async with app.run_test() as pilot:
        await pilot.pause()
        assert _tabs(app)[:3] == ["tab-list", "tab-calendar", "tab-year"]


async def test_tab_laeuft_durch_alle_reiter(app: JiraTimesheetApp) -> None:
    """TAB darf keinen Reiter auslassen - und das darf nicht gepflegt werden muessen.

    Die Reihenfolge stand als Liste im Code und lief zweimal aus dem Tritt:
    "Mein Team" und die Jahresansicht waren angelegt, TAB sprang aber an
    beiden vorbei. Der Test zaehlt gegen die tatsaechlich vorhandenen Reiter,
    nicht gegen eine zweite Liste - sonst pflegt man am Ende zwei.
    """
    async with app.run_test() as pilot:
        await pilot.pause()
        vorhanden = _tabs(app)
        app.query_one("#view-tabs", TabbedContent).active = vorhanden[0]
        await pilot.pause()

        besucht = [vorhanden[0]]
        for _ in range(len(vorhanden) - 1):
            app.action_next_tab()
            await pilot.pause()
            besucht.append(app._active_tab())

        assert besucht == vorhanden
        # Und im Kreis: der naechste landet wieder am Anfang.
        app.action_next_tab()
        await pilot.pause()
        assert app._active_tab() == vorhanden[0]


async def test_taste_j_gibt_es_nicht_mehr(app: JiraTimesheetApp) -> None:
    """Die Jahresansicht ist ein Reiter, kein Modal - also keine eigene Taste.

    Geprueft wird die Aktion, nicht der Buchstabe: "j" waere spaeter fuer
    etwas anderes vergeben, ``show_year`` gibt es dagegen ueberhaupt nicht mehr.
    """
    async with app.run_test() as pilot:
        await pilot.pause()
        aktionen = {
            binding.action
            for bindings in app._bindings.key_to_bindings.values()
            for binding in bindings
        }
        assert "show_year" not in aktionen
        assert not hasattr(app, "action_show_year")


async def test_jahr_laedt_nicht_beim_start(app: JiraTimesheetApp) -> None:
    """Beim Start laeuft nur der Monat - zwoelf Monate kosten zu viel Zeit."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        # Genau ein Zeitraum: der laufende Monat aus dem Startabruf.
        assert len(FakeJiraClient.calls) == 1
        assert app._year_loaded_for is None


async def test_erster_blick_in_den_reiter_laedt(app: JiraTimesheetApp) -> None:
    """Der Wechsel in den Reiter stoesst den Abruf an und fuellt die Kacheln."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        FakeJiraClient.calls.clear()

        app.query_one("#view-tabs", TabbedContent).active = "tab-year"
        await _warte_bis(pilot, lambda: app._year_loaded_for == _JAHR, "das Jahr ist geladen")

        # Nur vergangene Monate werden geholt - kuenftige haben nichts zu bieten.
        heute = date.today()
        erwartet = heute.month if heute.year == _JAHR else 12
        assert len(FakeJiraClient.calls) == erwartet

        panel = app.query_one("#year-panel", YearPanel)
        assert panel.year == _JAHR
        assert panel.total_hours > 0
        januar = next(t for t in panel.query(MonthTile) if t._month == 1)
        assert "8,0h" in januar.render().plain


async def test_zweiter_blick_laedt_nicht_erneut(app: JiraTimesheetApp) -> None:
    """Hin- und Herwechseln darf keinen zweiten Abruf ausloesen."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)

        tabs = app.query_one("#view-tabs", TabbedContent)
        tabs.active = "tab-year"
        await _warte_bis(pilot, lambda: app._year_loaded_for == _JAHR, "das Jahr ist geladen")
        nach_dem_ersten = len(FakeJiraClient.calls)

        tabs.active = "tab-list"
        await pilot.pause()
        tabs.active = "tab-year"
        await _beruhigen(pilot)

        assert len(FakeJiraClient.calls) == nach_dem_ersten


async def test_jahreswechsel_verwirft_den_stand(app: JiraTimesheetApp) -> None:
    """Ein anderes Jahr in den Einstellungen macht den geladenen Stand ungueltig.

    Ohne das zeigte der Reiter weiter die Kacheln des alten Jahres - unter
    einer Ueberschrift, die das neue nennt.
    """
    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        app.query_one("#view-tabs", TabbedContent).active = "tab-year"
        await _warte_bis(pilot, lambda: app._year_loaded_for == _JAHR, "das Jahr ist geladen")

        app._on_settings_closed({"year": _JAHR - 1})
        await _warte_bis(
            pilot,
            lambda: app._year_loaded_for == _JAHR - 1,
            "das neue Jahr ist geladen",
        )
        assert app.query_one("#year-panel", YearPanel).year == _JAHR - 1


async def test_manuelle_buchung_verwirft_den_stand(app: JiraTimesheetApp) -> None:
    """Die Jahressumme enthaelt die manuellen Zeiten - eine neue macht sie falsch."""
    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        app.query_one("#view-tabs", TabbedContent).active = "tab-year"
        await _warte_bis(pilot, lambda: app._year_loaded_for == _JAHR, "das Jahr ist geladen")

        app.query_one("#view-tabs", TabbedContent).active = "tab-list"
        await pilot.pause()
        app._reload_after_manual_change()
        assert app._year_loaded_for is None


async def test_kennzahlen_zeigen_das_jahr_nicht_den_monat(app: JiraTimesheetApp) -> None:
    """Unter einem Jahresraster duerfen keine Monatszahlen stehen.

    Beide Leisten benutzen dieselben Beschriftungen ("Ist", "Soll") - stuende
    dort der Monat, waere der Unterschied nicht zu sehen, nur zu ahnen.

    Geprueft wird ueber den Reiterwechsel HIN UND ZURUECK: nach dem Laden
    setzt der Abruf die Leiste selbst, das sagt noch nichts darueber, ob der
    Wechsel es auch tut. Erst der Weg zurueck in die Liste und wieder her
    trennt beide Wege voneinander.
    """
    async with app.run_test(size=(180, 55)) as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        tabs = app.query_one("#view-tabs", TabbedContent)
        tabs.active = "tab-year"
        await _warte_bis(pilot, lambda: app._year_loaded_for == _JAHR, "das Jahr ist geladen")

        tabs.active = "tab-list"
        await pilot.pause()
        monat = app.query_one("#summary-panel", SummaryPanel).render_line(0).text
        # Der Tagesdurchschnitt steht nur in der Monatsleiste - er ist das
        # Unterscheidungsmerkmal, die Beschriftungen sind es nicht.
        assert "Ø" in monat

        tabs.active = "tab-year"
        await pilot.pause()
        jahr = app.query_one("#summary-panel", SummaryPanel).render_line(0).text
        assert str(_JAHR) in jahr
        assert "Ø" not in jahr

        panel = app.query_one("#year-panel", YearPanel)
        assert panel.total_hours > 8.0


async def test_meldungen_im_reiter_tragen_kein_markup(
    app: JiraTimesheetApp, meldungen: list[str]
) -> None:
    """Im Reiter steht Klartext, keine Rich-Auszeichnung.

    Die log.*-Texte tragen Markup ("[bold]Lade Jahresdaten ...[/bold]"), weil
    das Log-Panel es aufloest. Der Reiter zeigt ein Text-Objekt und loest
    NICHTS auf - dieselbe Zeichenkette stuende dort mit Klammern.
    """
    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        app.query_one("#view-tabs", TabbedContent).active = "tab-year"
        await _warte_bis(pilot, lambda: app._year_loaded_for == _JAHR, "das Jahr ist geladen")

    assert meldungen, "es kam ueberhaupt keine Meldung im Reiter an"
    mit_markup = [m for m in meldungen if not _markup_frei(m)]
    assert not mit_markup, f"Rich-Markup in der Reiter-Meldung: {mit_markup}"


async def test_fehlermeldung_im_reiter_traegt_kein_markup(
    app: JiraTimesheetApp, meldungen: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auch der Fehlerfall - dort war log.error mit [red bold] im Einsatz."""

    class KaputterClient(FakeJiraClient):
        async def get_worklogs(self, date_from: date, date_to: date) -> list[WorklogEntry]:
            raise RuntimeError("Netz weg")

    monkeypatch.setattr("jira_timesheet.app.JiraClient", KaputterClient)

    async with app.run_test() as pilot:
        await pilot.pause()
        await _beruhigen(pilot)
        app.query_one("#view-tabs", TabbedContent).active = "tab-year"
        await _warte_bis(
            pilot,
            lambda: any("Netz weg" in m for m in meldungen),
            "die Fehlermeldung steht im Reiter",
        )

    mit_markup = [m for m in meldungen if not _markup_frei(m)]
    assert not mit_markup, f"Rich-Markup in der Reiter-Meldung: {mit_markup}"
    # Und der Reiter bleibt nicht mit "Lade ..." stehen.
    assert "Netz weg" in meldungen[-1]


async def test_fehlender_zugang_meldet_im_reiter_ohne_markup(
    app: JiraTimesheetApp, meldungen: list[str]
) -> None:
    """Ohne Jira-Zugang steht der Hinweis im Reiter, ebenfalls als Klartext."""
    app._settings.jira_token = ""

    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#view-tabs", TabbedContent).active = "tab-year"
        await _warte_bis(pilot, lambda: bool(meldungen), "der Hinweis steht im Reiter")

    assert app._year_loaded_for is None
    mit_markup = [m for m in meldungen if not _markup_frei(m)]
    assert not mit_markup, f"Rich-Markup in der Reiter-Meldung: {mit_markup}"


async def test_stundenzettel_tasten_sind_im_jahresreiter_aus(app: JiraTimesheetApp) -> None:
    """Ohne markierbare Zeile darf die Taste nicht angeboten werden.

    Der Cursor steht in der (unsichtbaren) Liste weiter auf einer Zeile - eine
    Taste, die damit etwas macht, waere eine Falle statt einer Hilfe.
    """
    async with app.run_test() as pilot:
        await pilot.pause()
        tabs = app.query_one("#view-tabs", TabbedContent)

        tabs.active = "tab-list"
        await pilot.pause()
        assert app.check_action("manual_entry", ()) is True

        tabs.active = "tab-year"
        await pilot.pause()
        assert app.check_action("manual_entry", ()) is False
        assert app.check_action("show_details", ()) is False
        assert app.check_action("delete_manual", ()) is None
