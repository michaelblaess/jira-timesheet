"""Pflege der Merkliste "Mein Team" in den Einstellungen.

Gesucht wird ueber den Namen, nicht ueber die Mailadresse. Der Grund steht in
services.team: von 63 vermessenen Personen gaben nur 46 eine Adresse heraus,
und ausgerechnet das Konto mit der meisten Arbeit gehoerte zu denen, die
keine zeigen.

Die Trefferliste fuehrt deshalb zwei Spalten, die woanders fehlen: die Zahl
der offenen Tickets und den Zeitpunkt der juengsten Aenderung. Erst beide
zusammen machen die Auswahl entscheidbar, wenn eine Person mehrere Konten
fuehrt - das aktuelle ist NICHT zwingend das groesste.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from textual import on, work
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from jira_timesheet.i18n import t
from jira_timesheet.services.jira_client import JiraClient, JiraClientError
from jira_timesheet.services.team import (
    AccountCandidate,
    Roster,
    from_storage,
    merge_accounts,
    parse_search,
    sort_candidates,
    to_storage,
    with_last_touch,
)
from jira_timesheet.services.ticket_board import assigned_jql, last_touch_jql

# Wert des Auswahlfelds fuer "als neue Person uebernehmen".
NEW_PERSON = "__neu__"

# Liefert Host, Mailadresse, Token und Proxy aus den aktuellen Eingabefeldern.
# Als Rueckruf, damit das Panel den Einstellungs-Bildschirm nicht kennen muss
# und frisch eingetippte Zugangsdaten sofort greifen.
Credentials = Callable[[], tuple[str, str, str, str]]


class TeamRosterPanel(Vertical):
    """Suchen, uebernehmen, entfernen - die Merkliste in einem Widget."""

    def __init__(self, stored: list[dict[str, object]], credentials: Credentials) -> None:
        """Baut das Panel auf.

        Args:
            stored:
                Die gespeicherte Merkliste in ihrer Speicherform.
            credentials:
                Rueckruf fuer die aktuellen Zugangsdaten.
        """
        super().__init__(id="team-panel")
        self._roster: Roster = from_storage(stored)
        self._credentials = credentials
        self._hits: list[AccountCandidate] = []

    def compose(self):  # type: ignore[no-untyped-def] # Textual-Signatur
        """Baut die Oberflaeche des Panels."""
        yield Static(t("settings.team_intro"), classes="hint")

        with Horizontal(classes="team-row"):
            yield Input(placeholder=t("settings.team_search_ph"), id="team-search")
            yield Button(t("settings.team_search"), id="team-btn-search")

        yield DataTable(id="team-hits", cursor_type="row")
        yield Static(t("settings.team_hits_empty"), id="team-hits-note", classes="hint")

        with Horizontal(classes="team-row"):
            yield Label(t("settings.team_add_as"))
            # Die erste Option steht schon hier: Textual lehnt ein leeres
            # Auswahlfeld ab, wenn es keinen Leerwert haben darf.
            yield Select(
                [(t("settings.team_new_person"), NEW_PERSON)],
                value=NEW_PERSON,
                id="team-target",
                allow_blank=False,
            )
            yield Input(placeholder=t("settings.team_name_ph"), id="team-name")
            yield Button(t("settings.team_add"), id="team-btn-add", variant="primary")

        yield Static(t("settings.team_roster"), classes="team-heading")
        yield DataTable(id="team-roster", cursor_type="row")
        yield Button(t("settings.team_remove"), id="team-btn-remove")

    def on_mount(self) -> None:
        """Setzt die Spaltenkoepfe und zeigt den gespeicherten Stand."""
        hits = self.query_one("#team-hits", DataTable)
        hits.add_columns(
            t("settings.team_col_name"),
            t("settings.team_col_mail"),
            t("settings.team_col_open"),
            t("settings.team_col_last"),
        )
        roster = self.query_one("#team-roster", DataTable)
        roster.add_columns(
            t("settings.team_col_name"),
            t("settings.team_col_accounts"),
            t("settings.team_col_mail"),
        )
        self._refresh_roster()

    # --- Aussenschnittstelle ------------------------------------------

    def storage(self) -> list[dict[str, object]]:
        """Liefert die Merkliste in ihrer Speicherform."""
        return to_storage(self._roster)

    # --- Suche ---------------------------------------------------------

    @on(Button.Pressed, "#team-btn-search")
    def _on_search_pressed(self) -> None:
        """Startet die Suche ueber den Knopf."""
        self._start_search()

    @on(Input.Submitted, "#team-search")
    def _on_search_submitted(self) -> None:
        """Startet die Suche mit der Eingabetaste."""
        self._start_search()

    def _start_search(self) -> None:
        """Prueft die Eingabe und stoesst die Suche an."""
        query = self.query_one("#team-search", Input).value.strip()
        if not query:
            return
        host, email, token, proxy = self._credentials()
        if not host or not email or not token:
            self.notify(t("settings.team_need_creds"), severity="warning")
            return
        self.notify(t("settings.team_searching"))
        self._search(query, host, email, token, proxy)

    @work(exclusive=True)
    async def _search(
        self, query: str, host: str, email: str, token: str, proxy: str
    ) -> None:
        """Sucht Konten und reichert sie um Anzahl und juengstes Datum an.

        Args:
            query:
                Der Suchbegriff, ueblicherweise ein Nachname.
            host:
                Basis-URL der Instanz.
            email:
                Anmeldeadresse fuer die Abfrage.
            token:
                API-Token.
            proxy:
                Optionaler Proxy.
        """
        client = JiraClient(host=host, email=email, token=token, legacy=False, proxy=proxy)
        try:
            found = parse_search(await client.fetch_people(query))
            facts = await client.fetch_account_facts(
                [c.account_id for c in found],
                lambda aid: assigned_jql([aid]),
                last_touch_jql,
            )
        except JiraClientError as exc:
            self.notify(str(exc), severity="error")
            return
        except Exception as exc:  # noqa: BLE001 - jede Netzwerkpanne als Hinweis
            self.notify(str(exc), severity="error")
            return

        angereichert: list[AccountCandidate] = []
        for kandidat in found:
            zahlen = facts.get(kandidat.account_id)
            if zahlen is None:
                # Abruf gescheitert: Spalten bleiben leer statt geraten.
                angereichert.append(kandidat)
                continue
            offen, juengst = zahlen
            mit_datum = with_last_touch(kandidat, juengst)
            angereichert.append(
                AccountCandidate(
                    account_id=mit_datum.account_id,
                    display_name=mit_datum.display_name,
                    email=mit_datum.email,
                    avatar_url=mit_datum.avatar_url,
                    open_count=offen,
                    last_touch=mit_datum.last_touch,
                )
            )

        self._hits = sort_candidates(angereichert)
        self._refresh_hits()
        if not self._hits:
            self.notify(t("settings.team_no_hits"), severity="warning")
        else:
            self.notify(t("settings.team_hits", count=len(self._hits)))

    # --- Uebernehmen und Entfernen -------------------------------------

    @on(Button.Pressed, "#team-btn-add")
    def _on_add_pressed(self) -> None:
        """Uebernimmt das gewaehlte Konto in die Merkliste."""
        kandidat = self._selected_hit()
        if kandidat is None:
            self.notify(t("settings.team_pick_hit"), severity="warning")
            return

        bereits = {
            kennung for m in self._roster.members for kennung in m.account_ids
        }
        if kandidat.account_id in bereits:
            self.notify(t("settings.team_duplicate"), severity="warning")
            return

        wunschname = self.query_one("#team-name", Input).value.strip()
        ziel = str(self.query_one("#team-target", Select).value or NEW_PERSON)

        if ziel == NEW_PERSON:
            mitglied = merge_accounts([kandidat], name=wunschname)
            self._roster.members.append(mitglied)
            self.notify(t("settings.team_added", name=mitglied.display_name))
        else:
            vorhanden = self._roster.find(ziel)
            if vorhanden is None:
                self.notify(t("settings.team_pick_member"), severity="warning")
                return
            index = self._roster.members.index(vorhanden)
            erweitert = merge_accounts(
                [
                    *self._known_candidates(vorhanden.account_ids),
                    kandidat,
                ],
                name=wunschname or vorhanden.display_name,
            )
            self._roster.members[index] = erweitert
            self.notify(
                t(
                    "settings.team_extended",
                    name=erweitert.display_name,
                    count=len(erweitert.account_ids),
                )
            )

        self.query_one("#team-name", Input).value = ""
        self._refresh_roster()

    @on(Button.Pressed, "#team-btn-remove")
    def _on_remove_pressed(self) -> None:
        """Nimmt die gewaehlte Person aus der Merkliste."""
        tabelle = self.query_one("#team-roster", DataTable)
        zeile = tabelle.cursor_row
        if zeile is None or not (0 <= zeile < len(self._roster.members)):
            self.notify(t("settings.team_pick_member"), severity="warning")
            return
        entfernt = self._roster.members.pop(zeile)
        self.notify(t("settings.team_removed", name=entfernt.display_name))
        self._refresh_roster()

    # --- Innere Helfer --------------------------------------------------

    def _known_candidates(self, account_ids: tuple[str, ...]) -> list[AccountCandidate]:
        """Baut aus bekannten Kennungen wieder Kandidaten.

        Die Reihenfolge der gespeicherten Kennungen ist bereits die nach
        Aktualitaet sortierte. Sie wird hier ueber absteigende Ersatzdaten
        erhalten, damit ein hinzukommendes Konto sich korrekt einsortiert,
        ohne dass alle alten Datumsangaben neu geholt werden muessen.
        """
        basis = dt.datetime(2000, 1, 1, tzinfo=dt.UTC)
        return [
            AccountCandidate(
                account_id=kennung,
                display_name="",
                last_touch=basis - dt.timedelta(days=rang),
            )
            for rang, kennung in enumerate(account_ids)
        ]

    def _selected_hit(self) -> AccountCandidate | None:
        """Liefert das in der Trefferliste markierte Konto."""
        if not self._hits:
            return None
        zeile = self.query_one("#team-hits", DataTable).cursor_row
        if zeile is None or not (0 <= zeile < len(self._hits)):
            return None
        return self._hits[zeile]

    def _refresh_hits(self) -> None:
        """Zeichnet die Trefferliste neu."""
        tabelle = self.query_one("#team-hits", DataTable)
        tabelle.clear()
        for kandidat in self._hits:
            tabelle.add_row(
                kandidat.display_name,
                kandidat.email or t("settings.team_no_mail"),
                "-" if kandidat.open_count is None else str(kandidat.open_count),
                self._datum(kandidat.last_touch),
            )
        note = self.query_one("#team-hits-note", Static)
        note.display = not self._hits

    def _refresh_roster(self) -> None:
        """Zeichnet die Merkliste neu und fuellt das Auswahlfeld."""
        self._roster.members.sort(key=lambda m: m.display_name.casefold())
        tabelle = self.query_one("#team-roster", DataTable)
        tabelle.clear()
        for mitglied in self._roster.members:
            tabelle.add_row(
                mitglied.display_name,
                str(len(mitglied.account_ids)),
                mitglied.email or t("settings.team_no_mail"),
            )

        auswahl = self.query_one("#team-target", Select)
        auswahl.set_options(
            [
                (t("settings.team_new_person"), NEW_PERSON),
                *((m.display_name, m.display_name) for m in self._roster.members),
            ]
        )
        auswahl.value = NEW_PERSON

    @staticmethod
    def _datum(stamp: dt.datetime | None) -> str:
        """Formatiert einen Zeitpunkt deutsch, leer wird zu "nie"."""
        return stamp.strftime("%d.%m.%Y") if stamp else t("settings.team_never")
