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

## Colonnes utiles

- `StartDateTime`, `EndDateTime` : timestamps de sequence.
- `Symbol`, `Side`, `Prints`, `Volume`.
- `DurationUS` : duree native C++ en microsecondes.
- `GapUsBefore` : silence natif C++ avant la sequence, en microsecondes.
- `PriceStart`, `PriceEnd`, `PriceMin`, `PriceMax`, `VWAP`.
- `StartBarIndex`, `EndBarIndex`, `TickSize`.
- `CutReason`.
- `VolProfile`.

## Garde-fou unite de temps

Les champs `DurationUS` et `GapUsBefore` sont produits par la study C++ et sont
deja en microsecondes. Ils ne doivent pas etre reconstruits en Python a partir
de timestamps pandas sans passer par les utilitaires temps NewTRY.

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
