"""Genere le calendrier de marche NewTRY (piste, asset de reference versionne).

Deux couches, indexees par date reelle (heure New York / ET), couvrant
2023-01-01 -> 2025-12-31 :

- reference/market_calendar_days.csv   : 1 ligne / jour calendaire (type de jour).
- reference/market_calendar_events.csv : 0..n lignes / jour (evenements horodates).

Sources des evenements (couche 2) :
- regles deterministes : NFP (1er vendredi), witching (3e vendredi mar/juin/sep/dec),
  OPEX mensuel (3e vendredi) ;
- seeds sourcees officiellement (a_valider=false) :
  * macro_release_dates_seed.csv     (NewTRY B : CPI/PPI/PCE/GDP/Retail, BLS/BEA/Census) ;
  * fed_ism_release_dates_seed.csv   (NewTRY C : FOMC/Jackson Hole/ISM, Fed/ISM).

Reste a sourcer (secondaires/medium) : JOLTS, ADP, jobless claims, FOMC minutes,
beige book, testimony -> voir MARKET_CALENDAR.md.

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
SEED_MACRO = REF_DIR / "macro_release_dates_seed.csv"
SEED_FED_ISM = REF_DIR / "fed_ism_release_dates_seed.csv"

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

# Reunions FOMC avec Summary of Economic Projections (dot plot) : trimestrielles.
SEP_MONTHS = {3, 6, 9, 12}

# Mapping des evenements sourcees (seeds) -> (categorie, cadence, impact, libelle).
SOURCED_META: dict[str, tuple[str, str, str, str]] = {
    "CPI":           ("Inflation", "monthly",   "high",   "Consumer Price Index"),
    "PPI":           ("Inflation", "monthly",   "high",   "Producer Price Index"),
    "PCE":           ("Inflation", "monthly",   "high",   "PCE price index (Personal Income & Outlays)"),
    "RETAIL_SALES":  ("Growth",    "monthly",   "high",   "Advance Monthly Retail Sales"),
    "GDP_ADV":       ("Growth",    "quarterly", "high",   "GDP (advance estimate)"),
    "GDP_INITIAL":   ("Growth",    "quarterly", "high",   "GDP (initial estimate, post-shutdown 2025)"),
    "GDP_2ND":       ("Growth",    "quarterly", "medium", "GDP (second estimate)"),
    "GDP_3RD":       ("Growth",    "quarterly", "medium", "GDP (third estimate)"),
    "FOMC_DECISION": ("Fed",       "8x/year",   "high",   "FOMC rate decision + statement"),
    "FOMC_PRESSER":  ("Fed",       "8x/year",   "high",   "FOMC press conference (Chair)"),
    "JACKSON_HOLE":  ("Fed",       "1x/year",   "high",   "Jackson Hole symposium (Chair speech)"),
    "ISM_MFG":       ("Growth",    "monthly",   "high",   "ISM Manufacturing PMI"),
    "ISM_SVC":       ("Growth",    "monthly",   "high",   "ISM Services PMI"),
}


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

    def add(d, t, code, name, cat, freq, impact, src, a_valider):
        rows.append({
            "date": d, "time_et": t, "event_code": code, "name": name,
            "category": cat, "frequency": freq, "impact": impact,
            "scheduled": True, "a_valider": a_valider, "source": src,
        })

    def load_seed(path: Path, tag: str) -> None:
        if not path.exists():
            return
        seed = pd.read_csv(path, dtype=str).fillna("")
        for _, s in seed.iterrows():
            code = s["event_code"].strip()
            cat, freq, impact, name = SOURCED_META.get(code, ("Macro", "varies", "medium", code))
            if code == "FOMC_DECISION" and int(s["date"][5:7]) in SEP_MONTHS:
                name += " (+SEP/dot plot)"
            add(s["date"].strip(), s["time_et"].strip(), code, name,
                cat, freq, impact, f'{s["source"].strip()} ({tag})', False)

    # Regles deterministes : NFP (1er vendredi), witching/OPEX (3e vendredi).
    for year in range(START.year, END.year + 1):
        for month in range(1, 13):
            nfp = nth_friday(year, month, 1)
            if START <= nfp <= END:
                add(nfp.isoformat(), "08:30", "NFP", "Employment Situation / Nonfarm Payrolls",
                    "Labor", "monthly", "high", "regle 1er vendredi", False)
            opex = nth_friday(year, month, 3)
            if START <= opex <= END:
                if month in SEP_MONTHS:
                    add(opex.isoformat(), "09:30", "WITCHING_TRIPLE",
                        "Triple/Quadruple Witching (index futures+options expiry)",
                        "Structural", "quarterly", "high", "regle 3e vendredi", False)
                add(opex.isoformat(), "16:00", "OPEX_MONTHLY", "Monthly options expiration",
                    "Structural", "monthly", "medium", "regle 3e vendredi", False)

    # Evenements sourcees officiellement (seeds) : macro (NewTRY B) + Fed/ISM (NewTRY C).
    load_seed(SEED_MACRO, "NewTRY B")
    load_seed(SEED_FED_ISM, "NewTRY C")

    df = pd.DataFrame(rows)
    return df.sort_values(["date", "time_et", "event_code"]).reset_index(drop=True)


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
        inputs=[SEED_MACRO, SEED_FED_ISM],
        extra={**common_extra, "layer": "2-events",
               "rule_based": ["NFP", "WITCHING_TRIPLE", "OPEX_MONTHLY"],
               "sourced_NewTRY_B_bls_bea_census": ["CPI", "PPI", "PCE", "RETAIL_SALES",
                                                    "GDP_ADV", "GDP_2ND", "GDP_3RD", "GDP_INITIAL"],
               "sourced_NewTRY_C_fed_ism": ["FOMC_DECISION", "FOMC_PRESSER", "JACKSON_HOLE",
                                            "ISM_MFG", "ISM_SVC"],
               "a_valider_note": ("toutes les dates sont a_valider=false : regle deterministe (NFP/witching/OPEX) "
                                  "ou source officielle (seeds NewTRY B/C). Sources officielles uniques, non "
                                  "re-croisees (sauf FOMC, recoupe avec liste connue)."),
               "seeds": [SEED_MACRO.name, SEED_FED_ISM.name],
               "macro_shutdown_note": ("Shutdown US 2025 : oct-dec 2025 macro irreguliers (CPI oct non publie ; "
                                       "decalages PCE/Retail). Hors fenetre data (finit sept 2025)."),
               "not_populated_yet": ["JOLTS", "ADP", "JOBLESS_CLAIMS", "FOMC_MINUTES", "BEIGE_BOOK", "FED_TESTIMONY"],
               "not_populated_reason": "evenements secondaires/medium, a sourcer ulterieurement si une etude le demande."},
    )

    print(f"days   : {len(days)} lignes -> {DAYS_OUT}")
    print(days["day_status"].value_counts().to_string())
    print(f"\nevents : {len(events)} lignes -> {EVENTS_OUT}")
    print(events["event_code"].value_counts().to_string())

    ev_dt = pd.to_datetime(events["date"], format="%Y-%m-%d")
    weekend = events[ev_dt.dt.dayofweek >= 5]
    dups = events[events.duplicated(subset=["event_code", "date", "time_et"], keep=False)]
    print(f"\nSANITY: dates en week-end = {len(weekend)} | doublons (code,date,heure) = {len(dups)}")
    print("a_valider:", dict(events["a_valider"].value_counts()))
    if len(weekend):
        print(weekend[["date", "event_code"]].to_string(index=False))
    if len(dups):
        print(dups[["date", "event_code", "time_et"]].to_string(index=False))
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
