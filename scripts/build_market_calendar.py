"""Genere le calendrier de marche NewTRY (piste, asset de reference versionne).

Deux couches, indexees par date reelle (heure New York / ET), couvrant
2023-01-01 -> 2025-12-31 :

- reference/market_calendar_days.csv   : 1 ligne / jour calendaire (type de jour).
- reference/market_calendar_events.csv : 0..n lignes / jour (evenements horodates).

Contenu deterministe seulement :
- jours/feries/demi-seances US (regles standard, corrobores par l'audit CSV 2024-2025) ;
- NFP (1er vendredi), witching (3e vendredi mar/juin/sep/dec), OPEX mensuel (3e vendredi) ;
- dates FOMC (liste connue, source Fed, A VALIDER).

NON peuple ici (a sourcer depuis les calendriers officiels BLS/BEA/ISM) :
- CPI, PCE, PPI, GDP, Retail Sales, JOLTS, ISM, claims, etc. -> voir MARKET_CALENDAR.md.

Statut : PISTE. Ne lie pas le canon. Lancer via runtime/run_python.cmd.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from lib.provenance import write_csv_with_provenance

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REF_DIR = PROJECT_ROOT / "reference"
DAYS_OUT = REF_DIR / "market_calendar_days.csv"
EVENTS_OUT = REF_DIR / "market_calendar_events.csv"

START = date(2023, 1, 1)
END = date(2025, 12, 31)
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# --- Feries / demi-seances FUTURES CME equity (ET). Regles US standard ;
#     types de seance corrobores par l'audit CSV 2024-2025 (13:00 vs 13:15). A VALIDER pour 2023. ---
# status: holiday_full_close (seance de jour fermee) | half_day (early close) | holiday_special
HOLIDAYS: dict[str, tuple[str, str, str]] = {
    # date            status                 early_close_et  name
    "2023-01-02": ("holiday_full_close", "", "New Year's Day (observed)"),
    "2023-01-16": ("half_day", "13:00", "Martin Luther King Jr. Day"),
    "2023-02-20": ("half_day", "13:00", "Washington's Birthday"),
    "2023-04-07": ("holiday_full_close", "", "Good Friday"),
    "2023-05-29": ("half_day", "13:00", "Memorial Day"),
    "2023-06-19": ("half_day", "13:00", "Juneteenth"),
    "2023-07-03": ("half_day", "13:15", "Day before Independence Day"),
    "2023-07-04": ("holiday_full_close", "", "Independence Day"),
    "2023-09-04": ("half_day", "13:00", "Labor Day"),
    "2023-11-23": ("half_day", "13:00", "Thanksgiving Day"),
    "2023-11-24": ("half_day", "13:15", "Day after Thanksgiving"),
    "2023-12-25": ("holiday_full_close", "", "Christmas Day"),

    "2024-01-01": ("holiday_full_close", "", "New Year's Day"),
    "2024-01-15": ("half_day", "13:00", "Martin Luther King Jr. Day"),
    "2024-02-19": ("half_day", "13:00", "Washington's Birthday"),
    "2024-03-29": ("holiday_full_close", "", "Good Friday"),
    "2024-05-27": ("half_day", "13:00", "Memorial Day"),
    "2024-06-19": ("half_day", "13:00", "Juneteenth"),
    "2024-07-03": ("half_day", "13:15", "Day before Independence Day"),
    "2024-07-04": ("holiday_full_close", "", "Independence Day"),
    "2024-09-02": ("half_day", "13:00", "Labor Day"),
    "2024-11-28": ("half_day", "13:00", "Thanksgiving Day"),
    "2024-11-29": ("half_day", "13:15", "Day after Thanksgiving"),
    "2024-12-24": ("half_day", "13:15", "Christmas Eve"),
    "2024-12-25": ("holiday_full_close", "", "Christmas Day"),

    "2025-01-01": ("holiday_full_close", "", "New Year's Day"),
    "2025-01-09": ("holiday_special", "09:30", "National Day of Mourning (J. Carter)"),
    "2025-01-20": ("half_day", "13:00", "Martin Luther King Jr. Day"),
    "2025-02-17": ("half_day", "13:00", "Washington's Birthday"),
    "2025-04-18": ("holiday_full_close", "", "Good Friday"),
    "2025-05-26": ("half_day", "13:00", "Memorial Day"),
    "2025-06-19": ("half_day", "13:00", "Juneteenth"),
    "2025-07-03": ("half_day", "13:15", "Day before Independence Day"),
    "2025-07-04": ("holiday_full_close", "", "Independence Day"),
    "2025-09-01": ("half_day", "13:00", "Labor Day"),
    "2025-11-27": ("half_day", "13:00", "Thanksgiving Day"),
    "2025-11-28": ("half_day", "13:15", "Day after Thanksgiving"),
    "2025-12-24": ("half_day", "13:15", "Christmas Eve"),
    "2025-12-25": ("holiday_full_close", "", "Christmas Day"),
}

# --- Dates FOMC (jour d'annonce, 14:00 ET). Source Fed, A VALIDER. ---
FOMC_DECISIONS = [
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
]
# Reunions avec Summary of Economic Projections (dot plot) : trimestrielles.
SEP_MONTHS = {3, 6, 9, 12}


def nth_friday(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (4 - d.weekday()) % 7  # 4 = Friday
    return date(year, month, 1 + offset + (n - 1) * 7)


def build_days() -> pd.DataFrame:
    rows = []
    d = START
    while d <= END:
        iso = d.isoformat()
        wd = d.weekday()
        if iso in HOLIDAYS:
            status, early, name = HOLIDAYS[iso]
        elif wd == 5:
            status, early, name = "saturday", "", ""
        elif wd == 6:
            status, early, name = "sunday", "", ""   # ouverture 18:00 ET (debut de semaine)
        else:
            status, early, name = "regular", "", ""
        rows.append({
            "date": iso,
            "dow": DOW[wd],
            "day_status": status,
            "early_close_et": early,
            "holiday_name": name,
            "counted_day": wd != 5,   # numerotation simple : chaque jour sauf samedi
        })
        d += timedelta(days=1)
    return pd.DataFrame(rows)


def build_events() -> pd.DataFrame:
    rows = []

    def add(d: str, t: str, code: str, name: str, cat: str, freq: str, impact: str, src: str):
        rows.append({
            "date": d, "time_et": t, "event_code": code, "name": name,
            "category": cat, "frequency": freq, "impact": impact,
            "scheduled": True, "source": src,
        })

    for year in range(START.year, END.year + 1):
        for month in range(1, 13):
            nfp = nth_friday(year, month, 1)
            if START <= nfp <= END:
                add(nfp.isoformat(), "08:30", "NFP", "Employment Situation / Nonfarm Payrolls",
                    "Labor", "monthly", "high", "BLS")
            opex = nth_friday(year, month, 3)
            if START <= opex <= END:
                if month in SEP_MONTHS:
                    add(opex.isoformat(), "09:30", "WITCHING_TRIPLE",
                        "Triple/Quadruple Witching (index futures+options expiry)",
                        "Structural", "quarterly", "high", "CME")
                add(opex.isoformat(), "16:00", "OPEX_MONTHLY", "Monthly options expiration",
                    "Structural", "monthly", "medium", "CME")

    for iso in FOMC_DECISIONS:
        if START <= date.fromisoformat(iso) <= END:
            month = int(iso[5:7])
            sep = " (+SEP/dot plot)" if month in SEP_MONTHS else ""
            add(iso, "14:00", "FOMC_DECISION", f"FOMC rate decision + statement{sep}",
                "Fed", "8x/year", "high", "Fed (a valider)")
            add(iso, "14:30", "FOMC_PRESSER", "FOMC press conference (Chair)",
                "Fed", "8x/year", "high", "Fed (a valider)")

    df = pd.DataFrame(rows)
    return df.sort_values(["date", "time_et"]).reset_index(drop=True)


def main() -> int:
    REF_DIR.mkdir(parents=True, exist_ok=True)
    days = build_days()
    events = build_events()

    common_extra = {
        "status": "piste",
        "scope": "Calendrier de marche US (ET) pour annoter les CSV a la carte; ne lie pas le canon.",
        "coverage": f"{START.isoformat()}..{END.isoformat()}",
        "join_key": "date (extraire la partie date du timestamp CSV; CSV en heure New York/ET)",
        "timezone": "America/New_York (ET), coherent avec l'affichage Sierra (reprise 18:00 ET).",
    }
    write_csv_with_provenance(
        days, DAYS_OUT, script=Path(__file__).resolve(), project_root=PROJECT_ROOT,
        extra={**common_extra, "layer": "1-days",
               "day_status_values": ["regular", "half_day", "holiday_full_close",
                                      "holiday_special", "saturday", "sunday"],
               "holiday_session_types_validation": "corrobore par audit CSV 2024-2025; 2023 par regle/convention",
               "numbering_note": "counted_day=False uniquement le samedi (numerotation simple 'chaque jour sauf samedi')."},
    )
    write_csv_with_provenance(
        events, EVENTS_OUT, script=Path(__file__).resolve(), project_root=PROJECT_ROOT,
        extra={**common_extra, "layer": "2-events",
               "populated": ["NFP", "WITCHING_TRIPLE", "OPEX_MONTHLY", "FOMC_DECISION", "FOMC_PRESSER"],
               "not_populated_yet": ["CPI", "PCE", "PPI", "GDP", "RETAIL_SALES", "JOLTS",
                                     "ISM_MFG", "ISM_SVC", "JOBLESS_CLAIMS", "FOMC_MINUTES",
                                     "BEIGE_BOOK", "FED_TESTIMONY", "JACKSON_HOLE"],
               "not_populated_reason": "dates variables a sourcer depuis calendriers officiels BLS/BEA/ISM/Fed."},
    )

    print(f"days   : {len(days)} lignes -> {DAYS_OUT}")
    print(days["day_status"].value_counts().to_string())
    print(f"\nevents : {len(events)} lignes -> {EVENTS_OUT}")
    print(events["event_code"].value_counts().to_string())
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
