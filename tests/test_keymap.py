"""Tests der umschaltbaren Tastenbelegung.

Die Mechanik selbst ist in `textual-widgets` geprueft. Hier steht, was diese
Anwendung ausmacht: dass die Bestandstabelle zur Anwendung passt, dass beide
Stile das Erwartete binden und dass die Vim-Ebene an den Tabellen wirklich
ankommt.
"""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult
from textual_widgets.keymap import KeymapStyle, find_collisions

from jira_timesheet import keymap
from jira_timesheet.models.settings import Settings
from jira_timesheet.widgets.resizable_data_table import ResizableDataTable

# --- Die Tabelle der Anwendung --------------------------------------------------


def test_bestandstabelle_ist_kollisionsfrei() -> None:
    assert find_collisions(keymap.CLASSIC) == ()


def test_jede_aktion_hat_eine_beschriftung() -> None:
    ohne = [action for action in keymap.CLASSIC if action not in keymap.LABEL_KEYS]
    assert ohne == []


def test_jede_beschriftung_gehoert_zu_einer_aktion() -> None:
    # Gegenrichtung: eine verwaiste Beschriftung heisst, dass eine Aktion
    # entfernt wurde und der Schluessel liegen blieb.
    verwaist = [action for action in keymap.LABEL_KEYS if action not in keymap.CLASSIC]
    assert verwaist == []


def test_beide_stile_sind_kollisionsfrei() -> None:
    for stil in KeymapStyle:
        ergebnis = keymap.resolve(Settings(keymap_style=stil.value))
        assert ergebnis.problems == (), f"{stil.value}: {[p.message for p in ergebnis.problems]}"


# --- Die Stile ------------------------------------------------------------------


def test_klassisch_laesst_alles_wie_bisher() -> None:
    ergebnis = keymap.resolve(Settings(keymap_style="classic"))
    assert ergebnis.bindings["show_settings"].keys == ("s", "S")
    assert ergebnis.bindings["show_about"].keys == ("i", "I")
    assert ergebnis.bindings["toggle_log"].keys == ("l", "L")
    assert ergebnis.bindings["focus_filter"].keys == ("slash",)


def test_f_tasten_treten_neben_die_buchstaben() -> None:
    ergebnis = keymap.resolve(Settings(keymap_style="function_keys"))
    assert ergebnis.bindings["show_settings"].keys == ("f2", "s", "S")
    assert ergebnis.bindings["show_about"].keys == ("f1", "i", "I")
    assert ergebnis.bindings["focus_filter"].keys == ("f3", "slash")


def test_nur_das_log_verliert_seinen_buchstaben() -> None:
    # Der Anspruch der Umstellung: sie nimmt genau eine Taste weg.
    klassisch = keymap.resolve(Settings(keymap_style="classic")).bindings
    f_tasten = keymap.resolve(Settings(keymap_style="function_keys")).bindings
    verloren = {action: sorted(set(klassisch[action].keys) - set(f_tasten[action].keys)) for action in klassisch}
    assert {a: k for a, k in verloren.items() if k} == {"toggle_log": ["L", "l"]}


def test_fachliche_tasten_bleiben_in_beiden_stilen() -> None:
    for stil in ("classic", "function_keys"):
        bindings = keymap.resolve(Settings(keymap_style=stil)).bindings
        assert bindings["show_details"].keys == ("d", "D"), stil
        assert bindings["ticket_report"].keys == ("b", "B"), stil
        assert bindings["toggle_anon"].keys == ("a", "A"), stil
        assert bindings["reset_cache"].keys == ("r", "R"), stil
        assert bindings["next_tab"].keys == ("tab",), stil
        assert bindings["refresh"].keys == ("f5",), stil


