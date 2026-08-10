"""Tests der Ansicht "Mein Team" - Abfragen, Kontoauswahl, Merkliste.

Die Zahlen und Faelle stammen aus Messungen gegen eine echte Jira-Instanz am
10.08.2026, nicht aus der Dokumentation. Wo ein Test eine Gegenprobe hat, ist
sie mitgetestet: eine Pruefung, die nicht scheitern kann, belegt nichts.
"""

from __future__ import annotations

import datetime as dt
import json
import unittest

import pytest
from textual.app import App
from textual.widgets import Button, DataTable, Input, Select, Static, TabbedContent

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import load_locale
from jira_timesheet.models.settings import Settings
from jira_timesheet.screens.settings_screen import SettingsScreen
from jira_timesheet.services.team import (
    Roster,
    TeamMember,
    from_storage,
    merge_accounts,
    parse_people,
    parse_search,
    sort_candidates,
    to_storage,
    with_last_touch,
)
from jira_timesheet.services.ticket_board import (
    AccountIdError,
    BoardConfig,
    Marker,
    assigned_jql,
    assignee_clause,
    build_board,
    closing_jql,
    history_jql,
    last_touch_jql,
)
from jira_timesheet.services.ticket_board_loader import (
    MODE_ASSIGNED,
    MODE_TEAM,
    jqls_for,
)
from jira_timesheet.widgets.team_roster_panel import TeamRosterPanel
from jira_timesheet.widgets.ticket_board_table import TicketBoardTable


@pytest.fixture(autouse=True)
def _german_labels() -> None:
    """Echte Beschriftungen laden - sonst stehen die i18n-Schluessel im Kopf.

    Fuer Tests, die Groessen messen, ist das kein Schoenheitsfehler: der
    Schluessel "settings.team_intro" ist einzeilig, der echte Satz dreizeilig.
    Ohne diese Fixture misst ein Sichtbarkeitstest ein Layout, das es im
    Betrieb nicht gibt. Dasselbe Muster steht in test_ticket_board_ui und
    test_widgets - beim Anlegen dieser Datei war es uebersehen worden.
    """
    load_locale("de")


# Kennungen im Format der vermessenen Instanz: 24 Zeichen alt, 43 Zeichen neu.
ID_A = "5cf79d64eba18b0ea85a7b53"
ID_B = "712020:e1153ec2-3116-4efb-bb7e-f94d2617a14a"
ID_C = "630f1a2b3c4d5e6f70819200"


def _user(
    account_id: str,
    name: str,
    mail: str = "",
    active: bool = True,
    kind: str = "atlassian",
) -> dict[str, object]:
    """Baut einen Treffer, wie ihn /user/search liefert."""
    entry: dict[str, object] = {
        "accountId": account_id,
        "displayName": name,
        "active": active,
        "accountType": kind,
        "avatarUrls": {"48x48": f"https://example.invalid/{account_id}.png"},
    }
    if mail:
        entry["emailAddress"] = mail
    return entry


