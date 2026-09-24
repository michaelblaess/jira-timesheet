"""Zu meinem Team hinzufuegen - Kern (gleich in beiden Fassungen) und TUI."""

from __future__ import annotations

import json
import unittest

import pytest

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import t
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.team import Roster, TeamMember, add_person, from_storage, member_of, to_storage
from jira_timesheet.services.ticket_board import AccountIdError, Ticket
from jira_timesheet.widgets.new_tickets_panel import NewTicketsPanel

ID_A = "712020:aaaaaaaa-0000-0000-0000-00000000000a"
ID_B = "712020:bbbbbbbb-0000-0000-0000-00000000000b"
ID_C = "712020:cccccccc-0000-0000-0000-00000000000c"
ANNA = TeamMember(display_name="Beispiel, Anna", account_ids=(ID_A,))


class TestKern:
    def test_neue_person_kommt_sortiert_dazu(self) -> None:
        alt = Roster(members=[ANNA])
        neu, name, added = add_person(alt, ID_B, "Adler, Bea")
        assert added and name == "Adler, Bea"
        assert [m.display_name for m in neu.members] == ["Adler, Bea", "Beispiel, Anna"]
        assert member_of(neu, ID_B) is not None
        # Die alte Liste bleibt unberuehrt.
        assert [m.display_name for m in alt.members] == ["Beispiel, Anna"]

    def test_bekannte_kennung_aendert_nichts(self) -> None:
        alt = Roster(members=[ANNA])
        neu, name, added = add_person(alt, ID_A, "Anders geschrieben")
        assert not added and name == "Beispiel, Anna" and neu is alt

    def test_gleicher_name_andere_person_bekommt_nummer(self) -> None:
        neu, name, added = add_person(Roster(members=[ANNA]), ID_C, "Beispiel, Anna")
        assert added and name == "Beispiel, Anna (2)"
        assert len(neu.members) == 2

    def test_kaputte_kennung_bricht_ab(self) -> None:
        with pytest.raises(AccountIdError):
            add_person(Roster(), 'a" OR 1=1', "X")


def _ticket() -> Ticket:
    return Ticket(
        key="ABC-1",
        assignee="Beispiel, Anna",
        assignee_id=ID_A,
        reporter="Adler, Bea",
        reporter_id=ID_B,
        url="https://jira.example.com/browse/ABC-1",
    )


def _merkliste(*members: TeamMember) -> None:
    Settings.SETTINGS_FILE.write_text(
        json.dumps({"team_members": to_storage(Roster(members=list(members)))}), encoding="utf-8"
    )


class AnwendungTest(unittest.IsolatedAsyncioTestCase):
    async def test_menue_bietet_nur_fehlende_personen_an(self) -> None:
        _merkliste(ANNA)
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            labels = [e.label for e in app._person_menu_items(_ticket())]
        self.assertIn(t("menu.add_to_team", name="Adler, Bea"), labels)
        self.assertNotIn(t("menu.add_to_team", name="Beispiel, Anna"), labels)

    async def test_screenshot_modus_bietet_niemanden_an(self) -> None:
        _merkliste()
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app._anonymized = True
            labels = [e.label for e in app._person_menu_items(_ticket())]
        self.assertFalse(any(label == t("menu.add_to_team", name="Adler, Bea") for label in labels))

    async def test_menueaktion_nimmt_auf_und_zieht_alles_nach(self) -> None:
        _merkliste(ANNA)
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            items = app._person_menu_items(_ticket())
            aktion = next(e for e in items if e.label == t("menu.add_to_team", name="Adler, Bea"))
            app._menu_ticket = _ticket()
            app._on_board_menu(aktion.id)
            await pilot.pause()
            gespeichert = [m.display_name for m in from_storage(Settings.load().team_members).members]
            self.assertEqual(["Adler, Bea", "Beispiel, Anna"], gespeichert)
            self.assertIn("Adler, Bea", app.query_one("#new-tickets", NewTicketsPanel)._members)
            labels = [e.label for e in app._person_menu_items(_ticket())]
            self.assertNotIn(t("menu.add_to_team", name="Adler, Bea"), labels)
            # Ein zweites Mal legt keinen Doppeleintrag an.
            app.add_person_to_team(ID_B, "Adler, Bea")
            self.assertEqual(2, len(from_storage(Settings.load().team_members).members))
