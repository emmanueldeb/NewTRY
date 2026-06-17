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
- Les coefficients `beta` / `R2` sont masques si `beta_n < 50`, pour eviter
  qu'un petit groupe ressemble a un resultat exploitable.

## 2026-06-16 - Domaine GapUsBefore

- Phase 3 ouverte : certifier le domaine d'usage de `GapUsBefore` avant toute
  analyse de respiration.
- `scripts/tickseq_v4_gap_domain_certify.py` classe `GapUsBefore` sans
  analyser la respiration : `-1`, `0`, `1..999 us`, `>=1000 us`.
- Regle provisoire : `GapUsBefore >= 1000 us` peut etre traite comme temps
  ecoule ; `0..999 us` reste technique/sub-ms.

## 2026-06-17 - Domaine GapUsBefore valide

- Certification reproduite : `54_227_841` lignes, `GapUsBefore = -1`
  exactement une fois par source, aucun missing/invalide/zero.
- Domaine sub-ms `1..999 us` : `5_708_692` lignes (`10,53 %`), a traiter
  comme censure/petit-inconnu, jamais comme silence nul.
- Domaine temps ecoule `>=1000 us` : `48_519_144` lignes (`89,47 %`).
- Toute future respiration est limitee a une resolution plancher de 1 ms.
- Limite connue : un seuil pur a `1000 us` suppose qu'un compteur synthetique
  intra-ms ne deborde pas au-dela de `999 us`.

## 2026-06-17 - Premiere passe silence reel

- Premiere utilisation de `G` apres certification : `GapUsBefore >= 1 ms`
  seulement, sur source unique `TICKSEQ_V4_1T2025`.
- Le sub-ms `0..999 us` reste censure/petit-inconnu et n'est jamais traite
  comme silence nul.
- `scripts/gap_real_first_pass_1t2025.py` produit des buckets descriptifs de
  gaps reels ; ce n'est pas une analyse de respiration `G->G`.

## 2026-06-17 - Garde-fous silence reel

- Audit croise reproduit la passe `gap_real_first_pass_1t2025.py` au chiffre
  pres.
- `CutReason` ne capture pas les fermetures : `GapUsBefore` decrit le silence
  avant la sequence, tandis que `CutReason` decrit comment la sequence se
  termine.
- Les fermetures doivent donc etre separees par magnitude, pas par `CutReason`.
- Sur `1T2025`, le bucket `10-59min` est vide, `1-9min` plafonne a environ
  `89 s`, et `>=1h` contient `63` gaps ; `>=1h` est un seuil candidat de
  fermeture pour cette source, a revalider avant generalisation.
- `real_gap_mean_ms` reste une mesure descriptive mais ne doit pas servir de
  signal de respiration : les buckets, medianes et effectifs sont prioritaires.

## 2026-06-17 - Seuil fermeture multi-sources

- `scripts/gap_closure_threshold_multisource.py` lit uniquement
  `GapUsBefore` sur les 5 sources `TICKSEQ_V4` referencees.
- Controle input : `54_227_841` lignes lues sur fichiers references, 0
  missing, 0 valeur negative invalide, `GapUsBefore = -1` une fois par source.
- Le bucket `10-59min` est vide sur chaque source.
- Le bucket `1-9min` reste rare (`45` gaps sur les fichiers references) et
  plafonne a `120,054 s`.
- Le bucket `>=1h` est present sur chaque source (`36`, `18`, `22`, `63`,
  `43` gaps ; `182` au total fichier, non deduplique).
- Decision provisoire : avant toute future chaine `G->G`, un gap `>=1h` doit
  etre traite comme coupure de fermeture candidate et ne doit pas etre traverse
  comme respiration intraday, sauf remplacement explicite par une logique
  calendrier/session ulterieure.
- Les CSV references peuvent se chevaucher ; la ligne aggregate sert au
  controle technique, pas a une frequence historique dedupliquee.

## 2026-06-17 - Vocabulaire G intraday

- Dans NewTRY, `G` designe un gap intraday exploitable.
- Une fermeture, un overnight, un week-end ou une coupure de session n'est pas
  un `G` ; c'est une coupure a exclure ou a separer.
