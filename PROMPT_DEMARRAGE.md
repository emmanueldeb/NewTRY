# PROMPT_DEMARRAGE NewTRY

Tu reprends le projet `C:\SierraChart\AI\NewTRY`.

La session peut etre ouverte dans `C:\SierraChart` pour acceder aussi a
`ACS_Source/` et `Data/`. Dans ce cas, prefixer les chemins NewTRY par
`AI/NewTRY/`.

Lire dans l'ordre, sans lancer d'analyse ni de script :

1. `AI/NewTRY/PLAN.md`
2. `AI/NewTRY/CLAUDE.md`
3. `AI/NewTRY/docs/COLLABORATION_NOTES.md`

Premiere reponse attendue :

- rappeler que NewTRY est en amorcage ;
- resumer seulement les branches `ACTIF` du `PLAN.md` ;
- demander la direction de l'utilisateur.

Ne pas importer TRY_plan, ne pas produire de grand plan documentaire, ne pas
lancer de regeneration sans demande explicite.

Avant tout travail Python ulterieur, verifier l'environnement avec :

`.\AI\NewTRY\runtime\check_env.cmd`