class AbfragenTest(unittest.TestCase):
    """Die JQL-Bauer mit und ohne fremde Kennung."""

    def test_ohne_kennung_bleibt_es_bei_currentuser(self) -> None:
        self.assertEqual("assignee = currentUser()", assignee_clause())
        self.assertIn("assignee = currentUser()", assigned_jql())
        self.assertIn("assignee = currentUser()", closing_jql(("Schliessen",)))

    def test_eine_kennung_nutzt_trotzdem_die_mengenform(self) -> None:
        # Bewusst IN statt "=", damit die Abfrage unveraendert bleibt, wenn
        # spaeter ein zweites Konto derselben Person dazukommt.
        self.assertEqual(f'assignee IN ("{ID_A}")', assignee_clause([ID_A]))

    def test_mehrere_kennungen_landen_alle_im_ausdruck(self) -> None:
        klausel = assignee_clause([ID_A, ID_B, ID_C])
        for kennung in (ID_A, ID_B, ID_C):
            self.assertIn(f'"{kennung}"', klausel)
        self.assertTrue(klausel.startswith("assignee IN ("))

    def test_unbrauchbare_kennung_bricht_ab_statt_sie_zu_uebergehen(self) -> None:
        # Eine uebersprungene Kennung liefert ein unvollstaendiges Ergebnis,
        # das wie ein vollstaendiges aussieht. Deshalb Abbruch.
        with self.assertRaises(AccountIdError):
            assignee_clause([ID_A, 'boese" OR key = "PROJ-1'])

    def test_kennung_wandert_in_beide_ansichten(self) -> None:
        self.assertIn(f'"{ID_A}"', assigned_jql([ID_A]))
        self.assertIn(f'"{ID_A}"', closing_jql(("Schliessen",), [ID_A]))

    def test_auswertung_kennt_keine_fremde_kennung(self) -> None:
        # Durchsatz je Monat ueber eine andere Person waere eine
        # Leistungskennzahl. history_jql darf deshalb gar keinen Parameter
        # haben - dieser Test scheitert, sobald jemand einen einbaut.
        self.assertIn("currentUser()", history_jql())
        with self.assertRaises(TypeError):
            history_jql(ID_A)  # type: ignore[call-arg]

    def test_letzter_kontakt_sortiert_absteigend(self) -> None:
        ausdruck = last_touch_jql(ID_A)
        self.assertIn(f'assignee = "{ID_A}"', ausdruck)
        self.assertIn("ORDER BY updated DESC", ausdruck)

    def test_letzter_kontakt_prueft_die_kennung(self) -> None:
        with self.assertRaises(AccountIdError):
            last_touch_jql('" OR key = "PROJ-1')


class KontoauswahlTest(unittest.TestCase):
    """Mehrere Konten je Person - der am 10.08.2026 gemessene Fall."""

    def _kandidaten(self) -> list[object]:
        """Die drei Konten eines Kollegen, wie am 10.08.2026 vermessen."""
        treffer = parse_search(
            [
                _user(ID_A, "Reinhold Beispiel"),
                _user(ID_B, "Beispiel, Reinhold", "vorname.nachname@example.invalid"),
                _user(ID_C, "Reiner Beispiel"),
            ]
        )
        stempel = {
            ID_A: "2026-04-16T09:00:00.000+0200",
            ID_B: "2026-08-05T09:00:00.000+0200",
            ID_C: "2026-07-30T09:00:00.000+0200",
        }
        return [
            with_last_touch(k, [{"fields": {"updated": stempel[k.account_id]}}])
            for k in treffer
        ]

    def test_juengstes_konto_gewinnt_nicht_das_groesste(self) -> None:
        # Der Kern des gemessenen Falls: das aktuelle Konto trug zwei Tickets,
        # ein stillgelegtes achtzehn. Wer nach Menge sortiert, liegt falsch.
        sortiert = sort_candidates(self._kandidaten())  # type: ignore[arg-type]
        self.assertEqual(ID_B, sortiert[0].account_id)
        self.assertEqual(ID_C, sortiert[1].account_id)
        self.assertEqual(ID_A, sortiert[2].account_id)

    def test_konto_ohne_jedes_ticket_landet_hinten(self) -> None:
        treffer = parse_search([_user(ID_A, "Ohne Ticket"), _user(ID_B, "Mit Ticket")])
        mit = with_last_touch(
            treffer[1], [{"fields": {"updated": "2026-08-05T09:00:00.000+0200"}}]
        )
        ohne = with_last_touch(treffer[0], [])
        self.assertIsNone(ohne.last_touch)
        self.assertEqual(ID_B, sort_candidates([ohne, mit])[0].account_id)

    def test_zusammenfassen_haelt_alle_kennungen(self) -> None:
        mitglied = merge_accounts(self._kandidaten(), name="Reiner Beispiel")  # type: ignore[arg-type]
        self.assertEqual("Reiner Beispiel", mitglied.display_name)
        self.assertEqual((ID_B, ID_C, ID_A), mitglied.account_ids)

    def test_eigener_name_schlaegt_den_aus_jira(self) -> None:
        # Jira fuehrt denselben Menschen unter drei Schreibweisen. Wie jemand
        # genannt werden moechte, entscheidet nicht das Verzeichnis.
        ohne = merge_accounts(self._kandidaten())  # type: ignore[arg-type]
        self.assertEqual("Beispiel, Reinhold", ohne.display_name)

    def test_mitglied_ohne_konto_wird_abgelehnt(self) -> None:
        with self.assertRaises(ValueError):
            merge_accounts([])

    def test_mailadresse_wird_uebernommen_wenn_irgendein_konto_sie_zeigt(self) -> None:
        mitglied = merge_accounts(self._kandidaten())  # type: ignore[arg-type]
        self.assertEqual("vorname.nachname@example.invalid", mitglied.email)


