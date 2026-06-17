# data

Donnees sources externes. Ne pas versionner les gros CSV Sierra ici.

Les sources historiques peuvent rester dans `C:\SierraChart\Data\` et etre
referencees explicitement par les scripts ou rapports.

## Sources tick TICKSEQ_V4 legacy audit

CSV Sierra references pendant la reconstruction. Ils restent utiles pour audit
historique, mais ne sont pas la source raw canon future :

- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_jan2025.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_fev2025.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_Apr_and_Mai.csv`

Regle : toute sortie analytique NewTRY doit etre regeneree avec le runtime
verrouille et une provenance explicite.

Verification legere des chemins et en-tetes :

`runtime/run_python.cmd scripts/check_sources.py`

Verification echantillonnee des unites de temps :

`runtime/run_python.cmd scripts/tickseq_v4_time_sanity_sample.py`

Inventaire complet d'integrite source (lecture chunked) :

`runtime/run_python.cmd scripts/tickseq_v4_source_inventory.py`

## Source raw canon future

La source raw canon NewTRY sera organisee en un fichier CSV complet par contrat
brut :

- contrat reel unique par fichier, par exemple `NQU26-CME` ;
- `Continuous Contract = None` dans Sierra ;
- pas de back-adjust Sierra comme source canon ;
- fichier complet du contrat, debuts/fins inclus ;
- CSV hors Git.

Le manifest versionne fera foi. Une ligne par contrat :

- `contract`
- `status` : `settled` ou `live`
- `path`
- `ts_min`, `ts_max`
- `rows`
- `sha256`
- `size_bytes`
- `export_params` : study version, suffixe, `MaxPauseUS`, chart settings,
  fuseau, `Continuous Contract = None`
- `schema_ok`
- `roll_in`, `roll_out` : fenetre front derivee

La vue front n'est pas une deuxieme source canon. Elle est une projection
regenerable :

`raw per-contrat + roll_in/roll_out -> vue front`

Les analyses futures devront lire la source raw canon ou une vue derivee du
manifest, sauf audit explicite des fichiers legacy.