- Regle courante issue de la validation multi-sources : `1000 us <=
  GapUsBefore < 1h` peut entrer dans `G` ; `GapUsBefore >= 1h` reste une
  coupure candidate, sauf future logique calendrier/session plus precise.

## 2026-06-17 - Premiere passe G intraday stricte

- `scripts/g_intraday_first_pass_1t2025.py` lit uniquement `GapUsBefore` sur
  `TICKSEQ_V4_1T2025`.
- Definition appliquee : `G = 1000 us <= GapUsBefore < 1h`.
- Controle : `19_363_849` lignes lues, 0 invalides.
- Exclusions : `1_995_405` sub-ms censures, `63` coupures candidates `>=1h`.
- `G` intraday retenus : `17_368_380` ; max `G` intraday `89,355 s`.
- Grands `G` intraday : `33_481` dans `10-59s`, `16` dans `1-9min`,
  `0` dans `10-59min`.
- Cette passe reste descriptive : pas de `G->G`, pas de `CutReason`, pas de
  signal metier.

## 2026-06-17 - Sequence apres G intraday

- Premiere question ouverte sur les grands `G` : decrire la sequence qui suit
  le gap intraday, sans chaine `G->G`.
- `scripts/g_intraday_following_sequence_1t2025.py` lit `GapUsBefore`,
  `Prints`, `Volume`, `PriceMin`, `PriceMax`, `TickSize` sur `1T2025`.
- `CutReason` n'est pas lu dans cette premiere passe, pour eviter toute
  confusion avec les fermetures.
- Les coupures `>=1h` et le sub-ms restent exclus du champ `G`.
- Garde d'effectif : groupes avec `sequence_count < 50` marques
  `n_below_min`, a ne pas interpreter.
- Sur `1T2025`, `10-59s` contient `33_481` sequences apres `G` intraday :
  `Volume/sequence = 1,764`, `Prints/sequence = 1,680`,
  `R/sequence = 0,259`, `R=0 = 83,96 %`.
- `1-9min` contient seulement `16` sequences et reste non interpretable ;
  `10-59min` contient `0` sequence.
- Ces valeurs decrivent la sequence qui suit le `G`, pas une relation
  temporelle `G->G`.

## 2026-06-17 - Gouvernance canon / piste

- Le clivage NewTRY retenu est `canon` / `piste`, pas `safe` / `recherche`.
- `canon` : regles, faits certifies et vocabulaire qui lient l'aval.
- `piste` : exploration provisoire, reversible, sans autorite globale.
- Une piste ne devient canon que via une entree datee dans `DECISIONS.md` et,
  quand c'est possible, un garde-fou executable.
- `IDEES.md` reste un parking sans autorite ; une idee peut sortir vers une
  piste, jamais directement vers le canon.
- La logique session / calendrier est un canon futur possible ; les tranches
  horaires et jours semaine restent une lentille d'analyse tant qu'elles ne
  sont pas justifiees comme canon.

## 2026-06-17 - Audit calendrier des coupures candidates

- `scripts/closure_candidate_calendar_audit.py` lit uniquement
  `StartDateTime`, `EndDateTime`, `GapUsBefore` pour auditer les coupures
  candidates `GapUsBefore >= 1h`.
- Ce script ne definit pas encore un calendrier de session et ne fait aucune
  analyse par tranche horaire / jour semaine.
- Controle input : `54_227_841` lignes lues sur fichiers references,
  `182` coupures candidates au total fichier non deduplique, 0 parse error de
  borne de coupure.
- Les coupures candidates commencent toutes a l'heure `18` dans les sources
  auditees ; les bornes precedentes sont entre heures `9` et `16`.
- Sur l'agregat fichier non deduplique : `145` coupures de meme date
  calendrier, `37` avec changement de weekday, `35` traversant un week-end.
- Conclusion de canon provisoire : le seuil `>=1h` reste une borne de coupure
  candidate, mais il ne doit pas etre assimile uniquement a overnight /
  week-end ; une future logique session / calendrier devra distinguer ces cas.
