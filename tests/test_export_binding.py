"""Tests fuer die Verdrahtung des gebuendelten Exports an der echten App.

Die Formatlogik steckt in `test_export_formats.py`, der Dialog in
`test_export_save_screen.py`. Hier geht es nur um die Frage, ob die Taste in
der laufenden Anwendung ankommt - genau die faellt sonst erst beim Anwender
auf, weil kein Test dazwischen liegt.
"""

from __future__ import annotations

from typing import Any

from textual.widgets import Tabs

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.models.settings import Settings
from jira_timesheet.screens.export_save_screen import ExportSaveScreen


async def _settle(pilot: Any) -> None:
    """Laesst die App zur Ruhe kommen, bevor gemessen wird."""
    await pilot.pause()
    await pilot.pause()


async def test_es_gibt_genau_eine_export_aktion() -> None:
    # Gegenprobe zur Zusammenlegung: blieben die alten Aktionen stehen,
    # haetten wir zwei Tasten fuer denselben Dialog.
    app = JiraTimesheetApp()
    assert hasattr(app, "action_export")
    assert not hasattr(app, "action_export_excel")
    assert not hasattr(app, "action_export_pdf")


def _stil_festlegen(stil: str) -> None:
    """Schreibt den Tastenstil in die (isolierte) Einstellungsdatei.

    Der Stil wird in ``__init__`` gelesen und gebunden - er muss also VOR dem
    Bau der App feststehen. Ohne diesen Schritt haengt der Test an der Vorgabe
    der Plattform und prueft auf einem Mac etwas anderes als hier.

    Args:
        stil: "function_keys" oder "classic".
    """

    einstellungen = Settings()
    einstellungen.keymap_style = stil
    einstellungen.save()


def _gebundene_tasten(app: JiraTimesheetApp) -> dict[str, str]:
    """Liest, welche Taste welche Aktion ausloest.

    Args:
        app: Die gebaute Anwendung.

    Returns:
        Taste auf Aktionsname.
    """

    return {
        key: binding.action
        for key, bindings in app._bindings.key_to_bindings.items()
        for binding in bindings
    }


async def test_f10_ist_der_export_und_f9_das_anonymisieren() -> None:
    _stil_festlegen("function_keys")
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await _settle(pilot)
        gebunden = _gebundene_tasten(app)

    assert gebunden["f10"] == "export"
    assert gebunden["f9"] == "toggle_anon"
    assert gebunden["e"] == "export"
    # Die zweite Export-Taste ist weg - sonst haetten wir wieder zwei fuer
    # denselben Dialog.
    assert "p" not in gebunden


async def test_im_bestandsstil_bleibt_e_der_export() -> None:
    _stil_festlegen("classic")
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await _settle(pilot)
        gebunden = _gebundene_tasten(app)

    assert gebunden["e"] == "export"
    assert gebunden["a"] == "toggle_anon"
    assert "p" not in gebunden
    # Beweist, dass der Stil wirklich angekommen ist - sonst prueft der Test
    # nur die Vorgabe der Plattform.
    assert "f10" not in gebunden


async def test_ohne_stundenzettel_bleibt_die_taste_aus_dem_footer() -> None:
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await _settle(pilot)
        assert app._timesheet is None
        assert app.check_action("export", ()) is None


async def test_export_oeffnet_den_speichern_dialog(monkeypatch: Any) -> None:
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await _settle(pilot)
        # Einen Stundenzettel unterschieben - ohne ihn bricht die Aktion mit
        # einem Hinweis ab, und der Dialog kaeme nie.
        from tests.test_export_formats import beispiel_stundenzettel

        app._timesheet = beispiel_stundenzettel()
        assert app.check_action("export", ()) is True

        app.action_export()
        await _settle(pilot)

        assert isinstance(app.screen, ExportSaveScreen)
        # Der Vorschlag steht auf dem vorausgewaehlten Format.
        from textual.widgets import Input

        assert app.screen.query_one(Input).value.endswith(".xlsx")


async def test_der_footer_zeigt_den_export_nur_einmal() -> None:
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await _settle(pilot)
        from jira_timesheet import keymap

        bindings = keymap.resolve(Settings(keymap_style="function_keys")).bindings
        assert "export_excel" not in bindings
        assert "export_pdf" not in bindings
        assert bindings["export"].keys[0] == "f10"
        assert bindings["toggle_anon"].keys[0] == "f9"
        # Tabs bleiben unberuehrt - reine Absicherung, dass die App steht.
        assert app.query_one(Tabs) is not None

async def test_der_dialog_geht_auch_ohne_schreibtisch_auf(
    tmp_path: Any, monkeypatch: Any
) -> None:
    """Auf einem Rechner ohne Verzeichnis "Desktop" darf der Dialog nicht abstuerzen.

    Genau das ist auf dem Linux-Runner der CI passiert: die Vorbelegung stand
    fest auf `~/Desktop`, textual_fspicker fand das Verzeichnis nicht und
    Textual schob einen Fehlerbildschirm ueber die Anwendung. Unter Windows
    faellt das nie auf, weil es den Schreibtisch dort immer gibt.
    """
    from pathlib import Path

    from jira_timesheet.screens.export_save_screen import ExportSaveScreen
    from tests.test_export_formats import beispiel_stundenzettel

    heim = tmp_path / "heim-ohne-schreibtisch"
    heim.mkdir()
    assert not (heim / "Desktop").exists()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: heim))

    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await _settle(pilot)
        app._timesheet = beispiel_stundenzettel()
        # So steht es nach dem Bau der Anwendung: ein Pfad, den es nicht gibt.
        app._last_export_dir = str(heim / "Desktop")
        assert Path(app._save_dialog_location()).is_dir()

        app.action_export()
        await _settle(pilot)

        assert isinstance(app.screen, ExportSaveScreen), type(app.screen).__name__
