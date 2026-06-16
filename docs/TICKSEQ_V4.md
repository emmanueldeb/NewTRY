# TICKSEQ_V4 - Source tick Sierra

Ce document accompagne `studies/TRY_TickSequenceExport_v4.cpp`.

Statut NewTRY : source Sierra importee depuis TRY_plan comme asset fiable. Ce
n'est pas un resultat analytique et aucun CSV historique n'est importe avec
elle.

## Role

`TRY_TickSequenceExport_v4.cpp` exporte des sequences de prints tick depuis
Sierra Chart. Une sequence est fermee par :

- `SIDE` : changement de sens d'agression ;
- `PAUSE` : gap intra-session superieur a `MaxPauseUS` entre deux prints du
  meme sens ;
- `SESSION` : changement de trading day ;
- `EOF` : sequence encore ouverte a la fin de l'export.

Le suffixe CSV par defaut est `TICKSEQ_V4`.

Contrat source verifie par `scripts/check_tickseq_v4_study_contract.py` :
suffixe `TICKSEQ_V4`, `MaxPauseUS = 1`, horloge microseconde
`AsMicrosecondsSinceBaseDate`, colonnes `DurationUS`, `GapUsBefore` et
`CutReason`, usage attendu sur chart `Number of Trades Per Bar = 1`.

## Colonnes utiles

- `StartDateTime`, `EndDateTime` : timestamps de sequence.
- `Symbol`, `Side`, `Prints`, `Volume`.
- `DurationUS` : champ natif C++ en microsecondes, a certifier avant toute
  interpretation temporelle.
- `GapUsBefore` : silence natif C++ avant la sequence, en microsecondes.
- `PriceStart`, `PriceEnd`, `PriceMin`, `PriceMax`, `VWAP`.
- `StartBarIndex`, `EndBarIndex`, `TickSize`.
- `CutReason`.
- `VolProfile`.

## Garde-fou unite de temps

Les champs `DurationUS` et `GapUsBefore` sont produits par la study C++ et sont
deja en microsecondes. Ils ne doivent pas etre reconstruits en Python a partir
de timestamps pandas sans passer par les utilitaires temps NewTRY.

Garde-fou semantique supplementaire : au niveau sequence brute, `DurationUS`
n'est pas considere comme une variable temporelle independante tant que le
controle `scripts/tickseq_v4_duration_prints_certify.py` montre
`DurationUS == Prints - 1` et `DurationUS < 1000 us` sur les sources courantes.
Dans ce cas, il s'agit d'un span technique intra-ms lie au nombre de prints ;
la vraie temporalite exploitable reste `GapUsBefore` ou des durees d'objets
composes reconstruits explicitement.

Les futures analyses Python doivent donc :

- lire explicitement `DurationUS` / `GapUsBefore` quand ces colonnes suffisent ;
- utiliser `lib/time_utils.py` pour toute conversion timestamp -> duree ;
- produire des outputs via `lib/provenance.py`.

## Non-import

Ne sont pas importes avec cette study :

- DLL Sierra compilees ;
- CSV historiques `TICKSEQ_V4` ;
- rapports ou conclusions TRY_plan ;
- chiffres de volume, nombre de sequences ou performance.
