"""Tests fuer den gebuendelten Export: Formatliste, JSON und Markdown.

Der Dialog liefert nur einen Pfad zurueck - das Format haengt also allein an
seiner Endung. Deshalb pruefen die ersten Tests die Endungslogik so genau:
geht sie daneben, schreibt die Anwendung stillschweigend das falsche Format.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from jira_timesheet.models.export_column import default_columns
from jira_timesheet.models.export_format import (
    DEFAULT_FORMAT,
    EXPORT_FORMATS,
    format_for_key,
    format_for_path,
    format_for_suffix,
    swap_suffix,
)
from jira_timesheet.models.settings import Settings
from jira_timesheet.models.timesheet import Timesheet, TimesheetDay, WorklogEntry
from jira_timesheet.services.exporters import build_exporter, suggested_filename
from jira_timesheet.services.json_exporter import FASSUNG, JsonExporter
from jira_timesheet.services.markdown_exporter import MarkdownExporter


@pytest.fixture
def stundenzettel() -> Timesheet:
    """Ein kleiner Stundenzettel mit zwei Tagen, einer davon manuell erfasst."""

    return beispiel_stundenzettel()


def beispiel_stundenzettel() -> Timesheet:
    """Baut den Beispiel-Stundenzettel dieser Tests.

    Steht neben der Fixture, damit ihn auch andere Testdateien bauen koennen -
    eine Fixture laesst sich nicht einfach importieren und aufrufen.

    Returns:
        Ein Stundenzettel mit zwei Tagen, einer davon manuell erfasst.
    """

    tag1 = TimesheetDay(
        date=date(2026, 9, 1),
        entries=[
            WorklogEntry(
                date=date(2026, 9, 1),
                ticket="PROJ-1201",
                summary="Konsole aufgeraeumt",
                author="Platzhalter, Paula",
                budget="Wartung",
                hours=4.0,
            ),
            WorklogEntry(
                date=date(2026, 9, 1),
                ticket="PROJ-1202",
                summary="WAF blockt | Sonderzeichen",
                author="Platzhalter, Paula",
                budget="Wartung",
                hours=2.5,
            ),
        ],
    )
    tag2 = TimesheetDay(
        date=date(2026, 9, 2),
        entries=[
            WorklogEntry(
                date=date(2026, 9, 2),
                ticket="PROJ-1203",
                summary="Von Hand nachgetragen",
                author="Platzhalter, Paula",
                budget="",
                hours=8.0,
                manual=True,
                manual_id=7,
                customer="Vertrieb",
            )
        ],
    )
    return Timesheet(
        developer="Platzhalter, Paula",
        email="mail@example.invalid",
        date_from=date(2026, 9, 1),
        date_to=date(2026, 9, 30),
        days=[tag1, tag2],
    )


# --- Formatliste und Endungen ---------------------------------------------


def test_jedes_format_hat_eine_eigene_endung() -> None:
    endungen = [f.suffix for f in EXPORT_FORMATS]
    assert len(set(endungen)) == len(endungen), f"Doppelte Endung: {endungen}"
    assert all(e.startswith(".") and e == e.lower() for e in endungen)


def test_die_vier_formate_sind_vollstaendig() -> None:
    assert [f.key for f in EXPORT_FORMATS] == ["excel", "pdf", "json", "markdown"]
    assert DEFAULT_FORMAT.key == "excel"


@pytest.mark.parametrize(
    ("endung", "erwartet"),
    [
        (".xlsx", "excel"),
        (".XLSX", "excel"),
        ("pdf", "pdf"),
        (".json", "json"),
        (".md", "markdown"),
        (".txt", None),
        ("", None),
    ],
)
def test_endung_findet_ihr_format(endung: str, erwartet: str | None) -> None:
    gefunden = format_for_suffix(endung)
    assert (gefunden.key if gefunden else None) == erwartet


def test_format_aus_ganzem_pfad() -> None:
    treffer = format_for_path(Path("C:/tmp/Stundenzettel_2026-09-01.md"))
    assert treffer is not None and treffer.key == "markdown"
    assert format_for_path(Path("C:/tmp/ohne_endung")) is None


def test_unbekannte_kennung_gibt_none() -> None:
    assert format_for_key("csv") is None
    assert format_for_key("PDF") is not None


# --- swap_suffix: das Herzstueck der Formatwahl ----------------------------


def test_bekannte_endung_wird_ersetzt() -> None:
    markdown = format_for_key("markdown")
    assert markdown is not None
    assert swap_suffix("Stundenzettel_2026-09-01.xlsx", markdown) == "Stundenzettel_2026-09-01.md"


def test_gleiche_endung_bleibt_unangetastet() -> None:
    pdf = format_for_key("pdf")
    assert pdf is not None
    assert swap_suffix("Bericht.pdf", pdf) == "Bericht.pdf"
    # Grossschreibung wird erkannt, aber nicht begradigt: die Endung doppelt
    # sich nicht, und der getippte Name bleibt so stehen, wie er dasteht.
    assert swap_suffix("Bericht.PDF", pdf) == "Bericht.PDF"


def test_fremde_endung_bleibt_stehen_und_die_neue_tritt_dahinter() -> None:
    # "Bericht v1.2" darf nicht zu "Bericht v1.md" werden - was der Anwender
    # getippt hat, geht nie verloren.
    markdown = format_for_key("markdown")
    assert markdown is not None
    assert swap_suffix("Bericht v1.2", markdown) == "Bericht v1.2.md"
    assert swap_suffix("Notizen.txt", markdown) == "Notizen.txt.md"


def test_ohne_endung_wird_angehaengt() -> None:
    json_format = format_for_key("json")
    assert json_format is not None
    assert swap_suffix("Stundenzettel", json_format) == "Stundenzettel.json"


def test_leerer_name_bleibt_leer() -> None:
    assert swap_suffix("", DEFAULT_FORMAT) == ""
    assert swap_suffix("   ", DEFAULT_FORMAT) == ""


def test_vorschlagsname_traegt_die_endung_seines_formats(stundenzettel: Timesheet) -> None:
    for export_format in EXPORT_FORMATS:
        name = suggested_filename(export_format, stundenzettel)
        assert name.endswith(export_format.suffix)
        assert format_for_path(name) is export_format


# --- Exporter-Auswahl ------------------------------------------------------


def test_jedes_format_bekommt_seinen_exporter() -> None:
    settings = Settings()
    for export_format in EXPORT_FORMATS:
        exporter = build_exporter(export_format, settings)
        assert hasattr(exporter, "export"), export_format.key


# --- JSON ------------------------------------------------------------------


def test_json_ist_lesbar_und_vollstaendig(stundenzettel: Timesheet, tmp_path: Path) -> None:
    ziel = tmp_path / "zettel.json"
    JsonExporter(jira_host="https://jira.example.invalid/").export(
        stundenzettel,
        missing_days=[(date(2026, 9, 3), "Feiertag")],
        target_hours=160.0,
        output_path=str(ziel),
    )
    daten = json.loads(ziel.read_text(encoding="utf-8"))

    assert daten["fassung"] == FASSUNG
    assert daten["entwickler"] == "Platzhalter, Paula"
    assert daten["zeitraum"] == {"von": "2026-09-01", "bis": "2026-09-30"}
    assert daten["summen"]["gesamt_stunden"] == 14.5
    assert daten["summen"]["arbeitstage"] == 2
    assert daten["summen"]["differenz_stunden"] == -145.5
    assert [t["datum"] for t in daten["tage"]] == ["2026-09-01", "2026-09-02"]
    assert daten["fehlende_tage"] == [{"datum": "2026-09-03", "grund": "Feiertag"}]


def test_json_haelt_auch_die_felder_ausserhalb_der_spalten(stundenzettel: Timesheet, tmp_path: Path) -> None:
    # Der Sinn des Formats: verlustfrei. Eine abgeschaltete Spalte im Ausdruck
    # ist kein Grund, das Feld hier wegzulassen.
    spalten = default_columns()
    for spalte in spalten:
        spalte.enabled = False
    ziel = tmp_path / "zettel.json"
    JsonExporter(jira_host="https://jira.example.invalid").export(stundenzettel, output_path=str(ziel))

    eintrag = json.loads(ziel.read_text(encoding="utf-8"))["tage"][0]["eintraege"][0]
    for feld in ("author", "budget", "status", "issuetype", "epic", "manual", "manual_id"):
        assert feld in eintrag, feld
    assert eintrag["url"] == "https://jira.example.invalid/browse/PROJ-1201"


def test_json_schreibt_lf_und_keine_crlf(stundenzettel: Timesheet, tmp_path: Path) -> None:
    # read_bytes, nicht read_text - Textmodus wuerde CRLF beim Lesen glaetten
    # und der Test koennte den Fehler gar nicht sehen.
    ziel = tmp_path / "zettel.json"
    JsonExporter().export(stundenzettel, output_path=str(ziel))
    assert b"\r\n" not in ziel.read_bytes()


def test_json_faellt_auf_den_vorgabe_kunden_zurueck(stundenzettel: Timesheet, tmp_path: Path) -> None:
    ziel = tmp_path / "zettel.json"
    JsonExporter(default_customer="Vertrieb").export(stundenzettel, output_path=str(ziel))
    eintrag = json.loads(ziel.read_text(encoding="utf-8"))["tage"][0]["eintraege"][0]
    assert eintrag["customer"] == "Vertrieb"


# --- Markdown --------------------------------------------------------------


def test_markdown_hat_kopf_und_tabelle(stundenzettel: Timesheet) -> None:
    text = MarkdownExporter().render(stundenzettel, target_hours=160.0)
    zeilen = text.splitlines()

    assert zeilen[0] == "# Stundenzettel"
    assert "- **Entwickler:** Platzhalter, Paula" in zeilen
    assert "- **Zeitraum:** 01.09.2026 - 30.09.2026" in zeilen
    assert "- **Gesamt:** 14.50 h" in zeilen
    assert any("**Differenz:** -145.50 h" in z for z in zeilen)


def test_markdown_tabelle_ist_rechteckig(stundenzettel: Timesheet) -> None:
    text = MarkdownExporter().render(stundenzettel, missing_days=[(date(2026, 9, 3), "Feiertag")])
    tabelle = [z for z in text.splitlines() if z.startswith("|")]
    # Nach unmaskierten Strichen trennen - ein "\|" im Text ist Inhalt und
    # kein Spaltenwechsel, sonst zaehlt der Test die falsche Groesse.
    spaltenzahl = {len(re.split(r"(?<!\\)\|", z)) for z in tabelle}
    assert len(spaltenzahl) == 1, f"Zeilen mit unterschiedlicher Spaltenzahl: {tabelle}"
    # Kopf, Trennzeile, drei Buchungen, ein Feiertag.
    assert len(tabelle) == 6


def test_markdown_maskiert_senkrechte_striche_im_text(stundenzettel: Timesheet) -> None:
    # "WAF blockt | Sonderzeichen" wuerde die Tabelle sonst sprengen.
    text = MarkdownExporter().render(stundenzettel)
    assert "WAF blockt \\| Sonderzeichen" in text
    assert "| WAF blockt | Sonderzeichen |" not in text


def test_markdown_verlinkt_tickets_nur_auf_wunsch(stundenzettel: Timesheet) -> None:
    ohne = MarkdownExporter(jira_host="https://jira.example.invalid").render(stundenzettel)
    assert "](https://jira.example.invalid/browse/PROJ-1201)" not in ohne

    mit = MarkdownExporter(
        jira_host="https://jira.example.invalid",
        show_ticket_links=True,
    ).render(stundenzettel)
    assert "[PROJ-1201](https://jira.example.invalid/browse/PROJ-1201)" in mit


def test_markdown_kennzeichnet_manuelle_eintraege(stundenzettel: Timesheet) -> None:
    assert "*PROJ-1203*" in MarkdownExporter().render(stundenzettel)
    assert "*PROJ-1203*" not in MarkdownExporter(mark_manual=False).render(stundenzettel)


def test_markdown_folgt_der_spaltenkonfiguration(stundenzettel: Timesheet) -> None:
    spalten = default_columns()
    for spalte in spalten:
        spalte.enabled = spalte.key in ("date", "ticket", "hours")
    text = MarkdownExporter(columns=spalten).render(stundenzettel)

    kopf = text.splitlines()[6]
    assert kopf == "| Datum | Ticket | Aufwand (h) |"
    # Zahlen rechts, Text links.
    assert text.splitlines()[7] == "| --- | --- | ---: |"
    assert "Konsole aufgeraeumt" not in text


def test_markdown_schreibt_lf_und_keine_crlf(stundenzettel: Timesheet, tmp_path: Path) -> None:
    ziel = tmp_path / "zettel.md"
    MarkdownExporter().export(stundenzettel, output_path=str(ziel))
    assert b"\r\n" not in ziel.read_bytes()
