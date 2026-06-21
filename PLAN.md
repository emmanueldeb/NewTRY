# PLAN - NewTRY

> Porte d'entree minimale. Ce fichier doit rester court. Il sert a savoir ou
> en est NewTRY sans reconstruire toute l'histoire de TRY_plan.

## 0. Regle de lecture

Au demarrage d'une session, lire :

- `PLAN.md`
- `CLAUDE.md` ou `AGENTS.md`
- `docs/COLLABORATION_NOTES.md`

`IDEES.md` est un parking optionnel : le lire seulement si une piste non active
est discutee.

`reference/MARKET_CALENDAR.md` documente un calendrier de marche (piste) : le
consulter seulement si une analyse utilise le calendrier de marche ou l'age
contrat (`age_from_prev_contract_end`).

Ne pas charger les documents de TRY_plan par defaut. Les consulter seulement
pour une composante precise.

## 1. Objectif

Reconstruire, de facon progressive et controlable, le travail utile de TRY_plan
sans importer son entropie documentaire ni ses outputs suspects.

Principes :

- variables directes uniquement : prix, volume, range, duree, gap, delta, VAP,
  zones, clusters ;
- pas d'indicateurs derives dans la base de variables ;
- simplisme prefere ; complexite acceptee seulement si justifiee et maitrisee ;
- aucune conclusion temporelle importee sans regeneration sous runtime
  verrouille ;
- une piste devient canonique NewTRY seulement apres provenance et validation.

Canon / piste :

- `canon` : regles, faits certifies et vocabulaire qui lient l'aval ;
- `piste` : exploration provisoire, reversible, sans autorite globale ;
- une piste ne devient canon que via une entree datee dans `DECISIONS.md`
  et, quand c'est possible, un garde-fou executable.

## 2. Trajectoire indicative

Cette trajectoire donne l'ordre logique de reconstruction. Elle est revisable :
elle guide la suite sans remplacer les decisions prises branche par branche.

- Phase 0 - Fondation / garde-fous : FAIT.
- Phase 1 - Tick sans temps (`V`, `R`, `Prints`, `CutReason`) : FAIT.
- Phase 2 - Clarification V/R : statut de `R=0`, `beta` comme question
  distincte du ratio agrege : FAIT.
- Phase 3 - Certification du domaine temporel de `GapUsBefore` : FAIT,
  prerequis a tout usage de `G`.
- Phase 4 - Silence reel simple (`GapUsBefore >= 1 ms`) : FAIT pour le canon
  `G` ; pistes `G` en PARKING.
- Phase 5 - Session / calendrier : audit approfondi FAIT ; `>=1h` invalide sur
  le raw complet ; pistes `G_close`/`G_open` + `age_from_prev_contract_end` et
  asset calendrier de marche (piste). Logique session reste un canon futur. Voir 3.8.
- Phase 6 - Objets temporels composes : PARKING, seule voie ou une vraie
  duree `D` peut redevenir legitime.
- Parking - respiration avancee `G->G`, R0/echappement, autres `.cpp`,
  debuts/fins de contrat, WVP/clusters : a ouvrir seulement sur demande
  explicite.

## 3. Etat courant

### 3.1 Noyau de confiance [CANON - amorcage]

But : poser les garde-fous avant toute analyse metier.

Inclus :

- runtime Python verrouille via `runtime/run_python.cmd` ;
- utilitaires temps dans `lib/time_utils.py` ;
- provenance des outputs dans `lib/provenance.py` ;
- scanner minimal `scripts/check_time_units.py` ;
- contrat study TICKSEQ_V4 verifie par
  `scripts/check_tickseq_v4_study_contract.py` ;
- garde-fou `DurationUS / Prints` pour les sources TICKSEQ_V4 ;
- scanner semantique `scripts/check_durationus_semantics.py` ;
- tests temps dans `tests/`.

### 3.2 Base de mesure V/R/D/G [CANON - vocabulaire]

Premier import conceptuel depuis TRY_plan, sans output ni chiffre canonique.
Detail court : `docs/BASE_MESURE.md`.

### 3.3 Source tick TICKSEQ_V4 [CANON - source importee]

Study Sierra importee comme asset source :
`studies/TRY_TickSequenceExport_v4.cpp`. Detail court :
`docs/TICKSEQ_V4.md`. CSV bruts references sans copie dans
`data/README.md`. Semantique `DurationUS` controlee par
`scripts/tickseq_v4_duration_prints_certify.py` : span natif technique,
compatible avec `Prints`, non promu en `D`.

Politique raw canon future : un fichier complet par contrat brut, non ajuste,
`Continuous Contract = None`, hors Git. La vue front sera une projection
derivee du raw via `roll_in` / `roll_out`, pas une seconde source canon.
Premiers candidats raw `NQH25-CME`, `NQM25-CME`, `NQU25-CME`, `ESH25-CME`,
`ESM25-CME` et `ESU25-CME` exportes et audites legerement, sans promotion
manifest.

### 3.4 Import depuis TRY_plan [PARKING]

TRY_plan est une source legacy, pas un depot actif pour NewTRY.

Regle d'import :

- `.cpp` Sierra : import apres verification ponctuelle ;
- scripts Python : audit ou reecriture avant usage ;
- CSV/rapports numeriques : regeneration obligatoire ;
- narratif "sub-seconde / atome / mur sub-seconde" : invalide comme conclusion ;
- hypotheses : recuperables comme questions, jamais comme resultats.

### 3.5 Tick sans temps / V-R [PISTE - parking]

