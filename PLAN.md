# PLAN - NewTRY

> Porte d'entree minimale. Ce fichier doit rester court. Il sert a savoir ou
> en est NewTRY sans reconstruire toute l'histoire de TRY_plan.

## 0. Regle de lecture

Au demarrage d'une session, lire :

- `PLAN.md`
- `CLAUDE.md` ou `AGENTS.md`
- `docs/COLLABORATION_NOTES.md`

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

## 2. Trajectoire indicative

Cette trajectoire donne l'ordre logique de reconstruction. Elle est revisable :
elle guide la suite sans remplacer les decisions prises branche par branche.

- Phase 0 - Fondation / garde-fous : FAIT.
- Phase 1 - Tick sans temps (`V`, `R`, `Prints`, `CutReason`) : FAIT.
- Phase 2 - Clarification V/R : statut de `R=0`, `beta` comme question
  distincte du ratio agrege : EN COURS.
- Phase 3 - Certification du domaine temporel de `GapUsBefore` : A FAIRE,
  prerequis a tout usage de `G`.
- Phase 4 - Objets temporels composes : PARKING, seule voie ou une vraie
  duree `D` peut redevenir legitime.
- Parking - respiration `G->G`, R0/echappement, autres `.cpp`, WVP/clusters :
  a ouvrir seulement sur demande explicite.

## 3. Etat courant

### 3.1 Noyau de confiance [ACTIF - amorcage]

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

### 3.2 Base de mesure V/R/D/G [SOCLE - pose]

Premier import conceptuel depuis TRY_plan, sans output ni chiffre canonique.
Detail court : `docs/BASE_MESURE.md`.

### 3.3 Source tick TICKSEQ_V4 [SOCLE - source importee]

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

### 3.5 Tick sans temps / V-R [ACTIF]

Premiere branche analytique canonique. Question limitee : verifier sur une
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

### 3.6 Branches analytiques [PARKING]

A ouvrir seulement une par une, quand l'utilisateur le demande.

Candidats issus de TRY_plan :

- etalons et distributions par tranche ;
- atypisme / absorption / deplacement ;
- swings DC et jambes composees ;
- respiration G->G ;
- R0 / niveaux / echappement ;
- approche bougie / WVP / clusters.

Pas de fichier de branche detaille tant qu'une branche n'est pas activee.