class PersonensucheTest(unittest.TestCase):
    """Was aus den Antworten gelesen wird und was nicht."""

    def test_stillgelegte_und_maschinenkonten_fallen_raus(self) -> None:
        treffer = parse_search(
            [
                _user(ID_A, "Aktiver Mensch"),
                _user(ID_B, "Stillgelegt", active=False),
                _user(ID_C, "Automat", kind="app"),
            ]
        )
        self.assertEqual([ID_A], [k.account_id for k in treffer])

    def test_konto_ohne_sichtbare_mail_bleibt_brauchbar(self) -> None:
        # Nicht sichtbar heisst nicht: nicht vorhanden. Das Konto mit der
        # meisten Arbeit gab in der Messung keine Adresse heraus - es
        # auszusortieren waere der teuerste denkbare Fehler.
        treffer = parse_search([_user(ID_A, "Ohne Mail")])
        self.assertEqual(1, len(treffer))
        self.assertEqual("", treffer[0].email)
        self.assertTrue(treffer[0].account_id)

    def test_unbrauchbare_kennung_wird_uebergangen(self) -> None:
        self.assertEqual([], parse_search([_user('" OR "', "Boese")]))

    def test_personen_aus_dem_ticketbestand(self) -> None:
        # Der Weg ohne Benutzer-Schnittstelle: die Kennung steht im
        # assignee-Objekt jeder Suchantwort.
        issues = [
            {"fields": {"assignee": _user(ID_B, "Zweite Person", "z@example.invalid")}},
            {"fields": {"assignee": _user(ID_A, "Erste Person")}},
            {"fields": {"assignee": _user(ID_A, "Erste Person")}},
            {"fields": {"assignee": None}},
            {"fields": {}},
        ]
        leute = parse_people(issues)
        self.assertEqual(["Erste Person", "Zweite Person"], [p.display_name for p in leute])
        self.assertEqual("z@example.invalid", leute[1].email)

    def test_avatar_wird_in_groesster_groesse_gelesen(self) -> None:
        treffer = parse_search([_user(ID_A, "Mit Bild")])
        self.assertTrue(treffer[0].avatar_url.endswith(f"{ID_A}.png"))


class MerklisteTest(unittest.TestCase):
    """Speichern und Laden, auch bei verdorbenem Bestand."""

    def test_hin_und_zurueck(self) -> None:
        roster = Roster(
            members=[
                TeamMember(display_name="Reiner Beispiel", account_ids=(ID_A, ID_B)),
                TeamMember(display_name="Anna Muster", account_ids=(ID_C,)),
            ]
        )
        zurueck = from_storage(to_storage(roster))
        # Alphabetisch beim Laden, nicht in Eingabereihenfolge.
        self.assertEqual(
            ["Anna Muster", "Reiner Beispiel"], [m.display_name for m in zurueck.members]
        )
        self.assertEqual((ID_A, ID_B), zurueck.find("Reiner Beispiel").account_ids)  # type: ignore[union-attr]

    def test_verdorbener_bestand_verhindert_den_start_nicht(self) -> None:
        roh = [
            {"display_name": "Gut", "account_ids": [ID_A]},
            {"display_name": "Ohne Konto", "account_ids": []},
            {"display_name": "", "account_ids": [ID_B]},
            {"account_ids": [ID_C]},
            {"display_name": "Boese Kennung", "account_ids": ['" OR "']},
            "kein Eintrag",
        ]
        geladen = from_storage(roh)
        self.assertEqual(["Gut"], [m.display_name for m in geladen.members])

    def test_kein_bestand_ergibt_leere_liste(self) -> None:
        for wert in (None, "", 42, {}):
            self.assertEqual([], from_storage(wert).members)

    def test_suche_ist_unabhaengig_von_gross_und_kleinschreibung(self) -> None:
        roster = Roster(members=[TeamMember(display_name="Reiner Beispiel", account_ids=(ID_A,))])
        self.assertIsNotNone(roster.find("reiner beispiel"))
        self.assertIsNone(roster.find("Niemand"))


