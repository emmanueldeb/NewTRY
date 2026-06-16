# DECISIONS - NewTRY

Journal court des decisions qui evitent de recreer les memes erreurs.
Garder ce fichier bref.

## 2026-06-16 - Creation NewTRY minimale

- NewTRY remplace la tentative de sauvetage longue de TRY_plan.
- TRY_plan devient une source legacy/quarantaine.
- NewTRY ne reprend aucun output numerique TRY_plan directement.
- Les hypotheses TRY_plan peuvent etre reprises comme questions, pas comme
  resultats.
- Le narratif "sub-seconde / atome / mur sub-seconde" est invalide comme
  conclusion : il dependait du bug d'unite de temps pandas.
- Les analyses temporelles doivent etre regenerees sous runtime verrouille
  avant toute decision forte.
- La documentation de depart reste minimale pour eviter l'usine a gaz.
- Les imports se feront composante par composante, quand ils deviennent utiles.

## 2026-06-16 - Runtime local NewTRY

- Runtime local cree hors depot : `C:\SierraChart\tools\newtry_python`.
- Verification via `runtime/run_python.cmd` : Python 3.12.13, pandas 2.2.3,
  numpy 2.2.0, scipy 1.14.1, `pd.to_datetime(...).dtype == datetime64[ns]`.
- Le wrapper NewTRY pointe sur ce venv avant tout autre Python.
- `runtime/check_env.cmd` devient la commande commune Claude/Codex avant tout
  travail Python.

## 2026-06-16 - Premier import conceptuel

- Premier import retenu : socle de mesure `V/R/D/G`.
- Import limite a un vocabulaire de travail dans `docs/BASE_MESURE.md`.
- Aucun output, rapport ou chiffre de performance TRY_plan n'est repris.

## 2026-06-16 - Import source TICKSEQ_V4

- `studies/TRY_TickSequenceExport_v4.cpp` est importe comme source Sierra.
- La copie TRY_plan et la copie `ACS_Source` avaient le meme SHA-256 avant
  import.
- Aucun CSV, DLL, rapport ou chiffre TRY_plan n'est importe.

## 2026-06-16 - Pointeurs vers CSV bruts

- Les CSV bruts `TICKSEQ_V4` de `C:\SierraChart\Data\` sont references dans
  `data/README.md`.
- Aucun CSV n'est copie ni versionne dans NewTRY.
- `scripts/check_sources.py` verifie les chemins et en-tetes sans lire les
  fichiers complets.

## 2026-06-16 - Controle temps echantillonne

- `scripts/tickseq_v4_time_sanity_sample.py` compare `DurationUS` et
  `GapUsBefore` aux timestamps sur un echantillon borne.
- La sortie reste un PASS/FAIL technique avec compteurs, sans analyse metier.
- Chaine temps certifiee sur echantillon `50_000` lignes par source
  `TICKSEQ_V4` : 0 mismatch `DurationUS`, 0 mismatch `GapUsBefore`.
  Ce n'est pas une preuve exhaustive sur tout l'historique.

## 2026-06-16 - Inventaire complet des sources

- `scripts/tickseq_v4_source_inventory.py` lit les sources en chunks et produit
  des compteurs d'integrite, sans statistiques de marche.

## 2026-06-16 - Garde-fou DurationUS / Prints

- TRY_plan avait consigne le grain ms natif et `MaxPauseUS = 1`, mais la
  consequence `DurationUS` non independant restait insuffisamment verrouillee :
  plusieurs docs continuaient a traiter `D = DurationUS` comme duree de rafale.
- NewTRY ajoute un controle complet dedie :
  `scripts/tickseq_v4_duration_prints_certify.py`.
- `runtime/check_env.cmd` lance aussi `scripts/check_durationus_semantics.py`
  pour bloquer les futurs alias `DurationUS -> D`.
- Le scanner bloque aussi la reconstruction brute `StartDateTime` /
  `EndDateTime` en duree de sequence sans justification explicite.
- `scripts/check_tickseq_v4_study_contract.py` verifie que la study source
  reste sur le contrat attendu, notamment `MaxPauseUS = 1`.
- Regle active : tant que `DurationUS == Prints - 1` et `DurationUS < 1000 us`
  sur les sources `TICKSEQ_V4`, `DurationUS` est un span technique intra-ms,
  pas une variable temporelle independante au niveau sequence brute.

## 2026-06-16 - Premiere branche analytique

- Premiere branche ouverte : tick sans temps / V-R.
- Source unique : `TICKSEQ_V4_1T2025`.
- Variables autorisees pour cette passe : `Volume`, `Prints`, range en ticks,
  `CutReason`.
- `GapUsBefore` reste exclu tant que son domaine temporel n'est pas certifie.
- `volume_per_range_tick` est un descripteur agrege `sum(V) / sum(R)` sur
  `R>0`, pas un test de `beta` ni de la relation puissance V/R.
- `R=0` est une population a suivre separement ; toute suite V/R devra dire
  explicitement si elle l'exclut, la segmente ou l'etudie a part.

## 2026-06-16 - Clarification beta V/R

- `scripts/tick_vr_beta_probe_1t2025.py` teste `beta` comme question distincte
  du ratio agrege.
- Modele descriptif minimal : regression OLS `log(R) ~ log(V)` sur evenements
  `R>0` uniquement.
- `R=0` reste exclu de la regression et suivi comme population separee.
