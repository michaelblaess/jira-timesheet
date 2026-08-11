"""Persistierte Benutzereinstellungen."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from jira_timesheet.models.export_column import ExportColumn, default_columns, parse_columns

logger = logging.getLogger(__name__)

# Markierungsfarbe manueller Eintraege als RRGGBB (ohne fuehrendes #).
DEFAULT_MANUAL_COLOR = "FF0000"

# Vorbelegte Kundenliste - der Benutzer pflegt sie in den Einstellungen.
DEFAULT_CUSTOMERS = ("Vertrieb", "Corporate")

_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")
_RGB_TRIPLE = re.compile(r"^(\d{1,3})\s*[,;/ ]\s*(\d{1,3})\s*[,;/ ]\s*(\d{1,3})$")


def normalize_color(value: str, fallback: str = DEFAULT_MANUAL_COLOR) -> str:
    """Normalisiert eine Farbeingabe auf RRGGBB (Grossbuchstaben).

    Akzeptiert "#RRGGBB", "RRGGBB", die Kurzform "#RGB" sowie ein
    RGB-Tripel wie "255,0,0". Bei ungueltiger Eingabe kommt der Fallback
    zurueck - eine kaputte Farbe darf den Export nie sprengen.

    Args:
        value:
            Die Benutzereingabe.
        fallback:
            Rueckgabewert bei ungueltiger Eingabe.

    Returns:
        Farbe als sechsstelliger Hex-String ohne fuehrendes Doppelkreuz.
    """
    raw = (value or "").strip().lstrip("#").strip()
    if _HEX_COLOR.match(raw):
        return raw.upper()

    if len(raw) == 3 and _HEX_COLOR.match(raw * 2):
        return "".join(ch * 2 for ch in raw).upper()

    match = _RGB_TRIPLE.match(raw)
    if match is not None:
        parts = [int(g) for g in match.groups()]
        if all(0 <= p <= 255 for p in parts):
            return "".join(f"{p:02X}" for p in parts)

    return fallback


# textual-themes 0.5 hat 25 Themes umbenannt (trademark-safety pass).
# Settings-Files aelterer Versionen koennen alte Slugs gespeichert haben —
# die werden beim Laden transparent gemappt.
_LEGACY_THEME_MAP: dict[str, str] = {
    "c64": "brotkasten",
    "amiga": "boing",
    "atari-st": "gemstone",
    "ibm-terminal": "classic-terminal",
    "nextstep": "next",
    "beos": "bebox",
    "ubuntu": "bunty",
    "macos": "cupertino",
    "windows-xp": "luna",
    "msdos": "commandr",
    "solaris-cde": "motif",
    "os2-warp": "warp",
    "opensuse": "geeko",
    "linux-mint": "minty",
    "red-hat": "crimson",
    "raspberry-pi": "razzy",
    "freebsd": "beastie",
    "tudor": "fifty-eight",
    "goldfinger": "goldfinder",
    "hulk": "hulkula",
    "batman": "flughund",
    "gameboy": "brick",
    "pan-am": "clipper",
    "miami-vice": "miami",
    "martini-racing": "racing",
    "superman": "metropolis",
    "spiderman": "spiderized",
    "gulf-racing": "textual-dark",  # entferntes Theme -> Textual Default
}


@dataclass
class Settings:
    """Einstellungen gespeichert in ~/.jira-timesheet/settings.json."""

    theme: str = "textual-dark"
    language: str = "de"
    jira_host: str = ""
    jira_token: str = ""
    email: str = ""
    use_legacy_api: bool = False
    proxy_url: str = ""
    logo_path: str = ""
    last_date_from: str = ""
    last_date_to: str = ""
    log_visible: bool = True
    budget_field: str = ""
    federal_state: str = "SN"
    hours_per_day: float = 8.0
    max_yearly_hours: float = 1720.0
    show_target_hours_in_export: bool = False
    show_ticket_links_in_export: bool = False
    hourly_rate: float = 0.0
    vat_rate: float = 19.0
    year: int = 0
    vacation_days: int = 30
    config_collapsed: bool = False
    search_history: list[str] = field(default_factory=list)
    # Manuell gezogene Spaltenbreiten der Liste, Schluessel ist der Spaltenindex.
    column_widths: dict[str, int] = field(default_factory=dict)
    # Konfiguration der Export-Spalten (aktiv + Bezeichnung).
    export_columns: list[ExportColumn] = field(default_factory=default_columns)
    mark_manual_entries: bool = True
    manual_entry_color: str = DEFAULT_MANUAL_COLOR
    default_customer: str = "Vertrieb"
    # Auswahlliste fuer das Kunden-Feld im Dialog fuer manuelle Zeiten.
    customers: list[str] = field(default_factory=lambda: list(DEFAULT_CUSTOMERS))

    # --- Ticket-Ansichten ---------------------------------------------
    # Welcher Status welche Rolle hat, ist bewusst Konfiguration und keine
    # Konstante: jede Jira-Instanz fuehrt eigene Workflows. Ohne Zuordnung
    # faellt der Kern auf die Jira-Statuskategorie zurueck - groeber, aber
    # sofort brauchbar.
    board_active_status: list[str] = field(default_factory=list)
    board_backlog_status: list[str] = field(default_factory=list)
    board_handback_status: list[str] = field(default_factory=list)
    board_acceptance_status: list[str] = field(default_factory=list)
    board_closing_status: list[str] = field(default_factory=list)
    # Wirklich fertig - reiner Kontrollblick, ohne Handlungsbedarf.
    board_done_status: list[str] = field(default_factory=list)
    # Rangfolge der Prioritaeten, dringendstes zuerst. Leer = die Vorgabe
    # des Kerns, die mehrere gaengige Jira-Schemata abdeckt.
    board_priorities: list[str] = field(default_factory=list)
    # Zeitfenster der Ansicht "Meine Aktivitaeten" in Kalendertagen.
    board_window_days: int = 90
    # Ab so vielen Kalendertagen ohne Aenderung gilt ein Ticket als verwaist.
    board_stale_days: int = 180
    # Schwellen in ARBEITSTAGEN je Rolle, 0 schaltet die Rolle ab. Das sind
    # Setzungen, keine Messungen - deshalb stehen sie in der Oberflaeche.
    board_threshold_active: float = 20.0
    board_threshold_acceptance: float = 10.0
    board_threshold_closing: float = 0.0

    # --- Mein Team ----------------------------------------------------
    # Die Merkliste in ihrer Speicherform, so wie services.team sie liest.
    # Bewusst als rohe Abbildungen und nicht als TeamMember: die
    # Einstellungen sollen den Kern nicht kennen und der Kern nicht die
    # Einstellungen. Je Eintrag stehen darin display_name und account_ids,
    # letzteres als LISTE - eine Person kann mehrere Konten fuehren.
    team_members: list[dict[str, object]] = field(default_factory=list)

    SETTINGS_DIR: Path = Path.home() / ".jira-timesheet"
    SETTINGS_FILE: Path = SETTINGS_DIR / "settings.json"

    _FIELDS = (
        "theme",
        "language",
        "jira_host",
        "jira_token",
        "email",
        "use_legacy_api",
        "proxy_url",
        "logo_path",
        "last_date_from",
        "last_date_to",
        "log_visible",
        "budget_field",
        "federal_state",
        "hours_per_day",
        "max_yearly_hours",
        "show_target_hours_in_export",
        "show_ticket_links_in_export",
        "hourly_rate",
        "vat_rate",
        "year",
        "vacation_days",
        "config_collapsed",
        "search_history",
        "column_widths",
        "export_columns",
        "mark_manual_entries",
        "manual_entry_color",
        "default_customer",
        "customers",
        "board_active_status",
        "board_backlog_status",
        "board_handback_status",
        "board_acceptance_status",
        "board_closing_status",
        "board_done_status",
        "board_priorities",
        "board_window_days",
        "board_stale_days",
        "board_threshold_active",
        "board_threshold_acceptance",
        "board_threshold_closing",
        "team_members",
    )

    def to_dict(self) -> dict[str, object]:
        """Konvertiert die Einstellungen in ein Dictionary fuer JSON."""
        data: dict[str, object] = {name: getattr(self, name) for name in self._FIELDS}
        # Spalten sind Dataclasses - fuer JSON in Dicts wandeln.
        data["export_columns"] = [column.to_dict() for column in self.export_columns]
        return data

    @staticmethod
    def load() -> Settings:
        """Laedt die Einstellungen aus der JSON-Datei.

        Gibt Default-Einstellungen zurueck bei Fehler. Migriert dabei alte
        Theme-Slugs aus textual-themes < 0.5 auf ihre aktuellen Namen
        und persistiert die Migration.
        """
        if not Settings.SETTINGS_FILE.is_file():
            return Settings()

        try:
            raw = Settings.SETTINGS_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                return Settings()
            settings = Settings(
                theme=data.get("theme", "textual-dark"),
                language=data.get("language", "de"),
                jira_host=data.get("jira_host", ""),
                jira_token=data.get("jira_token", ""),
                email=data.get("email", ""),
                use_legacy_api=bool(data.get("use_legacy_api", False)),
                proxy_url=data.get("proxy_url", ""),
                logo_path=data.get("logo_path", ""),
                last_date_from=data.get("last_date_from", ""),
                last_date_to=data.get("last_date_to", ""),
                log_visible=data.get("log_visible", True),
                budget_field=data.get("budget_field", ""),
                federal_state=data.get("federal_state", "SN"),
                hours_per_day=data.get("hours_per_day", 8.0),
                max_yearly_hours=data.get("max_yearly_hours", 1720.0),
                show_target_hours_in_export=data.get("show_target_hours_in_export", False),
                show_ticket_links_in_export=data.get("show_ticket_links_in_export", False),
                hourly_rate=data.get("hourly_rate", 0.0),
                vat_rate=data.get("vat_rate", 19.0),
                year=data.get("year", 0),
                vacation_days=data.get("vacation_days", 30),
                config_collapsed=data.get("config_collapsed", False),
                search_history=[str(x) for x in data.get("search_history", []) if isinstance(x, str)],
                column_widths=Settings._parse_column_widths(data.get("column_widths")),
                export_columns=parse_columns(data.get("export_columns")),
                mark_manual_entries=bool(data.get("mark_manual_entries", True)),
                manual_entry_color=normalize_color(str(data.get("manual_entry_color", DEFAULT_MANUAL_COLOR))),
                default_customer=str(data.get("default_customer", "Vertrieb")),
                customers=Settings._parse_customers(data.get("customers")),
                board_active_status=Settings._parse_str_list(data.get("board_active_status")),
                board_backlog_status=Settings._parse_str_list(data.get("board_backlog_status")),
                board_handback_status=Settings._parse_str_list(data.get("board_handback_status")),
                board_acceptance_status=Settings._parse_str_list(
                    data.get("board_acceptance_status")
                ),
                board_closing_status=Settings._parse_str_list(data.get("board_closing_status")),
                board_done_status=Settings._parse_str_list(data.get("board_done_status")),
                board_priorities=Settings._parse_str_list(data.get("board_priorities")),
                board_window_days=Settings._parse_int(data.get("board_window_days"), 90),
                board_stale_days=Settings._parse_int(data.get("board_stale_days"), 180),
                board_threshold_active=Settings._parse_float(
                    data.get("board_threshold_active"), 20.0
                ),
                board_threshold_acceptance=Settings._parse_float(
                    data.get("board_threshold_acceptance"), 10.0
                ),
                board_threshold_closing=Settings._parse_float(
                    data.get("board_threshold_closing"), 0.0
                ),
                team_members=Settings._parse_team(data.get("team_members")),
            )
        except Exception as exc:
            logger.warning("Settings konnten nicht geladen werden: %s", exc)
            return Settings()

        # Legacy-Theme-Slug migrieren
        if settings.theme in _LEGACY_THEME_MAP:
            settings.theme = _LEGACY_THEME_MAP[settings.theme]
            settings.save()

        return settings

    @staticmethod
    def _parse_customers(raw: object) -> list[str]:
        """Liest die Kundenliste defensiv; leere Eintraege fliegen raus."""
        if not isinstance(raw, list):
            return list(DEFAULT_CUSTOMERS)
        names = [str(item).strip() for item in raw if str(item).strip()]
        return names or list(DEFAULT_CUSTOMERS)

    @staticmethod
    def _parse_str_list(raw: object) -> list[str]:
        """Liest eine Liste von Zeichenketten defensiv aus dem JSON.

        Args:
            raw:
                Der rohe Wert aus der Datei.

        Returns:
            Die bereinigten Eintraege, leere fliegen raus. Kein Rueckfall auf
            eine Vorgabe: eine leere Statusliste ist eine gueltige Angabe
            (dann greift die Statuskategorie), keine fehlende.
        """
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    @staticmethod
    def _parse_team(raw: object) -> list[dict[str, object]]:
        """Liest die Merkliste "Mein Team" defensiv aus dem JSON.

        Geprueft wird hier nur die Form, nicht der Inhalt: ob eine Kennung
        brauchbar ist, entscheidet services.team beim Aufbau der Liste. Was
        hier durchkommt, ist eine Abbildung mit Namen und mindestens einer
        Kennung - alles andere waere ein Eintrag, der spaeter als leere
        Ansicht erscheint und wie "nichts zu tun" aussieht.

        Args:
            raw:
                Der rohe Wert aus der Datei.

        Returns:
            Die brauchbaren Eintraege in der Speicherform.
        """
        if not isinstance(raw, list):
            return []
        members: list[dict[str, object]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("display_name") or "").strip()
            ids = [
                str(value).strip()
                for value in (entry.get("account_ids") or [])
                if str(value).strip()
            ]
            if not name or not ids:
                continue
            members.append(
                {
                    "display_name": name,
                    "account_ids": ids,
                    "email": str(entry.get("email") or ""),
                    "avatar_url": str(entry.get("avatar_url") or ""),
                }
            )
        return members

    @staticmethod
    def _parse_int(raw: object, fallback: int) -> int:
        """Liest eine ganze Zahl defensiv, mit Rueckfall auf die Vorgabe."""
        if isinstance(raw, bool) or not isinstance(raw, int | float | str):
            return fallback
        try:
            return int(raw)
        except ValueError:
            return fallback

    @staticmethod
    def _parse_float(raw: object, fallback: float) -> float:
        """Liest eine Kommazahl defensiv, mit Rueckfall auf die Vorgabe."""
        if isinstance(raw, bool) or not isinstance(raw, int | float | str):
            return fallback
        try:
            return float(raw)
        except ValueError:
            return fallback

    @staticmethod
    def _parse_column_widths(raw: object) -> dict[str, int]:
        """Liest die gespeicherten Spaltenbreiten defensiv aus dem JSON."""
        if not isinstance(raw, dict):
            return {}
        return {str(key): int(value) for key, value in raw.items() if isinstance(value, int) and value > 0}

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