class FremdsichtGrenzeTest(unittest.TestCase):
    """Was in der Fremdsicht NICHT entstehen darf."""

    def _issue(self, key: str, reporter: str) -> dict[str, object]:
        """Ein Ticket in einem Rueckgabe-Status mit gegebenem Autor."""
        alt = (dt.datetime.now(dt.UTC) - dt.timedelta(days=90)).strftime(
            "%Y-%m-%dT%H:%M:%S.000+0000"
        )
        return {
            "key": key,
            "fields": {
                "summary": "Beispiel",
                "status": {"name": "In Arbeit", "statusCategory": {"key": "indeterminate"}},
                "priority": {"name": "Medium"},
                "issuetype": {"name": "Task"},
                "reporter": {"accountId": reporter, "displayName": "Autor"},
                "assignee": {"accountId": ID_A, "displayName": "Person"},
                "created": alt,
                "updated": alt,
            },
        }

    def test_ohne_buchungsdaten_kein_pile_of_shame(self) -> None:
        # Fuer fremde Personen werden Worklogs gar nicht erst geholt. Ohne sie
        # darf der Marker nicht gesetzt werden - geraten wird nicht.
        config = BoardConfig(active_status=("In Arbeit",))
        board = build_board(
            [self._issue("PROJ-1", ID_B)], config, account_id=ID_A, account_ids=[ID_A]
        )
        alle = [t for gruppe in board.groups for t in gruppe.tickets]
        self.assertEqual(1, len(alle))
        self.assertNotIn(Marker.PILE_OF_SHAME, alle[0].markers)

    def test_zweites_konto_macht_den_eigenen_vorgang_nicht_fremd(self) -> None:
        # Wer unter Konto A meldet und unter Konto B bearbeitet, meldet nicht
        # sich selbst fremd. Ohne die vollstaendige Kennungsliste passiert
        # genau das.
        config = BoardConfig(active_status=("In Arbeit",))
        board = build_board(
            [self._issue("PROJ-2", ID_B)],
            config,
            account_id=ID_A,
            account_ids=[ID_A, ID_B],
        )
        ticket = [t for gruppe in board.groups for t in gruppe.tickets][0]
        self.assertFalse(ticket.foreign_reporter)

    def test_gegenprobe_fremder_autor_wird_weiterhin_erkannt(self) -> None:
        # Ohne diese Gegenprobe wuerde der Test oben auch dann bestehen, wenn
        # foreign_reporter grundsaetzlich False waere.
        config = BoardConfig(active_status=("In Arbeit",))
        board = build_board(
            [self._issue("PROJ-3", ID_C)],
            config,
            account_id=ID_A,
            account_ids=[ID_A, ID_B],
        )
        ticket = [t for gruppe in board.groups for t in gruppe.tickets][0]
        self.assertTrue(ticket.foreign_reporter)


class VerdrahtungTest(unittest.TestCase):
    """Was der Loader aus einer Ansicht macht."""

    def test_team_ansicht_fragt_die_kennungen_ab(self) -> None:
        mitglied = TeamMember(display_name="Reiner Beispiel", account_ids=(ID_A, ID_B))
        config = BoardConfig(closing_status=("Schliessen",))
        ausdruecke = jqls_for(MODE_TEAM, config, mitglied)("eigene-kennung")
        self.assertEqual(2, len(ausdruecke))
        for ausdruck in ausdruecke:
            self.assertIn(f'"{ID_A}"', ausdruck)
            self.assertIn(f'"{ID_B}"', ausdruck)
            self.assertNotIn("currentUser()", ausdruck)

    def test_team_ansicht_ohne_person_bricht_ab(self) -> None:
        # Ohne Kennung faellt die Abfrage auf currentUser() zurueck. Dann
        # staenden die eigenen Tickets unter fremdem Namen in der Ansicht -
        # ein stiller Fehler, der wie ein Ergebnis aussieht.
        config = BoardConfig()
        with self.assertRaises(ValueError):
            jqls_for(MODE_TEAM, config, None)
        with self.assertRaises(ValueError):
            jqls_for(MODE_TEAM, config, TeamMember(display_name="Ohne Konto"))

    def test_eigene_ansicht_bleibt_unveraendert(self) -> None:
        config = BoardConfig(closing_status=("Schliessen",))
        for ausdruck in jqls_for(MODE_ASSIGNED, config)("eigene-kennung"):
            self.assertIn("currentUser()", ausdruck)


