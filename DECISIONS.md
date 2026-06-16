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