Premiere piste analytique descriptive. Question limitee : verifier sur une
seule source TICKSEQ_V4 (`1T2025`) si la relation volume / range merite une
branche, sans utiliser `DurationUS`, `GapUsBefore` ni timestamps.
Le premier output est un descripteur agrege, pas un test de `beta` ni d'une
relation puissance evenement par evenement.
La masse `R=0` est suivie comme population distincte, pas comme bruit a ignorer.

Script : `scripts/tick_vr_first_pass_1t2025.py`.
Output ignore/provenance : `outputs/tick_vr_first_pass_1t2025.csv`.

Clarification `beta` evenement par evenement sur `R>0` :
`scripts/tick_vr_beta_probe_1t2025.py`.
Output ignore/provenance : `outputs/tick_vr_beta_probe_1t2025.csv`.

### 3.6 Domaine GapUsBefore [CANON - certifie]

Certification du domaine d'usage de `GapUsBefore` avant toute branche
respiration / silence. Regle provisoire : `GapUsBefore >= 1000 us` peut etre
traite comme temps ecoule ; `0..999 us` reste sub-ms censure, pas silence nul.
Toute future respiration reste limitee a une resolution plancher de 1 ms.

Script : `scripts/tickseq_v4_gap_domain_certify.py`.
Output ignore/provenance : `outputs/tickseq_v4_gap_domain_certify.csv`.

### 3.7 Silence reel simple / G intraday [CANON borne - pistes parking]

Premiere utilisation de `G` apres certification. Source unique `1T2025`.
Le sub-ms reste censure ; seuls les gaps `>= 1 ms` entrent dans les buckets de
temps reel. Pas de sequence `G->G` ni de respiration avancee dans cette passe.
Audit croise : les fermetures doivent etre separees par magnitude, pas par
`CutReason`, et la moyenne agregee ne doit pas devenir un descripteur de
respiration.

Canon acquis : `G` designe un gap intraday exploitable ; sub-ms censure ;
fermetures candidates `>=1h` exclues de `G`. Les passes descriptives `G`
ci-dessous sont en parking, a rouvrir seulement sur hypothese explicite.

Script : `scripts/gap_real_first_pass_1t2025.py`.
Output ignore/provenance : `outputs/gap_real_first_pass_1t2025.csv`.

Validation multi-sources du seuil de fermeture :
`scripts/gap_closure_threshold_multisource.py`.
Output ignore/provenance :
`outputs/gap_closure_threshold_multisource.csv`.
Resultat : bucket `10-59min` vide sur les 5 sources referencees ; `>=1h`
reste le seuil candidat de coupure avant toute future chaine `G->G`.

Passe stricte `G` intraday :
`scripts/g_intraday_first_pass_1t2025.py`.
Output ignore/provenance : `outputs/g_intraday_first_pass_1t2025.csv`.
Resultat `1T2025` : `17_368_380` `G` intraday ; `63` coupures `>=1h`
exclues de `G`.

Descripteur sequence apres `G` intraday :
`scripts/g_intraday_following_sequence_1t2025.py`.
Output ignore/provenance :
`outputs/g_intraday_following_sequence_1t2025.csv`.
Resultat `1T2025` : bucket `10-59s` descriptible (`33_481` cas) ;
bucket `1-9min` sous garde d'effectif (`16` cas).

### 3.8 Session / calendrier [PISTE - audit approfondi + asset]

Logique session / calendrier visee comme canon futur pour remplacer le seuil
provisoire `>=1h`. Ne pas confondre avec les lentilles horaire / jour semaine.

Audit lecture seule (HH:MM:SS, split DST, raw per-contrat) : la reprise
programmee tombe a `18:00 ET` (horodatage Sierra DST-aware America/New_York).
Sur le raw complet, le seuil `>=1h` s'effondre comme separateur (illiquidite
back-month massive) ; distinguer `G_close` = fermeture programmee (calendrier)
de `G_open` = silence reel en marche ouvert.

Piste (NON canon) : `age_from_prev_contract_end` (`jour 0` = premiere seance
apres le dernier jour de cotation du contrat precedent ; chaque jour sauf
samedi). Apres nettoyage `G_close`, l'age isole l'illiquidite back-month (age
negatif), le plateau liquide et le roll-out (age `~>=60`). Reproduit sur NQ et
ES (NQM25, ESM25). Pas de `roll_in/roll_out` fige : l'age reste un axe continu
de comparaison entre contrats separes.

Asset abouti (piste, versionne) : calendrier de marche pour annoter les CSV a la
carte, `2023-2025`, heure ET. Jours / feries / demi-seances + evenements high
(et une partie des medium), sourcees (BLS/BEA/Census/Fed/ISM) ou par regle,
`a_valider=false`. Genere par `scripts/build_market_calendar.py` depuis 3 seeds.
Detail, schemas et completude : `reference/MARKET_CALENDAR.md`. Historique
date : `DECISIONS.md`.

### 3.9 Branches analytiques [PARKING]

A ouvrir seulement une par une, quand l'utilisateur le demande.
Les idees non actives peuvent etre notees dans `IDEES.md` sans devenir des
branches.

Core a ne pas confondre avec les pistes : une future logique session /
calendrier peut remplacer le seuil `>=1h` comme borne de fermeture. Les
tranches horaires et jours semaine restent une lentille d'analyse tant qu'elles
ne sont pas justifiees comme canon.

Candidats issus de TRY_plan :

- etalons et distributions par tranche ;
- atypisme / absorption / deplacement ;
- swings DC et jambes composees ;
- respiration avancee G->G ;
- segmentation horaire / jours semaine comme lentille d'analyse ;
- R0 / niveaux / echappement ;
- approche bougie / WVP / clusters.

Pas de fichier de branche detaille tant qu'une branche n'est pas activee.
