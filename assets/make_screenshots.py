"""Nimmt die README-Screenshots headless auf - mit erfundenen Daten.

WARUM ERFUNDEN und nicht der Anonymisierungs-Modus der Anwendung: der ersetzt
Ticketnummern, Beschreibungen, Namen und Budgets und zensiert Geldbetraege,
aber er laesst die STUNDEN unberuehrt ("Stunden, Daten und Struktur bleiben
erhalten", anonymizer.py). Ein Screenshot im a-Modus zeigt also weiter die
echte Arbeitszeit ueber zwoelf Monate, und aus Stunden und Nettobetrag laesst
sich der Stundensatz zurueckrechnen. Fuer ein oeffentliches Repo ist das zu
viel. Dieses Skript speist die Anwendung stattdessen mit einem erfundenen
Jahrgang - dann ist nichts zu zensieren.

Ablauf: Anwendung headless starten, Ansicht ansteuern, Textual schreibt ein
SVG, danach rendert das gecachte Chromium daraus ein PNG.

Aufruf aus dem Repo-Wurzelverzeichnis:

    .venv/Scripts/python.exe assets/make_screenshots.py
    .venv/Scripts/python.exe assets/make_screenshots.py --themes miami,luna
    .venv/Scripts/python.exe assets/make_screenshots.py --views 03-year-view
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from PIL import Image

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

from textual.widgets import TabbedContent  # noqa: E402

from jira_timesheet.app import JiraTimesheetApp  # noqa: E402
from jira_timesheet.i18n import load_locale  # noqa: E402
from jira_timesheet.models.settings import Settings  # noqa: E402
from jira_timesheet.models.timesheet import WorklogEntry  # noqa: E402
from jira_timesheet.services import cache_service  # noqa: E402
from jira_timesheet.services.manual_entry_service import ManualEntryService  # noqa: E402

ZIEL = WURZEL / "docs" / "screenshots"

# Bewusst eine AUSWAHL, nicht alle 38 Themes - sonst waeren es weit ueber
# hundert Bilder, die niemand ansieht und die jeden Release-Diff sprengen.
THEMES = ("beastie", "bebox", "classic-terminal", "corleone", "gemstone", "metropolis", "miami")

@dataclass(frozen=True)
class Lage:
    """Beschreibt, was vor der Aufnahme hergestellt werden soll.

    Attributes:
        tab:
            Reiter der Hauptansicht. None laesst den Startreiter stehen.
        dialog:
            "details", "settings" oder "info". None bleibt in der Hauptansicht.
        settings_tab:
            Nur bei dialog="settings": welcher Reiter des Dialogs zu sehen ist.
    """

    tab: str | None = None
    dialog: str | None = None
    settings_tab: str | None = None


# Die Zieldateien - EXAKT die Namen, die in beiden READMEs und auf der
# Pages-Seite verlinkt sind. Weicht ein Name ab, bleibt das alte Bild liegen
# und das neue wird nirgends angezeigt.
ANSICHTEN: dict[str, Lage] = {
    "01-main": Lage(),
    "02-month-view": Lage(tab="tab-calendar"),
    "03-year-view": Lage(tab="tab-year"),
    "04-details": Lage(dialog="details"),
    "06-info": Lage(dialog="info"),
    # Der Einstellungsdialog mit je einem anderen Reiter - die Bestandsbilder
    # zeigen ebenfalls verschiedene Seiten, daher die abweichenden Namen.
    "05-settings": Lage(dialog="settings", settings_tab="settings-tab-jira"),
    "05-settings-gemstone-1": Lage(dialog="settings", settings_tab="settings-tab-jira"),
    "05-settings-gemstone-2": Lage(dialog="settings", settings_tab="settings-tab-calc"),
    "05-settings-metropolis-02": Lage(dialog="settings", settings_tab="settings-tab-tickets"),
    "05-settings-metropolis-03": Lage(dialog="settings", settings_tab="settings-tab-team"),
}

# Welche Ansicht fuer welche Themes existiert. Der Bestand ist hier bewusst
# ungleichmaessig - nicht jede Ansicht gibt es in jedem Theme.
BELEGUNG: dict[str, tuple[str, ...]] = {
    "01-main": THEMES,
    "02-month-view": THEMES,
    "03-year-view": THEMES,
    "04-details": ("beastie", "bebox", "classic-terminal", "metropolis"),
    "05-settings": ("beastie", "classic-terminal", "corleone", "metropolis"),
    "06-info": ("beastie", "bebox", "metropolis"),
    # Sonderdateien: Name traegt das Theme schon, deshalb leerer Zusatz.
    "05-settings-gemstone-1": ("gemstone",),
    "05-settings-gemstone-2": ("gemstone",),
    "05-settings-metropolis-02": ("metropolis",),
    "05-settings-metropolis-03": ("metropolis",),
}

# Bei diesen Ansichten steckt das Theme bereits im Namen - kein Suffix anhaengen.
OHNE_THEME_SUFFIX = frozenset(
    {
        "05-settings-gemstone-1",
        "05-settings-gemstone-2",
        "05-settings-metropolis-02",
        "05-settings-metropolis-03",
    }
)

# Terminalmass der Aufnahme. Breit genug fuer alle drei Monatsspalten der
# Jahresansicht, hoch genug, dass Summe und Forecast nicht scrollen muessen -
# aber nicht hoeher, sonst klafft zwischen Kachelraster und Summenzeile eine
# leere Flaeche, weil die Summe unten angedockt ist.
BREITE, HOEHE = 200, 53

# Erfundene Zahlen: ein Jahrgang mit sichtbarer Streuung, damit die
# Fortschrittsbalken nicht alle gleich aussehen. Runder Stundensatz, damit
# niemand auf die Idee kommt, einen echten herauszulesen.
STUNDENSATZ = 100.0
STUNDEN_JE_MONAT = {
    1: 7.5, 2: 8.0, 3: 6.0, 4: 8.0, 5: 7.5, 6: 6.5,
    7: 8.5, 8: 3.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0,
}

TICKETS = (
    ("PROJ-1042", "Anmeldung ueber das neue Portal"),
    ("PROJ-1108", "Rechnungslauf beschleunigen"),
    ("DEMO-217", "Wartungsfenster dokumentieren"),
    ("DEMO-233", "Auswertung fuer das Quartal"),
    ("SHOP-88", "Warenkorb behaelt Rabatte"),
)


class ErfundenerClient:
    """Steht an der Stelle des Jira-Clients und liefert erfundene Buchungen."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    async def get_worklogs(self, date_from: date, date_to: date) -> list[WorklogEntry]:
        """Baut fuer jeden Werktag des Zeitraums ein bis zwei Buchungen.

        Bewusst NICHT jeden Tag gleich: mit einer festen Stundenzahl je Tag
        stuenden in der Liste zwanzig identische Zeilen, und die Tagessumme
        waere nie von einem Einzeleintrag zu unterscheiden. Die Streuung ist
        fest verdrahtet (kein Zufall), damit dasselbe Bild reproduzierbar
        bleibt.
        """
        eintraege: list[WorklogEntry] = []
        tag = date_from
        index = 0
        while tag <= date_to:
            tagessoll = STUNDEN_JE_MONAT.get(tag.month, 0.0)
            if tag.weekday() < 5 and tagessoll > 0:
                # Jeder dritte Tag wird auf zwei Vorgaenge aufgeteilt.
                anteile = (tagessoll * 0.6, tagessoll * 0.4) if index % 3 == 0 else (tagessoll,)
                for anteil in anteile:
                    ticket, titel = TICKETS[index % len(TICKETS)]
                    eintraege.append(
                        WorklogEntry(
                            date=tag,
                            ticket=ticket,
                            summary=titel,
                            author="Erika Musterfrau",
                            budget="Weiterentwicklung",
                            hours=round(anteil, 2),
                        )
                    )
                    index += 1
            tag += timedelta(days=1)
        return eintraege


