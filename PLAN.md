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
- Phase 5 - Session / calendrier : CANON FUTUR, remplacement possible du seuil
  provisoire `>=1h`, a traiter separement des lentilles d'analyse horaire/jour.
- Phase 6 - Objets temporels composes : PARKING, seule voie ou une vraie
  duree `D` peut redevenir legitime.
- Parking - respiration avancee `G->G`, R0/echappement, autres `.cpp`,
  WVP/clusters : a ouvrir seulement sur demande explicite.

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
`scripts/tickseq_v4_duration_prints_certify.py`.

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

### 3.8 Session / calendrier [CANON FUTUR - audit initial]

But : preparer un remplacement eventuel du seuil provisoire `>=1h` par une
logique session / calendrier explicite. Ne pas confondre avec les lentilles
d'analyse horaire / jour semaine.

Script : `scripts/closure_candidate_calendar_audit.py`.
Output ignore/provenance : `outputs/closure_candidate_calendar_audit.csv`.
Resultat : les coupures candidates `>=1h` sont auditables par calendrier ;
sur fichiers references, beaucoup sont des coupures de meme date avec reprise
a `18:00`, et pas seulement des overnight / week-end.

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
