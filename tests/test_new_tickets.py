"""Tests fuer den Reiter "Neue Tickets" - Kern (gleich wie in der Qt-Fassung) und App."""

from __future__ import annotations

import datetime as dt
import json
import unittest
from typing import Any
from unittest import mock

import pytest
from textual.widgets import Button, DataTable, Select, TabbedContent

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import t
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.new_tickets import (
    ALL_MEMBERS,
    build_new_tickets,
    created_label,
    new_tickets_jql,
    visible_tickets,
    window_start,
)
from jira_timesheet.services.team import TeamMember
from jira_timesheet.services.ticket_board import AccountIdError, BoardConfig

ANNA_ID = "712020:aaaaaaaa-0000-0000-0000-000000000001"
ANNA_ALT = "712020:aaaaaaaa-0000-0000-0000-000000000002"
BERT_ID = "712020:bbbbbbbb-0000-0000-0000-000000000003"
ANNA = TeamMember(display_name="Anna", account_ids=(ANNA_ID, ANNA_ALT))
BERT = TeamMember(display_name="Bert", account_ids=(BERT_ID,))

# Dienstag, 22.09.2026 - der Vortag ist ein Montag.
TUESDAY = dt.date(2026, 9, 22)
MONDAY = dt.date(2026, 9, 21)


def issue(key: str, created: str, reporter_id: str, reporter_name: str = "Jira-Name") -> dict[str, Any]:
    """Ein Suchtreffer, wie Jira ihn liefert."""
    return {
        "key": key,
        "fields": {
            "summary": f"Titel {key}",
            "status": {"name": "Offen", "statusCategory": {"key": "new"}},
            "priority": {"name": "Mittel"},
            "issuetype": {"name": "Aufgabe"},
            "reporter": {"accountId": reporter_id, "displayName": reporter_name},
            "assignee": None,
            "created": created,
            "updated": created,
        },
    }


ISSUES = [
    issue("ABC-10", "2026-09-22T08:14:00.000+0200", ANNA_ID),
    issue("ABC-11", "2026-09-21T16:02:00.000+0200", ANNA_ALT),
    issue("ABC-12", "2026-09-18T10:30:00.000+0200", BERT_ID),
    issue("ABC-13", "2026-09-14T09:00:00.000+0200", BERT_ID),
]


def _tickets() -> list[Any]:
    return build_new_tickets(
        ISSUES, [ANNA, BERT], BoardConfig(), dt.datetime(2026, 9, 22, 9, tzinfo=dt.UTC), "https://jira.example.com"
    )


class TestZeitraum:
    def test_dienstag_zeigt_ab_montag(self) -> None:
        assert window_start(TUESDAY, 1) == MONDAY

    def test_montag_zeigt_ab_freitag(self) -> None:
        # Der eigentliche Grund fuer Arbeitstage: rollende 24 h zeigten nur den Sonntag.
        assert window_start(MONDAY, 1) == dt.date(2026, 9, 18)
        assert window_start(MONDAY, 2) == dt.date(2026, 9, 17)

    def test_wochenende_zaehlt_ab_freitag(self) -> None:
        assert window_start(dt.date(2026, 9, 26), 1) == dt.date(2026, 9, 25)

    def test_sieben_arbeitstage(self) -> None:
        assert window_start(TUESDAY, 7) == dt.date(2026, 9, 11)

    def test_feiertage_zaehlen_nicht(self) -> None:
        # Dienstag nach Ostern 2026: Ostermontag und Karfreitag fallen weg.
        feiertage = {dt.date(2026, 4, 3), dt.date(2026, 4, 6)}

        def arbeitstag(day: dt.date) -> bool:
            return day.weekday() < 5 and day not in feiertage

        assert window_start(dt.date(2026, 4, 7), 1, arbeitstag) == dt.date(2026, 4, 2)

    def test_kaputter_kalender_haengt_nicht(self) -> None:
        assert window_start(TUESDAY, 1, lambda _day: False) == MONDAY


