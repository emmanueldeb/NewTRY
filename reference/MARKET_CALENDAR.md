# MARKET_CALENDAR (piste)

Calendrier de marché US (NQ/ES, CME equity), en **heure New York (ET)**, pour
**annoter les CSV à la carte** lors des analyses : segmenter, marquer ou exclure
des jours/événements (ex. retirer les « grosses journées » des calculs de
moyenne). **Statut : piste — ne lie pas le canon.**

Couverture : **2023-01-01 → 2025-12-31** (couvre la vie back-month des échéances
H/M/U/Z 2024 et 2025). Trivialement extensible en éditant `START`/`END`.

## Principe : couche absolue + axe relatif

- Ce calendrier est une **couche absolue**, indexée par **date réelle**.
- L'**axe de comparaison** entre contrats, lui, est **relatif** au contrat :
  `age_from_prev_contract_end` (`jour 0` = première vraie séance après le dernier
  jour de cotation du contrat précédent ; numérotation simple, **chaque jour sauf
  le samedi**). Cet axe se calcule à l'analyse, il n'est **pas** stocké ici.
- Les deux se **joignent par la date réelle**. Aucune logique calendaire n'est
  enfouie dans l'axe : la finesse vit ici, et on l'applique à la demande.

Clé de jointure : la **partie date** du timestamp CSV (format
`YYYY-MM-DD␠␠HH:MM:SS.ffffff`, deux espaces ; déjà en ET).

## Fichiers

Générés par [`scripts/build_market_calendar.py`](../scripts/build_market_calendar.py)
(reproductible, provenance dans les `.meta.json`). Régénérer :
`runtime/run_python.cmd scripts/build_market_calendar.py`.

### Couche 1 — `market_calendar_days.csv` (1 ligne / jour calendaire)

| colonne | sens |
|---|---|
| `date` | `YYYY-MM-DD` (ET) |
| `dow` | jour de semaine (`Mon`..`Sun`) |
| `day_status` | `regular` / `half_day` / `holiday_full_close` / `holiday_special` / `saturday` / `sunday` |
| `early_close_et` | heure de clôture anticipée si `half_day`/spécial (`13:00`, `13:15`, `09:30`), sinon vide |
| `holiday_name` | nom du férié/demi-séance, sinon vide |
| `counted_day` | `True` sauf le samedi (= « chaque jour sauf samedi ») |

Notes :
- `sunday` = ouverture en soirée (18:00 ET), début de la semaine de trading.
- `half_day` 13:00 : MLK, Presidents, Memorial, Juneteenth, Labor, Thanksgiving.
  13:15 : veille d'Independence Day, lendemain de Thanksgiving, Christmas Eve.
- `holiday_full_close` : New Year, Good Friday, Independence Day, Christmas
  (séance de jour fermée ; réouverture 18:00 ET le soir).
- `holiday_special` : 2025-01-09, deuil national (J. Carter), clôture ~09:30 ET.

### Couche 2 — `market_calendar_events.csv` (0..n lignes / jour)

| colonne | sens |
|---|---|
| `date`, `time_et` | date + heure ET de publication |
| `event_code`, `name` | identifiant + libellé |
| `category` | `Fed` / `Labor` / `Inflation` / `Growth` / `Sentiment` / `Housing` / `Structural` |
| `frequency` | cadence |
| `impact` | `high` / `medium` / `low` (pour le filtrage à la carte) |
| `scheduled` | `True` = date déterministe/connue à l'avance |
| `a_valider` | `true` = date par règle/liste à recontrôler (ISM, FOMC, Jackson Hole) |
| `source` | `BLS` / `Fed` / `BEA` / `ISM` / `CME` / `rule` / `manual` |

**Peuplé** (dates présentes dans le CSV) :

| code | heure ET | cadence | impact | `a_valider` |
|---|---|---|---|---|
| `NFP` | 08:30 | mensuel (1er vendredi) | high | false (règle) |
| `WITCHING_TRIPLE` | 09:30 | trim. (3e vendredi mar/juin/sep/déc) | high | false (règle) |
| `OPEX_MONTHLY` | 16:00 | mensuel (3e vendredi) | medium | false (règle) |
| `FOMC_DECISION` (+SEP trim.) | 14:00 | 8×/an | high | **true** (liste Fed) |
| `FOMC_PRESSER` | 14:30 | 8×/an | high | **true** (liste Fed) |
| `ISM_MFG` | 10:00 | mensuel (1er jour ouvré) | high | **true** (règle + fériés) |
| `ISM_SVC` | 10:00 | mensuel (3e jour ouvré) | high | **true** (règle + fériés) |
| `JACKSON_HOLE` | ~10:00 | 1×/an (fin août) | high | **true** (3 dates) |

Les lignes `a_valider=true` sont à recontrôler avant tout usage critique : ISM
par règle (le jour ouvré exact peut varier autour des fériés), FOMC et Jackson
Hole depuis une liste connue (non re-vérifiée à la source).

