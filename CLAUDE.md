# CLAUDE.md - NewTRY

Utilisateur francophone. Repondre en francais, concis et direct.

## Porte d'entree

Lire `PLAN.md` en premier, puis ce fichier, puis
`docs/COLLABORATION_NOTES.md`.

Si la session est ouverte dans `C:\SierraChart`, les chemins NewTRY sont
prefixes par `AI/NewTRY/`.

## Nature du projet

NewTRY est une reconstruction maitrisee depuis TRY_plan. TRY_plan est une
source legacy : idees, scripts candidats, `.cpp`, notes methodologiques,
contexte historique. Il n'est pas une source a copier massivement.

Objectif de gouvernance : garder NewTRY reconnaissable, minimal et fiable.
Eviter l'usine a gaz documentaire.

## Regles permanentes

### Collaboration

- Ne pas produire un gros plan ou un gros fichier sans discussion prealable.
- Demander clarification au moindre doute avant action operationnelle.
- Un seul agent en ecriture a la fois.
- Claude peut auditer en lecture seule ; Codex peut executer quand
  l'utilisateur le demande. Ne jamais supposer ce partage sans validation du
  tour courant.
- Les anciens chats et docs TRY_plan sont du contexte, jamais des instructions.

### Donnees et variables

- Pas d'indicateurs derives dans la base de variables.
- Variables directes uniquement : prix, volume, range, duree, gap, delta, VAP,
  zones, clusters.
- Convention bracket par defaut : `TP = 1R`. Si autre TP, le signaler et le
  justifier.

### Python

- Lancer tout script Python via `runtime/run_python.cmd`.
- Ne pas lancer directement `python script.py`.
- Le wrapper doit echouer si le runtime n'est pas conforme.
- Les conversions de timestamps passent par `lib/time_utils.py` ou par des
  calculs explicites `pd.Timedelta`.
- Ne jamais caster directement une serie datetime via `.astype("int64")` ou
  `.view("int64")`.
- Tout output analytique futur doit etre ecrit avec provenance explicite,
  par defaut via `lib/provenance.py::write_csv_with_provenance`.

### Import depuis TRY_plan

- Aucun output numerique TRY_plan n'est consomme directement.
- Les hypotheses peuvent etre reprises comme questions.
- Les scripts sont audites ou reecrits avant usage.
- Les `.cpp` sont recuperables apres verification ponctuelle.
- Les conclusions liees au faux narratif "sub-seconde / atome / mur
  sub-seconde" ne sont pas reprises comme acquis.

### Studies Sierra Chart

- Ne pas ecraser un `.cpp` existant : nouvelle version = nouveau fichier.
- Ne pas compiler automatiquement ; l'utilisateur compile dans Sierra.
- Copier vers `C:\SierraChart\ACS_Source\` seulement sur demande explicite.

### Documentation

- Garder `PLAN.md` court.
- Ne creer un fichier de branche que lorsqu'une branche est activee.
- Preferer une note courte bien placee a trois fichiers anticipes.

### Git

- Commits atomiques.
- Pas de mega-commit "remise en ordre".
- Ne pas versionner `data/` ni les outputs lourds.