class TestAbfrage:
    def test_alle_kennungen_aller_mitglieder(self) -> None:
        jql = new_tickets_jql([ANNA, BERT, ANNA], dt.date(2026, 9, 11))
        assert jql == (
            f'reporter IN ("{ANNA_ID}", "{ANNA_ALT}", "{BERT_ID}") AND created >= "2026-09-11" ORDER BY created DESC'
        )

    def test_ohne_kennungen_keine_abfrage(self) -> None:
        assert new_tickets_jql([TeamMember(display_name="Leer")], TUESDAY) == ""

    def test_kaputte_kennung_bricht_ab(self) -> None:
        with pytest.raises(AccountIdError):
            new_tickets_jql([TeamMember(display_name="X", account_ids=('a" OR 1=1',))], TUESDAY)


class TestAufbereitung:
    def test_neueste_zuerst_mit_namen_aus_der_merkliste(self) -> None:
        tickets = _tickets()
        assert [t.key for t in tickets] == ["ABC-10", "ABC-11", "ABC-12", "ABC-13"]
        # Auch das Zweitkonto fuehrt zum Namen der Merkliste.
        assert [t.reporter for t in tickets] == ["Anna", "Anna", "Bert", "Bert"]
        assert tickets[0].url == "https://jira.example.com/browse/ABC-10"

    def test_doppelte_treffer_einmal(self) -> None:
        tickets = build_new_tickets([*ISSUES, ISSUES[0]], [ANNA, BERT], BoardConfig(), dt.datetime.now(dt.UTC))
        assert len(tickets) == 4

    def test_filter_nach_person_und_zeitraum(self) -> None:
        tickets = _tickets()
        assert [t.key for t in visible_tickets(tickets, ALL_MEMBERS, MONDAY)] == ["ABC-10", "ABC-11"]
        assert [t.key for t in visible_tickets(tickets, "Bert", dt.date(2026, 9, 11))] == ["ABC-12", "ABC-13"]
        assert visible_tickets(tickets, "Bert", MONDAY) == []

    def test_beschriftung_der_anlage(self) -> None:
        tz = dt.timezone(dt.timedelta(hours=2))
        assert created_label(dt.datetime(2026, 9, 22, 8, 14, tzinfo=tz), TUESDAY) == "heute 08:14"
        assert created_label(dt.datetime(2026, 9, 21, 16, 2, tzinfo=tz), TUESDAY) == "gestern 16:02"
        assert created_label(dt.datetime(2026, 9, 18, 10, 30, tzinfo=tz), TUESDAY) == "Fr 18.09. 10:30"
        assert created_label(None, TUESDAY) == ""


def _schreibe_einstellungen(**extra: Any) -> None:
    daten: dict[str, Any] = {
        "jira_host": "https://jira.example.com",
        "email": "max@example.com",
        "jira_token": "geheim",
        "team_members": [
            {"display_name": "Anna", "account_ids": [ANNA_ID, ANNA_ALT]},
            {"display_name": "Bert", "account_ids": [BERT_ID]},
        ],
    }
    daten.update(extra)
    Settings.SETTINGS_FILE.write_text(json.dumps(daten), encoding="utf-8")


class _Abruf:
    """Ersetzt load_new_tickets - haelt die Aufrufe fest und liefert die Testliste."""

    def __init__(self) -> None:
        self.aufrufe: list[tuple[list[str], dt.date]] = []

    async def __call__(self, settings: Any, config: Any, members: Any, since: dt.date, on_log: Any = None) -> list[Any]:
        self.aufrufe.append(([m.display_name for m in members], since))
        return _tickets()


def _zeilen(app: JiraTimesheetApp) -> list[str]:
    table = app.query_one("#new-data", DataTable)
    return [str(table.get_row_at(i)[0]) for i in range(table.row_count)]


