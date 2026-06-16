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
