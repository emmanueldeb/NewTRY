# IDEES - NewTRY

Parking d'idees non actives.

Une idee notee ici n'est pas une branche ouverte, ni une decision, ni une
conclusion validee. Elle sert seulement a ne pas perdre une piste pendant la
reconstruction controlee.

Regles :

- rester court ;
- ne pas importer de chiffres TRY_plan comme resultats ;
- ne pas transformer une intuition en tache active ;
- ouvrir une branche seulement via `PLAN.md` quand l'utilisateur le demande.

## G intraday longs

Question possible : les grands gaps intraday ont-ils une signature sur la
sequence qui suit ?

Vocabulaire provisoire :

- `G` designe un gap intraday exploitable ;
- une coupure de session, fermeture, overnight ou week-end n'est pas un `G` ;
- un gap `>=1h` est une coupure candidate selon le seuil valide multi-sources,
  donc exclu de cette piste sauf logique calendrier/session ulterieure.

Cadre provisoire :

- utiliser seulement le domaine certifie `GapUsBefore >= 1000 us` ;
- garder le sub-ms censure, jamais silence nul ;
- ne pas utiliser `CutReason` comme detecteur de fermeture ;
- rester descriptif : pas de signal metier, pas de trading, pas de `G->G` par
  defaut.
