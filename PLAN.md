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

## 2. Etat courant

### 2.1 Noyau de confiance [ACTIF - amorcage]

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

### 2.2 Base de mesure V/R/D/G [SOCLE - pose]

Premier import conceptuel depuis TRY_plan, sans output ni chiffre canonique.
Detail court : `docs/BASE_MESURE.md`.

### 2.3 Source tick TICKSEQ_V4 [SOCLE - source importee]

Study Sierra importee comme asset source :
`studies/TRY_TickSequenceExport_v4.cpp`. Detail court :
`docs/TICKSEQ_V4.md`. CSV bruts references sans copie dans
`data/README.md`. Semantique `DurationUS` controlee par
`scripts/tickseq_v4_duration_prints_certify.py`.

### 2.4 Import depuis TRY_plan [PARKING]

TRY_plan est une source legacy, pas un depot actif pour NewTRY.

Regle d'import :

- `.cpp` Sierra : import apres verification ponctuelle ;
- scripts Python : audit ou reecriture avant usage ;
- CSV/rapports numeriques : regeneration obligatoire ;
- narratif "sub-seconde / atome / mur sub-seconde" : invalide comme conclusion ;
- hypotheses : recuperables comme questions, jamais comme resultats.

### 2.5 Branches analytiques [PARKING]

A ouvrir seulement une par une, quand l'utilisateur le demande.

Candidats issus de TRY_plan :

- socle tick V/R/D/G ;
- etalons et distributions par tranche ;
- atypisme / absorption / deplacement ;
- swings DC et jambes composees ;
- respiration G->G ;
- R0 / niveaux / echappement ;
- approche bougie / WVP / clusters.

Pas de fichier de branche detaille tant qu'une branche n'est pas activee.
