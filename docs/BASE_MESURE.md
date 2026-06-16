# BASE_MESURE - Socle V/R/D/G

Ce document pose le premier import conceptuel depuis TRY_plan. Il ne reprend
aucun output numerique et ne rend aucune conclusion TRY_plan canonique.

## Objet

NewTRY etudie d'abord les mouvements avec des variables directes :

- `V` : volume en contrats ;
- `R` : range en ticks ;
- `D` : duree, uniquement quand l'objet mesure possede une vraie etendue
  temporelle ;
- `G` : gap / silence avant l'evenement.

Ces variables forment la base de mesure. Les indicateurs derives restent hors
base de variables.

Au niveau brut `TICKSEQ_V4`, `DurationUS` n'est pas promu automatiquement en
`D`. Sur les sources actuelles, il doit d'abord passer le garde-fou dedie :
`DurationUS == Prints - 1` et `DurationUS < 1000 us` signifient que le champ est
un span technique intra-ms de sequencing, pas une duree de marche independante.

## Cadre herite comme hypothese de travail

- La relation `V/R` est une candidate structurante pour qualifier la facon dont
  le volume produit ou non du deplacement.
- `G` est traite comme une dimension propre : silence / respiration locale,
  a ne pas confondre avec `V`, `R` ou `D`.
- Les objets composes (swings, jambes, zones, respiration) ne sont pas des
  resultats acquis. Ils seront reintroduits un par un si utiles.

## Ce qui n'est pas importe

- Aucun CSV TRY_plan.
- Aucun rapport TRY_plan.
- Aucun chiffre de performance TRY_plan.
- Aucune conclusion temporelle issue du narratif "sub-seconde / atome / mur
  sub-seconde".
- Aucune conclusion fondee sur `DurationUS` comme duree independante au niveau
  sequence brute.

## Regle d'usage

Une future branche peut s'appuyer sur ce vocabulaire, mais toute conclusion
numerique devra etre regeneree dans NewTRY avec le runtime verrouille et une
provenance explicite.