def chromium() -> Path:
    """Findet die neueste gecachte Chromium-Binary von Playwright.

    Raises:
        SystemExit:
            Wenn keine gefunden wird - dann fehlt das Playwright-Cache, und
            ohne Browser gibt es kein PNG.
    """
    basis = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"
    kandidaten = sorted(basis.glob("chromium-*/chrome-win64/chrome.exe"), reverse=True)
    if not kandidaten:
        raise SystemExit(
            "Kein gecachtes Chromium gefunden. Playwright-Browser installieren "
            "(siehe reference_headless_browser_smoketest)."
        )
    return kandidaten[0]


def svg_nach_png(svg: Path, png: Path, browser: Path) -> None:
    """Rendert ein SVG als PNG.

    --no-sandbox ist noetig: die Windows-Sandbox verweigert den Zugriff auf die
    Playwright-Binary und wirft eine Fehlerzeile, obwohl das Bild entsteht.
    """
    png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(browser),
            "--headless",
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={BREITE * 9},{HOEHE * 21}",
            f"--screenshot={png}",
            svg.resolve().as_uri(),
        ],
        capture_output=True,
        check=True,
    )
    _auf_palette_reduzieren(png)


def _auf_palette_reduzieren(png: Path) -> None:
    """Schreibt das Bild mit 256er-Palette neu.

    Ein Terminal-Standbild kommt mit sehr wenigen Farbtoenen aus (gemessen:
    knapp 8000 in einem Vollbild, davon fast alles Kantenglaettung der
    Schrift). Als Echtfarbbild wiegt es rund 270 KB, mit Palette 85 KB - bei
    36 Bildern also gut sechs Megabyte weniger, die sonst mit jeder
    Neuaufnahme erneut in die Git-History wandern. Ein Unterschied ist am
    Bildschirm nicht auszumachen.
    """
    with Image.open(png) as bild:
        verkleinert = bild.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    verkleinert.save(png, optimize=True)