class AnwendungTest(unittest.IsolatedAsyncioTestCase):
    """Der Reiter in der laufenden Anwendung."""

    async def asyncSetUp(self) -> None:
        self.abruf = _Abruf()
        patcher = mock.patch("jira_timesheet.app.load_new_tickets", self.abruf)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def _oeffnen(self, app: JiraTimesheetApp, pilot: Any) -> None:
        app._new_panel().set_clock(lambda: TUESDAY)
        # Erst den Startfokus abwarten: kommt er unter Last nach dem Wechsel,
        # holt er den Stundenzettel-Reiter zurueck, und es wird nie geladen.
        await self._startfokus_abwarten(app, pilot)
        app.query_one("#view-tabs", TabbedContent).active = "tab-new"
        # Warten, bis die Liste wirklich da ist - unter Last startet der Worker
        # erst nach dem ersten pause(), ein wait_for_complete kaeme zu frueh.
        # Zeitbasiert, bis zu 10 s: unter Last reichten 30 Schritte nicht.
        # Schluss ist, sobald die Liste da ist oder die App bewusst nicht laedt.
        panel = app._new_panel()
        for _ in range(200):
            await pilot.pause(0.05)
            if panel.tickets is not None:
                break
            if not app._new_loaded and panel._message != t("new.not_loaded"):
                break
        await app.workers.wait_for_complete()
        await pilot.pause()

    async def test_reiter_steht_hinter_mein_team(self) -> None:
        _schreibe_einstellungen()
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            reiter = [p.id for p in app.query_one("#view-tabs", TabbedContent).query("TabPane")]
            self.assertEqual(reiter.index("tab-new"), reiter.index("tab-team") + 1)

    async def test_ein_abruf_danach_filtert_es_lokal(self) -> None:
        _schreibe_einstellungen()
        app = JiraTimesheetApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await self._oeffnen(app, pilot)
            self.assertEqual(1, len(self.abruf.aufrufe))
            namen, seit = self.abruf.aufrufe[0]
            self.assertEqual(["Anna", "Bert"], namen)
            self.assertEqual(dt.date(2026, 9, 11), seit)
            self.assertEqual(["ABC-10", "ABC-11"], _zeilen(app))
            tab = app.query_one("#view-tabs", TabbedContent).get_tab("tab-new")
            self.assertIn("(2)", str(tab.label))

            app.query_one("#new-window-7T", Button).press()
            await pilot.pause()
            self.assertEqual(["ABC-10", "ABC-11", "ABC-12", "ABC-13"], _zeilen(app))
            app.query_one("#new-member", Select).value = "Bert"
            await pilot.pause()
            self.assertEqual(["ABC-12", "ABC-13"], _zeilen(app))
            # Zweiter Besuch laedt nicht erneut.
            tabs = app.query_one("#view-tabs", TabbedContent)
            tabs.active = "tab-list"
            await pilot.pause()
            tabs.active = "tab-new"
            await pilot.pause()
            self.assertEqual(1, len(self.abruf.aufrufe))
            self.assertEqual("7T", Settings.load().new_tickets_window)

    async def test_leere_merkliste_sagt_wo_man_sie_fuellt(self) -> None:
        _schreibe_einstellungen(team_members=[])
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            await self._oeffnen(app, pilot)
            self.assertEqual([], self.abruf.aufrufe)
            self.assertIsNone(app._new_panel().tickets)

    async def test_screenshot_modus_zeigt_keine_echten_nummern(self) -> None:
        _schreibe_einstellungen()
        app = JiraTimesheetApp()
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await self._oeffnen(app, pilot)
            app.action_toggle_anon()
            await pilot.pause()
            self.assertTrue(all(not key.startswith("ABC-") for key in _zeilen(app)))
            # Gefiltert wird weiter auf den echten Namen.
            app._new_panel().set_window("7T")
            app._new_panel().select_member("Bert")
            self.assertEqual(2, len(_zeilen(app)))
            app.action_toggle_anon()
            await pilot.pause()
            self.assertEqual(["ABC-12", "ABC-13"], _zeilen(app))

    async def test_startet_auf_wunsch_mit_den_neuen_tickets(self) -> None:
        _schreibe_einstellungen(start_with_new_tickets=True)
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await self._startfokus_abwarten(app, pilot)
            self.assertEqual("tab-new", app.query_one("#view-tabs", TabbedContent).active)

    async def _startfokus_abwarten(self, app: JiraTimesheetApp, pilot: Any) -> None:
        # Nicht warten, bis "tab-new" vorn steht: initial zeigt ihn kurz, und
        # erst der Startfokus entscheidet, ob er bleibt. Also auf den Fokus
        # warten und DANN pruefen - sonst koennte der Test nie scheitern.
        for _ in range(30):
            await pilot.pause()
            if app.focused is not None:
                break
        await pilot.pause()
        await pilot.pause()

    async def test_ohne_einstellung_bleibt_der_stundenzettel(self) -> None:
        _schreibe_einstellungen()
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await self._startfokus_abwarten(app, pilot)
            self.assertEqual("tab-list", app.query_one("#view-tabs", TabbedContent).active)