class EinstellungsseiteTest(unittest.IsolatedAsyncioTestCase):
    """Der Reiter "Mein Team" - Anzeige, Uebernahme, Speichern."""

    async def test_merkliste_wird_geladen_und_wieder_eingesammelt(self) -> None:
        vorhanden = [
            {"display_name": "Reiner Beispiel", "account_ids": [ID_A, ID_B]},
            {"display_name": "Anna Muster", "account_ids": [ID_C]},
        ]
        werte = Settings().to_dict()
        werte["team_members"] = vorhanden
        screen = SettingsScreen(werte, lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            # Die Merkliste steht im Entfernen-Auswahlfeld, nicht mehr in
            # einer eigenen Tabelle - die lag ausserhalb des Bildes. Geprueft
            # wird ueber den Wert und nicht ueber Select._options: private
            # Attribute in Tests brechen beim naechsten Textual-Update.
            auswahl = screen.query_one("#team-remove-target", Select)
            self.assertEqual("Anna Muster", str(auswahl.value))
            ergebnis: dict[str, object] = {}
            screen.collect_app_settings(ergebnis)

        gespeichert = ergebnis["team_members"]
        assert isinstance(gespeichert, list)
        # Alphabetisch, nicht in Eingabereihenfolge.
        self.assertEqual(
            ["Anna Muster", "Reiner Beispiel"], [m["display_name"] for m in gespeichert]
        )
        self.assertEqual([ID_A, ID_B], gespeichert[1]["account_ids"])

    async def test_treffer_wird_als_neue_person_uebernommen(self) -> None:
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            panel = screen.query_one(TeamRosterPanel)
            # Die Suche selbst braucht das Netz - hier wird nur ihr Ergebnis
            # eingesetzt, damit die Uebernahme fuer sich pruefbar bleibt.
            panel._hits = parse_search([_user(ID_A, "Beispiel, Reinhold")])
            panel._refresh_hits()
            await pilot.pause()
            screen.query_one("#team-name", Input).value = "Reiner Beispiel"
            screen.query_one("#team-btn-add", Button).press()
            await pilot.pause()

            self.assertEqual(
                "Reiner Beispiel",
                str(screen.query_one("#team-remove-target", Select).value),
            )
            ergebnis: dict[str, object] = {}
            screen.collect_app_settings(ergebnis)

        gespeichert = ergebnis["team_members"]
        assert isinstance(gespeichert, list)
        self.assertEqual("Reiner Beispiel", gespeichert[0]["display_name"])
        self.assertEqual([ID_A], gespeichert[0]["account_ids"])

    async def test_zweites_konto_landet_bei_derselben_person(self) -> None:
        werte = Settings().to_dict()
        werte["team_members"] = [{"display_name": "Reiner Beispiel", "account_ids": [ID_A]}]
        screen = SettingsScreen(werte, lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            panel = screen.query_one(TeamRosterPanel)
            panel._hits = parse_search([_user(ID_B, "Beispiel, Reinhold")])
            panel._refresh_hits()
            await pilot.pause()
            screen.query_one("#team-target", Select).value = "Reiner Beispiel"
            screen.query_one("#team-btn-add", Button).press()
            await pilot.pause()

            # Eine Zeile, aber zwei Konten - nicht zwei Personen.
            self.assertEqual(
                "Reiner Beispiel",
                str(screen.query_one("#team-remove-target", Select).value),
            )
            ergebnis: dict[str, object] = {}
            screen.collect_app_settings(ergebnis)

        gespeichert = ergebnis["team_members"]
        assert isinstance(gespeichert, list)
        self.assertEqual(1, len(gespeichert))
        self.assertEqual({ID_A, ID_B}, set(gespeichert[0]["account_ids"]))

    async def test_dasselbe_konto_kommt_nicht_zweimal_hinein(self) -> None:
        werte = Settings().to_dict()
        werte["team_members"] = [{"display_name": "Reiner Beispiel", "account_ids": [ID_A]}]
        screen = SettingsScreen(werte, lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test() as pilot:
            await pilot.pause()
            panel = screen.query_one(TeamRosterPanel)
            panel._hits = parse_search([_user(ID_A, "Beispiel, Reinhold")])
            panel._refresh_hits()
            await pilot.pause()
            screen.query_one("#team-btn-add", Button).press()
            await pilot.pause()
            ergebnis: dict[str, object] = {}
            screen.collect_app_settings(ergebnis)

        gespeichert = ergebnis["team_members"]
        assert isinstance(gespeichert, list)
        self.assertEqual(1, len(gespeichert))
        self.assertEqual([ID_A], gespeichert[0]["account_ids"])


class TeamTabTest(unittest.IsolatedAsyncioTestCase):
    """Das Auswahlfeld fuer die Person in der Ansicht "Mein Team"."""

    def _app(self, tabelle: TicketBoardTable) -> App[None]:
        class _App(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield tabelle

        return _App()

    async def test_ohne_merkliste_kein_auswahlfeld(self) -> None:
        # Die eigenen Ansichten duerfen kein Personenfeld bekommen - dort
        # gibt es nichts auszuwaehlen.
        tabelle = TicketBoardTable(MODE_ASSIGNED, id="board-assigned")
        async with self._app(tabelle).run_test() as pilot:
            await pilot.pause()
            self.assertEqual(0, len(tabelle.query(f"#board-member-{MODE_ASSIGNED}")))
            self.assertEqual("", tabelle.member)

    async def test_auswahlfeld_zeigt_die_merkliste(self) -> None:
        tabelle = TicketBoardTable(
            MODE_TEAM, members=["Anna Muster", "Reiner Beispiel"], id="board-team"
        )
        async with self._app(tabelle).run_test() as pilot:
            await pilot.pause()
            self.assertEqual("Anna Muster", tabelle.member)

    async def test_wechsel_meldet_sich_bei_der_anwendung(self) -> None:
        # Eine andere Person ist ein anderer Bestand. Das Widget filtert
        # deshalb nicht selbst, sondern bittet um einen neuen Abruf.
        gemeldet: list[str] = []
        tabelle = TicketBoardTable(
            MODE_TEAM, members=["Anna Muster", "Reiner Beispiel"], id="board-team"
        )

        class _App(App[None]):
            def compose(self):  # type: ignore[no-untyped-def]
                yield tabelle

            def on_ticket_board_table_member_changed(
                self, event: TicketBoardTable.MemberChanged
            ) -> None:
                gemeldet.append(event.name)

        async with _App().run_test() as pilot:
            await pilot.pause()
            tabelle.query_one(f"#board-member-{MODE_TEAM}", Select).value = "Reiner Beispiel"
            await pilot.pause()

        self.assertEqual(["Reiner Beispiel"], gemeldet)

    async def test_geaenderte_merkliste_haelt_die_gewaehlte_person(self) -> None:
        tabelle = TicketBoardTable(
            MODE_TEAM, members=["Anna Muster", "Reiner Beispiel"], id="board-team"
        )
        async with self._app(tabelle).run_test() as pilot:
            await pilot.pause()
            tabelle.query_one(f"#board-member-{MODE_TEAM}", Select).value = "Reiner Beispiel"
            await pilot.pause()
            tabelle.set_members(["Anna Muster", "Reiner Beispiel", "Neuer Kollege"])
            await pilot.pause()
            self.assertEqual("Reiner Beispiel", tabelle.member)

    async def test_verschwundene_person_ruecken_nicht_still_auf_jemand_anderen(self) -> None:
        # Wird die gewaehlte Person entfernt, faellt die Auswahl auf den
        # ersten Eintrag - aber sichtbar, nicht unter Beibehaltung des alten
        # Namens im Feld.
        tabelle = TicketBoardTable(
            MODE_TEAM, members=["Anna Muster", "Reiner Beispiel"], id="board-team"
        )
        async with self._app(tabelle).run_test() as pilot:
            await pilot.pause()
            tabelle.query_one(f"#board-member-{MODE_TEAM}", Select).value = "Reiner Beispiel"
            await pilot.pause()
            tabelle.set_members(["Anna Muster"])
            await pilot.pause()
            self.assertEqual("Anna Muster", tabelle.member)


class AnwendungTest(unittest.IsolatedAsyncioTestCase):
    """Die Anwendung mit dem neuen Reiter."""

    async def test_reiter_ist_da_und_traegt_das_personenfeld(self) -> None:
        # Der Beleg, dass die Ansicht wirklich in der Anwendung ankommt:
        # dass ein Widget fuer sich funktioniert, sagt darueber nichts.
        Settings.SETTINGS_FILE.write_text(
            json.dumps(
                {
                    "team_members": [
                        {"display_name": "Reiner Beispiel", "account_ids": [ID_A]}
                    ]
                }
            ),
            encoding="utf-8",
        )
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            reiter = [
                pane.id for pane in app.query_one("#view-tabs", TabbedContent).query("TabPane")
            ]
            self.assertIn("tab-team", reiter)
            # Das Auswahlfeld gehoert genau in diesen einen Reiter.
            self.assertEqual(1, len(app.query(f"#board-member-{MODE_TEAM}")))
            self.assertEqual(0, len(app.query(f"#board-member-{MODE_ASSIGNED}")))

    async def test_ohne_merkliste_wird_nichts_abgerufen(self) -> None:
        # Ein Abruf ohne Person fiele auf currentUser() zurueck und zeigte
        # die eigenen Tickets unter fremder Ueberschrift.
        Settings.SETTINGS_FILE.write_text(json.dumps({}), encoding="utf-8")
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # Das Auswahlfeld ist trotzdem da - nur ohne waehlbare Person.
            # Es erst bei gefuellter Merkliste zu bauen war der Fehler vom
            # 10.08.2026: wer die Liste im laufenden Programm anlegt, saehe
            # das Feld sonst bis zum Neustart nicht.
            self.assertEqual(1, len(app.query(f"#board-member-{MODE_TEAM}")))
            self.assertEqual("", app._board_widget(MODE_TEAM).member)
            self.assertIsNone(app._current_member())

    async def test_merkliste_aus_den_einstellungen_kommt_im_reiter_an(self) -> None:
        # Der zweite Fehler vom 10.08.2026: die gepflegte Merkliste blieb im
        # Einstellungsdialog haengen. Das Widget erfuhr nie davon.
        Settings.SETTINGS_FILE.write_text(json.dumps({}), encoding="utf-8")
        app = JiraTimesheetApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            self.assertIsNone(app._current_member())

            app._on_settings_closed(
                {
                    "team_members": [
                        {"display_name": "Reiner Beispiel", "account_ids": [ID_A]}
                    ]
                }
            )
            await pilot.pause()

            # Nicht nur der gemeldete Name zaehlt: das Auswahlfeld muss
            # tatsaechlich da sein und den Namen fuehren. Ohne diese Pruefung
            # besteht der Test auch dann, wenn es das Feld gar nicht gibt -
            # "member" faellt in dem Fall auf den ersten Namen zurueck.
            felder = app.query(f"#board-member-{MODE_TEAM}")
            self.assertEqual(1, len(felder))
            self.assertEqual(
                "Reiner Beispiel",
                str(app.query_one(f"#board-member-{MODE_TEAM}", Select).value),
            )
            self.assertEqual("Reiner Beispiel", app._board_widget(MODE_TEAM).member)
            mitglied = app._current_member()
            self.assertIsNotNone(mitglied)
            self.assertEqual((ID_A,), mitglied.account_ids)  # type: ignore[union-attr]


class SichtbarkeitTest(unittest.IsolatedAsyncioTestCase):
    """Die Bedienelemente muessen ohne Blaettern erreichbar sein.

    Am 10.08.2026 lagen Trefferliste, Uebernahme und Merkliste komplett
    unterhalb des sichtbaren Bereichs - Michael hat einen Treffer markiert,
    gespeichert, und nichts kam an. Ein Widget, das man nicht sieht, gibt es
    fuer den Benutzer nicht.
    """

    async def test_kernbedienung_passt_auf_dreissig_zeilen(self) -> None:
        # Mit gefuellter Merkliste: bei leerer Liste ist die Seite kuerzer
        # als im Betrieb, und der Test wuerde zu frueh gruen.
        werte = Settings().to_dict()
        werte["team_members"] = [
            {"display_name": f"Person {i}", "account_ids": [f"kennung{i}"]}
            for i in range(5)
        ]
        screen = SettingsScreen(werte, lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        # Die kleinste Groesse, die im Alltag vorkommt.
        async with _App().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            screen.query_one(TabbedContent).active = "settings-tab-team"
            await pilot.pause()
            hoehe = screen.size.height
            unsichtbar = []
            for wid in (
                "team-search",
                "team-btn-search",
                "team-hits",
                "team-state",
                "team-target",
                "team-btn-add",
                "team-remove-target",
                "team-btn-remove",
            ):
                bereich = screen.query_one(f"#{wid}").region
                passt = (
                    bereich.y >= 0
                    and bereich.y + bereich.height <= hoehe
                    and bereich.width > 1
                )
                if not passt:
                    unsichtbar.append(f"{wid} (y={bereich.y}, b={bereich.width})")

        self.assertEqual([], unsichtbar, "nicht ohne Blaettern erreichbar")

    async def test_auswahlfeld_wird_nicht_plattgequetscht(self) -> None:
        # Ohne feste Breite drueckten Eingabefeld und Knopf daneben das
        # Auswahlfeld auf genau eine Spalte - vorhanden, aber unbenutzbar.
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            screen.query_one(TabbedContent).active = "settings-tab-team"
            await pilot.pause()
            breite = screen.query_one("#team-target", Select).region.width

        self.assertGreaterEqual(breite, 20)


    async def test_enter_auf_einem_treffer_uebernimmt_ihn(self) -> None:
        # Der eigentliche Bedienfehler vom 10.08.2026: der Uebernahme-Knopf
        # stand unterhalb des Sichtbaren. Wer einen Treffer markiert und
        # speichert, erwartet ohnehin, dass er damit drin ist.
        screen = SettingsScreen(Settings().to_dict(), lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            screen.query_one(TabbedContent).active = "settings-tab-team"
            await pilot.pause()
            panel = screen.query_one(TeamRosterPanel)
            panel._hits = parse_search([_user(ID_A, "Beispiel, Reinhold")])
            panel._refresh_hits()
            await pilot.pause()

            tabelle = screen.query_one("#team-hits", DataTable)
            tabelle.focus()
            tabelle.move_cursor(row=0)
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()

            ergebnis: dict[str, object] = {}
            screen.collect_app_settings(ergebnis)

        gespeichert = ergebnis["team_members"]
        assert isinstance(gespeichert, list)
        self.assertEqual([ID_A], gespeichert[0]["account_ids"])

    async def test_der_stand_der_merkliste_steht_ueber_dem_falz(self) -> None:
        # Die Merkliste selbst liegt weiter unten. Ohne diese Zeile bleibt
        # nach dem Uebernehmen offen, ob ueberhaupt etwas passiert ist.
        werte = Settings().to_dict()
        werte["team_members"] = [{"display_name": "Anna Muster", "account_ids": [ID_A]}]
        screen = SettingsScreen(werte, lang="de")

        class _App(App[None]):
            def on_mount(self) -> None:
                self.push_screen(screen)

        async with _App().run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            screen.query_one(TabbedContent).active = "settings-tab-team"
            await pilot.pause()
            zeile = screen.query_one("#team-state", Static)
            text = str(zeile.render())
            hoehe = screen.size.height
            sichtbar = zeile.region.y + zeile.region.height <= hoehe

        self.assertIn("Anna Muster", text)
        self.assertTrue(sichtbar, "die Rueckmeldung selbst liegt ausserhalb des Bildes")


if __name__ == "__main__":
    unittest.main()
