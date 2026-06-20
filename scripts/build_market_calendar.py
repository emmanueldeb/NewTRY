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
SEED_MACRO = REF_DIR / "macro_release_dates_seed.csv"

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

# Jackson Hole symposium (discours du Chair), ~10:00 ET. A VALIDER.
JACKSON_HOLE = ["2023-08-25", "2024-08-23", "2025-08-22"]

# Feries federaux tombant dans les 3 premiers jours ouvres d'un mois
# (necessaires pour calculer le 1er/3e jour ouvre ISM). A VALIDER.
EARLY_MONTH_HOLIDAYS = {
    "2023-01-02", "2024-01-01", "2025-01-01",   # New Year (observed)
    "2023-07-04", "2024-07-04", "2025-07-04",   # Independence Day
    "2023-09-04", "2024-09-02", "2025-09-01",   # Labor Day
}

# Mapping des publications macro sourcees (seed) -> categorie / cadence / impact.
MACRO_META = {
    "CPI":          ("Inflation", "monthly",   "high"),
    "PPI":          ("Inflation", "monthly",   "high"),
    "PCE":          ("Inflation", "monthly",   "high"),
    "RETAIL_SALES": ("Growth",    "monthly",   "high"),
    "GDP_ADV":      ("Growth",    "quarterly", "high"),
    "GDP_INITIAL":  ("Growth",    "quarterly", "high"),
    "GDP_2ND":      ("Growth",    "quarterly", "medium"),
    "GDP_3RD":      ("Growth",    "quarterly", "medium"),
}
MACRO_NAMES = {
    "CPI": "Consumer Price Index",
    "PPI": "Producer Price Index",
    "PCE": "PCE price index (Personal Income & Outlays)",
    "RETAIL_SALES": "Advance Monthly Retail Sales",
    "GDP_ADV": "GDP (advance estimate)",
    "GDP_2ND": "GDP (second estimate)",
    "GDP_3RD": "GDP (third estimate)",
    "GDP_INITIAL": "GDP (initial estimate, post-shutdown 2025)",
}


def nth_friday(year: int, month: int, n: int) -> date:
    d = date(year, month, 1)
    offset = (4 - d.weekday()) % 7  # 4 = Friday
    return date(year, month, 1 + offset + (n - 1) * 7)


def nth_business_day(year: int, month: int, n: int) -> date | None:
    """n-ieme jour ouvre du mois (Lun-Ven hors feries federaux de debut de mois)."""
    count = 0
    d = date(year, month, 1)
    while d.month == month:
        if d.weekday() < 5 and d.isoformat() not in EARLY_MONTH_HOLIDAYS:
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)
    return None


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

    for year in range(START.year, END.year + 1):
        for month in range(1, 13):
            nfp = nth_friday(year, month, 1)
            if START <= nfp <= END:
                add(nfp.isoformat(), "08:30", "NFP", "Employment Situation / Nonfarm Payrolls",
                    "Labor", "monthly", "high", "BLS (regle 1er vendredi)", False)
            opex = nth_friday(year, month, 3)
            if START <= opex <= END:
                if month in SEP_MONTHS:
                    add(opex.isoformat(), "09:30", "WITCHING_TRIPLE",
                        "Triple/Quadruple Witching (index futures+options expiry)",
                        "Structural", "quarterly", "high", "CME (regle 3e vendredi)", False)
                add(opex.isoformat(), "16:00", "OPEX_MONTHLY", "Monthly options expiration",
                    "Structural", "monthly", "medium", "CME (regle 3e vendredi)", False)
            ism_m = nth_business_day(year, month, 1)
            if ism_m and START <= ism_m <= END:
                add(ism_m.isoformat(), "10:00", "ISM_MFG", "ISM Manufacturing PMI",
                    "Growth", "monthly", "high", "rule 1er jour ouvre", True)
            ism_s = nth_business_day(year, month, 3)
            if ism_s and START <= ism_s <= END:
                add(ism_s.isoformat(), "10:00", "ISM_SVC", "ISM Services PMI",
                    "Growth", "monthly", "high", "rule 3e jour ouvre", True)

    for iso in FOMC_DECISIONS:
        if START <= date.fromisoformat(iso) <= END:
            month = int(iso[5:7])
            sep = " (+SEP/dot plot)" if month in SEP_MONTHS else ""
            add(iso, "14:00", "FOMC_DECISION", f"FOMC rate decision + statement{sep}",
                "Fed", "8x/year", "high", "Fed", True)
            add(iso, "14:30", "FOMC_PRESSER", "FOMC press conference (Chair)",
                "Fed", "8x/year", "high", "Fed", True)

    for iso in JACKSON_HOLE:
        if START <= date.fromisoformat(iso) <= END:
            add(iso, "10:00", "JACKSON_HOLE", "Jackson Hole symposium (Chair speech)",
                "Fed", "1x/year", "high", "Fed", True)

    # Publications macro a dates variables, sourcees (seed NewTRY B / Codex, sources officielles).
    if SEED_MACRO.exists():
        seed = pd.read_csv(SEED_MACRO, dtype=str).fillna("")
        for _, s in seed.iterrows():
            code = s["event_code"].strip()
            cat, freq, impact = MACRO_META.get(code, ("Macro", "varies", "medium"))
            add(s["date"].strip(), s["time_et"].strip(), code, MACRO_NAMES.get(code, code),
                cat, freq, impact, f'{s["source"].strip()} (NewTRY B, officiel)', False)

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
        inputs=[SEED_MACRO],
        extra={**common_extra, "layer": "2-events",
               "populated_reliable": ["NFP", "WITCHING_TRIPLE", "OPEX_MONTHLY",
                                      "CPI", "PPI", "PCE", "RETAIL_SALES",
                                      "GDP_ADV", "GDP_2ND", "GDP_3RD", "GDP_INITIAL"],
               "populated_a_valider": ["FOMC_DECISION", "FOMC_PRESSER", "ISM_MFG", "ISM_SVC", "JACKSON_HOLE"],
               "a_valider_note": ("a_valider=true reserve aux dates non sourcees officiellement : FOMC et Jackson Hole "
                                  "(liste connue/memoire), ISM (regle 1er/3e jour ouvre). Macro sourcees officiellement "
                                  "(BLS/BEA/Census via NewTRY B) = a_valider=false, mais source unique non re-croisee."),
               "macro_seed": SEED_MACRO.name,
               "macro_shutdown_note": ("Shutdown US 2025 : oct-dec 2025 irreguliers (CPI oct non publie ; sept/oct decales ; "
                                       "PCE/Retail combines/repousses). Hors fenetre data (finit sept 2025)."),
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
