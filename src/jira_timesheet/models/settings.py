"""Persistierte Benutzereinstellungen."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Einstellungen gespeichert in ~/.jira-timesheet/settings.json."""

    theme: str = "textual-dark"
    jira_host: str = ""
    jira_token: str = ""
    email: str = ""
    logo_path: str = ""
    last_date_from: str = ""
    last_date_to: str = ""
    log_visible: bool = True
    budget_field: str = "customfield_36461"
    federal_state: str = "SN"
    hours_per_day: float = 8.0
    max_yearly_hours: float = 1720.0

    SETTINGS_DIR: Path = Path.home() / ".jira-timesheet"
    SETTINGS_FILE: Path = SETTINGS_DIR / "settings.json"

    _FIELDS = (
        "theme", "jira_host", "jira_token", "email", "logo_path",
        "last_date_from", "last_date_to", "log_visible", "budget_field",
        "federal_state", "hours_per_day", "max_yearly_hours",
    )

    def to_dict(self) -> dict[str, object]:
        """Konvertiert die Einstellungen in ein Dictionary fuer JSON."""
        return {field: getattr(self, field) for field in self._FIELDS}

    @staticmethod
    def load() -> Settings:
        """Laedt die Einstellungen aus der JSON-Datei.

        Gibt Default-Einstellungen zurueck bei Fehler.
        """
        if not Settings.SETTINGS_FILE.is_file():
            return Settings()

        try:
            raw = Settings.SETTINGS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return Settings()
            return Settings(
                theme=data.get("theme", "textual-dark"),
                jira_host=data.get("jira_host", ""),
                jira_token=data.get("jira_token", ""),
                email=data.get("email", ""),
                logo_path=data.get("logo_path", ""),
                last_date_from=data.get("last_date_from", ""),
                last_date_to=data.get("last_date_to", ""),
                log_visible=data.get("log_visible", True),
                budget_field=data.get("budget_field", "customfield_36461"),
                federal_state=data.get("federal_state", "SN"),
                hours_per_day=data.get("hours_per_day", 8.0),
                max_yearly_hours=data.get("max_yearly_hours", 1720.0),
            )
        except Exception as exc:
            logger.warning("Settings konnten nicht geladen werden: %s", exc)
            return Settings()

    def save(self) -> None:
        """Speichert die Einstellungen in die JSON-Datei."""
        try:
            Settings.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            Settings.SETTINGS_FILE.write_text(
                json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Settings konnten nicht gespeichert werden: %s", exc)