async def aufnehmen(theme: str, ansicht: str, lage: Lage, browser: Path, ablage: Path) -> Path:
    """Startet die Anwendung, stellt eine Lage her und nimmt sie auf."""
    heim = ablage / f"heim-{theme}-{ansicht}"
    heim.mkdir(parents=True, exist_ok=True)
    load_locale("de")
    Settings.SETTINGS_DIR = heim
    Settings.SETTINGS_FILE = heim / "settings.json"
    ManualEntryService.db_path = heim / "manual-entries.db"
    cache_service.CACHE_DIR = heim / "cache"

    import jira_timesheet.app as app_modul

    app_modul.JiraClient = ErfundenerClient
    JiraTimesheetApp._ask_disclaimer = lambda self: None  # noqa: SLF001

    app = JiraTimesheetApp()
    app._settings.jira_host = "https://beispiel.atlassian.net"
    app._settings.email = "erika.musterfrau@beispiel.de"
    app._settings.jira_token = "beispiel-token"
    app._settings.year = date.today().year
    app._settings.hourly_rate = STUNDENSATZ
    app._settings.max_yearly_hours = 1720.0
    app._settings.theme = theme
    app._settings.log_visible = False

    datei = ansicht if ansicht in OHNE_THEME_SUFFIX else f"{ansicht}-{theme}"
    svg = ablage / f"{datei}.svg"

    async with app.run_test(size=(BREITE, HOEHE)) as pilot:
        app.theme = theme
        for _ in range(40):
            await pilot.pause()

        if lage.tab is not None:
            reiter = app.query_one("#view-tabs", TabbedContent)
            # Wiederholen, bis der Wechsel haelt - eine einzelne Zuweisung
            # verwirft TabbedContent, solange es nicht fertig initialisiert
            # ist (siehe tests/test_year_view.py::_wechsle_zu).
            for _ in range(200):
                if app._active_tab() == lage.tab:
                    break
                reiter.active = lage.tab
                await pilot.pause()

        # Der Jahres-Reiter laedt zwoelf Monate nach; ohne Warten steht im
        # Bild "Lade Jahresdaten ...".
        for _ in range(400):
            await pilot.pause()
            if lage.tab != "tab-year" or app._year_loaded_for is not None:
                break

        if lage.dialog is not None:
            await _dialog_oeffnen(app, pilot, lage)

        for _ in range(30):
            await pilot.pause()
        app.save_screenshot(str(svg))

    png = ZIEL / f"{datei}.png"
    svg_nach_png(svg, png, browser)
    return png


async def _dialog_oeffnen(app: JiraTimesheetApp, pilot: Any, lage: Lage) -> None:
    """Oeffnet den Dialog der Lage und wartet, bis er steht."""
    if lage.dialog == "info":
        app.action_show_about()
    elif lage.dialog == "settings":
        app.action_show_settings()
    elif lage.dialog == "details":
        # Ueber den Kern statt ueber den Tabellen-Cursor: fuer ein Standbild
        # zaehlt, WAS im Dialog steht, nicht wie er geoeffnet wurde.
        eintrag = next(iter(app._timesheet.all_entries)) if app._timesheet else None
        if eintrag is None:
            raise SystemExit("Kein Eintrag fuer den Detail-Dialog - lud der Zettel nicht?")
        app._show_entry_details(eintrag)
    else:
        raise SystemExit(f"Unbekannter Dialog: {lage.dialog}")

    for _ in range(60):
        await pilot.pause()

    if lage.settings_tab is not None:
        reiter = app.screen.query_one(TabbedContent)
        for _ in range(200):
            if reiter.active == lage.settings_tab:
                break
            reiter.active = lage.settings_tab
            await pilot.pause()


async def main(themes: Sequence[str], ansichten: Sequence[str]) -> None:
    browser = chromium()
    print(f"Chromium: {browser}")
    erzeugt = 0
    with tempfile.TemporaryDirectory(prefix="jts-shots-") as tmp:
        ablage = Path(tmp)
        for ansicht in ansichten:
            lage = ANSICHTEN[ansicht]
            # Nur die Themes, fuer die es dieses Bild ueberhaupt gibt - sonst
            # entstehen Dateien, die nirgends verlinkt sind.
            fuer_diese = [t for t in themes if t in BELEGUNG[ansicht]]
            for theme in fuer_diese:
                png = await aufnehmen(theme, ansicht, lage, browser, ablage)
                print(f"  {png.name}  ({png.stat().st_size // 1024} KB)")
                erzeugt += 1
    print(f"{erzeugt} Bild(er) erzeugt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--themes", default=",".join(THEMES), help="Komma-getrennte Theme-Namen")
    parser.add_argument(
        "--views",
        default=",".join(ANSICHTEN),
        help=f"Komma-getrennte Ansichten aus: {', '.join(ANSICHTEN)}",
    )
    args = parser.parse_args()

    gewaehlt = [v.strip() for v in args.views.split(",") if v.strip()]
    unbekannt = [v for v in gewaehlt if v not in ANSICHTEN]
    if unbekannt:
        raise SystemExit(f"Unbekannte Ansicht(en): {', '.join(unbekannt)}")

    asyncio.run(main([t.strip() for t in args.themes.split(",") if t.strip()], gewaehlt))
