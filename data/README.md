# data

Donnees sources externes. Ne pas versionner les gros CSV Sierra ici.

Les sources historiques peuvent rester dans `C:\SierraChart\Data\` et etre
referencees explicitement par les scripts ou rapports.

## Sources tick TICKSEQ_V4

CSV bruts Sierra references, non copies dans NewTRY :

- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_jan2025.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_fev2025.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_1T2025.csv`
- `C:\SierraChart\Data\TRY_TickSequenceExport_NQM26-CME_TICKSEQ_V4_Apr_and_Mai.csv`

Regle : ces fichiers sont des sources brutes. Toute sortie analytique NewTRY
doit etre regeneree avec le runtime verrouille et une provenance explicite.

Verification legere des chemins et en-tetes :

`runtime/run_python.cmd scripts/check_sources.py`

Verification echantillonnee des unites de temps :

`runtime/run_python.cmd scripts/tickseq_v4_time_sanity_sample.py`
