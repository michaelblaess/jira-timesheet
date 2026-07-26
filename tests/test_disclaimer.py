"""Tests fuer den bestaetigungspflichtigen Haftungshinweis beim Programmstart.

Die App liest fremde Arbeitszeit-Daten aus einer Jira-Instanz. Der Hinweis ist
darum nicht optional - ohne Zustimmung beendet sich das Programm. Diese Tests
halten fest, dass er erscheint, dass Ablehnung wirklich beendet und dass eine
einmal erteilte Zustimmung beim naechsten Start nicht erneut abgefragt wird.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import Button, Checkbox
from textual_widgets import DISCLAIMER_VERSION, DisclaimerScreen

from jira_timesheet.app import JiraTimesheetApp
from jira_timesheet.i18n import load_locale
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.manual_entry_service import ManualEntryService


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt alle Nutzerdateien nach tmp_path.

    Ohne das laufen die Tests gegen die echte ~/.jira-timesheet - und eine
    lokal bereits erteilte Zustimmung wuerde den ersten Test gruen faerben,
    obwohl der Dialog gar nicht eingebaut ist.
    """
    load_locale("de")
    monkeypatch.setattr(Settings, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(Settings, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(ManualEntryService, "db_path", tmp_path / "manual-entries.db")
    return tmp_path


async def test_disclaimer_is_shown_on_first_start(_isolated_home: Path) -> None:
    """Ohne vorliegende Zustimmung blockiert der Hinweis den Start."""
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, DisclaimerScreen)


async def test_declining_quits_the_application(_isolated_home: Path) -> None:
    """Wer ablehnt, kann das Programm nicht benutzen - es beendet sich."""
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, DisclaimerScreen)
        await pilot.press("escape")
        await pilot.pause()

    assert not (_isolated_home / "disclaimer.json").is_file()


async def test_acceptance_is_recorded_and_not_asked_again(
    _isolated_home: Path,
) -> None:
    """Nach der Zustimmung startet der naechste Lauf ohne Rueckfrage."""
    app = JiraTimesheetApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DisclaimerScreen)
        # Zustimmung wie durch den Anwender: Haken setzen, dann bestaetigen.
        screen.query_one("#disclaimer-agree", Checkbox).value = True
        await pilot.pause()
        screen.query_one("#disclaimer-accept", Button).press()
        await pilot.pause()
        assert not isinstance(app.screen, DisclaimerScreen)

    recorded = _isolated_home / "disclaimer.json"
    assert recorded.is_file()
    assert DISCLAIMER_VERSION in recorded.read_text(encoding="utf-8")

    # Zweiter Start mit derselben Zustimmung - der Hinweis bleibt aus.
    again = JiraTimesheetApp()
    async with again.run_test() as pilot:
        await pilot.pause()
        assert not isinstance(again.screen, DisclaimerScreen)
