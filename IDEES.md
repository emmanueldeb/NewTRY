# IDEES - NewTRY

Parking d'idees non actives.

Une idee notee ici n'est pas une branche ouverte, ni une decision, ni une
conclusion validee. Elle sert seulement a ne pas perdre une piste pendant la
reconstruction controlee.

Regles :

- aucune autorite : ni fait, ni conclusion, ni canon ;
- rester court ;
- ne pas importer de chiffres TRY_plan comme resultats ;
- ne pas transformer une intuition en tache active ;
- une idee peut sortir vers une piste, jamais directement vers le canon ;
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

## Segmentation horaire / jours semaine

Question possible : relire les futures pistes par tranche horaire et jour de
semaine pour eviter de melanger des regimes de marche differents.

Cadre provisoire :

- ne pas confondre cette lentille d'analyse avec la definition canonique de
  session / fermeture ;
- la logique calendrier/session qui remplacerait un jour le seuil `>=1h`
  releve du canon futur ;
- les tranches horaires et jours semaine comme lecture analytique restent une
  piste tant qu'elles ne sont pas justifiees.

## Debuts / fins de contrat

Question possible : les phases hors fenetre front ont-elles une signature
propre de liquidite, volume, range ou gap ?

Cadre provisoire :

- utiliser le raw per-contrat complet ;
- ne pas confondre avec la vue front derivee ;
- comparer les contrats par age relatif au roll ou a l'echeance ;
- rester descriptif avant toute conclusion.

## Inventaire NewTRY

Question possible : faire le point sur ce dont NewTRY dispose deja avant
d'ouvrir une nouvelle phase.

Cadre provisoire :

- inventaire des sources raw, scripts, garde-fous, outputs regenerables,
  decisions et pistes en parking ;
- distinguer clairement `canon`, `piste`, `parking`, `legacy` et donnees hors
  Git ;
- ne pas transformer l'inventaire en refonte documentaire ;
- objectif : rendre le projet redemarrable et lisible avant de choisir la suite.
