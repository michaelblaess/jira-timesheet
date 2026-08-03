"""CLI Entry Point fuer jira-timesheet."""

from __future__ import annotations

import argparse
import contextlib
import faulthandler
import sys
from datetime import datetime
from typing import TextIO

from textual_widgets import reset_terminal_title, set_terminal_title

from jira_timesheet import __version__
from jira_timesheet.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, load_locale
from jira_timesheet.models.settings import Settings

# Log-Handle offen halten, solange der Prozess laeuft - faulthandler schreibt
# beim fatalen Signal direkt hinein. Ohne Referenz wuerde der GC es schliessen.
_fault_log: TextIO | None = None

BANNER = f"Jira Timesheet v{__version__} — TUI für Jira Stundenzettel"

USAGE_EXAMPLES = """
Beispiele:
  jira-timesheet
  jira-timesheet --lang en
  jira-timesheet --version
"""


def main() -> None:
    """Haupteinstiegspunkt."""
    _enable_faulthandler()
    settings = Settings.load()
    saved_lang = settings.language if settings.language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    parser = argparse.ArgumentParser(
        prog="jira-timesheet",
        description=BANNER,
        epilog=USAGE_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--lang",
        default=saved_lang,
        choices=SUPPORTED_LANGUAGES,
        help="Sprache der Oberfläche (Default: gespeicherte Einstellung)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Sprache laden, BEVOR die App-Klasse importiert wird - sonst sind
    # t()-Aufrufe auf Modul-Ebene leer.
    load_locale(args.lang)

    # Per CLI gewaehlte Sprache persistieren.
    if args.lang != saved_lang:
        settings.language = args.lang
        settings.save()

    # Terminal-Tab-Titel setzen - Textual macht das nicht selbst.
    set_terminal_title(f"◷ jira-timesheet v{__version__}")
    try:
        from jira_timesheet.app import JiraTimesheetApp

        app = JiraTimesheetApp()
        app.run()
    finally:
        reset_terminal_title()
        # Nach einem harten Absturz laesst Textuals Windows-Teardown das
        # Maus-Tracking an - danach kippt jede Mausbewegung Steuerzeichen-Muell
        # in die Shell. Hier abschalten, auch bei Crash (finally).
        _reset_mouse_tracking()


def _enable_faulthandler() -> None:
    """Faengt HARTE Abstuerze ab, die an Pythons Exception-Handling UND am
    finally-Block vorbeilaufen: native Access Violation, Stack-Overflow, fataler
    Interpreter-Fehler.

    faulthandler installiert einen Handler fuer fatale Signale (unter Windows
    auch fuer Access Violations) und schreibt beim Absturz den Traceback aller
    Threads in fault.log - separat vom Terminal, das der Maus-Tracking-Muell
    sonst unlesbar macht. Der CrashGuard und _persist_crash greifen nur bei
    normalen Python-Exceptions, dieser Handler bei allem darunter.
    """
    global _fault_log
    with contextlib.suppress(Exception):
        Settings.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        # Bewusst offen lassen (Prozess-Lebensdauer) - faulthandler schreibt
        # beim fatalen Signal direkt in dieses Handle.
        _fault_log = open(Settings.SETTINGS_DIR / "fault.log", "a", encoding="utf-8")  # noqa: SIM115
        _fault_log.write(f"\n===== Start {datetime.now():%Y-%m-%d %H:%M:%S} - v{__version__} =====\n")
        _fault_log.flush()
        faulthandler.enable(file=_fault_log, all_threads=True)


def _reset_mouse_tracking() -> None:
    """Schaltet alle Maus-Tracking-Modi des Terminals ab (idempotent).

    ?1000/?1002/?1003 = Tracking-Modi, ?1006/?1015 = erweitertes Encoding.
    Sind sie bereits aus, bewirken die Sequenzen nichts.

    Schreibt bewusst nach sys.__stdout__, NICHT sys.stdout: Textual kapert
    sys.stdout zur Laufzeit, ein Reset dorthin landet im Nichts und das Terminal
    bleibt im Maus-Tracking-Modus haengen. sys.__stdout__ ist die echte Konsole.
    Der garantierte Reset passiert ohnehin im Shell-Wrapper run.ps1 (laeuft auch
    nach einem harten Crash) - das hier ist der zusaetzliche In-Prozess-Pfad.
    """
    stream = sys.__stdout__
    if stream is None or not stream.isatty():
        return
    stream.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l")
    stream.flush()


if __name__ == "__main__":
    main()