**Publications macro à dates variables** (sourcées via la session Codex
*NewTRY B*, depuis les calendriers/archives officiels ; `a_valider=true`, source
unique non re-croisée — seed éditable `macro_release_dates_seed.csv`) :

| code | heure ET | cadence | impact |
|---|---|---|---|
| `CPI` | 08:30 | mensuel | high |
| `PCE` | 08:30 | mensuel | high |
| `PPI` | 08:30 | mensuel | medium |
| `RETAIL_SALES` | 08:30 | mensuel | high |
| `GDP_ADV` / `GDP_INITIAL` | 08:30 | trimestriel | high |
| `GDP_2ND` / `GDP_3RD` | 08:30 | trimestriel | medium |

Irrégularités **shutdown US 2025** intégrées telles quelles (CPI d'octobre 2025
non publié ; sept./oct. décalés ; PCE/Retail combinés/repoussés ; GDP Q3 2025 =
`GDP_INITIAL` le 23 déc.). C'est **après la fin des données (sept. 2025)** →
impact analytique négligeable. Contrôle local : 0 date en week-end, 0 doublon.

> `WITCHING_TRIPLE` tombe sur l'expiry des contrats — c'est la fenêtre du
> roll-out observée dans l'audit `age_from_prev_contract_end`. Grosse journée
> **ouverte**, à ne pas confondre avec un congé.

## Restent à sourcer (secondaires / medium, non peuplés)

Les événements high sont peuplés (voir plus haut). Restent des indicateurs
d'impact medium/secondaire, à dater seulement si une étude les réclame (heures
stables ; dates à sourcer) :

| code | heure ET | cadence | impact | source |
|---|---|---|---|---|
| `JOLTS` | 10:00 | mensuel | medium | BLS |
| `ADP` | 08:15 | mensuel | medium | ADP |
| `JOBLESS_CLAIMS` | 08:30 | hebdo (jeudi) | medium | DOL |
| `ECI` | 08:30 | trimestriel | medium→high | BLS |
| `DURABLE_GOODS` | 08:30 | mensuel | medium | Census |
| `INDUSTRIAL_PROD` | 09:15 | mensuel | medium | Fed |
| `PMI_FLASH` | 09:45 | mensuel | medium | S&P Global |
| `CONSUMER_CONF` | 10:00 | mensuel | medium | Conf. Board |
| `MICHIGAN_SENT` | 10:00 | mensuel (prelim+final) | medium | U. Michigan |
| `FOMC_MINUTES` | 14:00 | 8×/an (J+3 sem) | medium | Fed |
| `BEIGE_BOOK` | 14:00 | 8×/an | medium | Fed |
| `FED_TESTIMONY` | 10:00 | 2×/an (fév/juil) | high | Fed |

Note d'accès : BLS/FRED/Census bloquent le WebFetch automatisé (403/404) ; le
sourcing des macro déjà peuplées a été fait via la session Codex *NewTRY B*
(accès navigateur). Même voie possible pour ces indicateurs si besoin.

Couche **discrétionnaire** (à annoter à la main, `scheduled=False`, étiquetée
piste) : annonces tarifaires (ex. 2 avr. 2025), chocs géopolitiques, élections.
Périmètre **US uniquement** (EU/Asie : impact marginal sur RTH US).

Les **haltes isolées** (DCB ~2 min, coupe-circuit ~10 min) sont *event-driven* et
*intraday* : à marquer comme événements horodatés **observés** (non programmés),
pas comme attribut de jour.

## Usage à la carte

- **Tagger** chaque séquence CSV par jointure sur `date` → type de jour + événements.
- **Exclure des moyennes** : dériver un `is_high_impact_day` (jour portant ≥1
  événement `impact=high`) et filtrer à la demande.
- **Segmenter** : comparer `G_open` (ou toute variable) jours normaux vs FOMC,
  demi-séances, witching, etc.

## Provenance & niveau de confiance

- **Jours/fériés/demi-séances** : règles US standard ; types de séance
  (13:00 vs 13:15) **corroborés par l'audit CSV 2024-2025** ; **2023 par
  règle/convention** (pas encore de CSV pour cross-check).
- **FOMC / Jackson Hole** : dates connues, `a_valider=true`.
- **NFP / witching / OPEX** : règles déterministes (1er / 3e vendredi).
- **ISM mfg/svc** : règle 1er/3e jour ouvré (fériés fédéraux), `a_valider=true`.
- **Macro variables (CPI/PPI/PCE/GDP/Retail)** : sourcées via Codex *NewTRY B*
  depuis BLS/BEA/Census (officiel, source unique non re-croisée), `a_valider=true` ;
  seed `macro_release_dates_seed.csv`. Contrôle local : 0 date en week-end, 0 doublon.

Tout est régénérable et horodaté via les `.meta.json`. Aucune de ces entrées ne
devient canon sans validation explicite et une entrée datée dans `DECISIONS.md`.
