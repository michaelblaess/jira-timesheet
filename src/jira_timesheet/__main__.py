"""CLI Entry Point fuer jira-timesheet."""

from __future__ import annotations

import argparse

from textual_widgets import reset_terminal_title, set_terminal_title

from jira_timesheet import __version__
from jira_timesheet.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, load_locale
from jira_timesheet.models.settings import Settings

BANNER = f"Jira Timesheet v{__version__} — TUI für Jira Stundenzettel"

USAGE_EXAMPLES = """
Beispiele:
  jira-timesheet
  jira-timesheet --lang en
  jira-timesheet --version
"""


def main() -> None:
    """Haupteinstiegspunkt."""
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


if __name__ == "__main__":
    main()