@pytest.mark.parametrize(
    ("plattform", "erwartet"),
    [("darwin", KeymapStyle.CLASSIC), ("win32", KeymapStyle.FUNCTION_KEYS)],
)
def test_leerer_stil_folgt_der_plattform(
    plattform: str, erwartet: KeymapStyle, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("textual_widgets.keymap.sys.platform", plattform)
    assert keymap.style_from_settings(Settings(keymap_style="")) is erwartet


def test_unbekannter_stil_faellt_nicht_um() -> None:
    # Eine von Hand verbogene Einstellungsdatei darf den Start nicht verhindern.
    assert keymap.style_from_settings(Settings(keymap_style="quatsch")) in tuple(KeymapStyle)


# --- Eigene Belegungen ----------------------------------------------------------


def test_eigene_belegung_gewinnt() -> None:
    ergebnis = keymap.resolve(Settings(keymap_style="function_keys", keymap_custom={"toggle_log": ["alt+l"]}))
    assert ergebnis.bindings["toggle_log"].keys == ("alt+l",)
    assert ergebnis.problems == ()


def test_eigene_belegung_auf_unbekannte_aktion_wird_gemeldet() -> None:
    ergebnis = keymap.resolve(Settings(keymap_custom={"gibtsnicht": ["z"]}))
    assert len(ergebnis.problems) == 1
    assert "gibtsnicht" in ergebnis.problems[0].message


def test_eigene_belegung_darf_quit_nicht_ausknipsen() -> None:
    ergebnis = keymap.resolve(Settings(keymap_style="classic", keymap_custom={"show_details": ["q", "Q"]}))
    assert ergebnis.bindings["quit"].keys == ("q", "Q")
    assert len(ergebnis.problems) == 1


# --- Die Vim-Ebene am Widget ----------------------------------------------------


class _TabellenApp(App[None]):
    """Kleinste App mit einer Tabelle, um die Vim-Bindung zu pruefen."""

    def __init__(self, vim: bool) -> None:
        super().__init__()
        self._vim = vim

    @property
    def vim_navigation(self) -> bool:
        return self._vim

    def compose(self) -> ComposeResult:
        yield ResizableDataTable(id="probe")

    def on_mount(self) -> None:
        tabelle = self.query_one("#probe", ResizableDataTable)
        tabelle.add_column("a")
        for zeile in ("eins", "zwei", "drei"):
            tabelle.add_row(zeile)
        tabelle.focus()


@pytest.mark.asyncio
async def test_j_bewegt_den_zeiger_wenn_vim_an_ist() -> None:
    app = _TabellenApp(vim=True)
    async with app.run_test() as pilot:
        tabelle = app.query_one("#probe", ResizableDataTable)
        assert tabelle.cursor_row == 0
        await pilot.press("j")
        await pilot.pause()
        assert tabelle.cursor_row == 1
        await pilot.press("k")
        await pilot.pause()
        assert tabelle.cursor_row == 0


@pytest.mark.asyncio
async def test_j_tut_nichts_wenn_vim_aus_ist() -> None:
    # Gegenprobe: ohne den Schalter darf die Taste den Zeiger nicht bewegen.
    app = _TabellenApp(vim=False)
    async with app.run_test() as pilot:
        tabelle = app.query_one("#probe", ResizableDataTable)
        await pilot.press("j")
        await pilot.pause()
        assert tabelle.cursor_row == 0


@pytest.mark.asyncio
async def test_grosses_g_springt_ans_ende() -> None:
    app = _TabellenApp(vim=True)
    async with app.run_test() as pilot:
        tabelle = app.query_one("#probe", ResizableDataTable)
        await pilot.press("G")
        await pilot.pause()
        assert tabelle.scroll_offset.y >= 0


# --- Uebersichtsseite -----------------------------------------------------------


def test_uebersicht_zeigt_jede_aktion() -> None:
    from jira_timesheet.screens.keymap_screen import _ist_grossschreibung

    ergebnis = keymap.resolve(Settings(keymap_style="function_keys"))
    # Was die Seite je Zeile anzeigt - keine Aktion darf dabei ohne Taste
    # dastehen, sonst steht dort eine leere Zelle.
    for action, binding in ergebnis.bindings.items():
        sichtbar = [key for key in binding.keys if not _ist_grossschreibung(key)]
        assert sichtbar, f"{action} haette in der Uebersicht keine Taste"


def test_grossschreibung_wird_als_dublette_erkannt() -> None:
    from jira_timesheet.screens.keymap_screen import _ist_grossschreibung

    assert _ist_grossschreibung("Q")
    assert not _ist_grossschreibung("q")
    assert not _ist_grossschreibung("f5")
    assert not _ist_grossschreibung("alt+l")
