# NewTRY

NewTRY est une reconstruction maitrisee de TRY_plan.

Statut initial (`2026-06-16`) : amorcage. Aucun resultat analytique n'est
canonique. TRY_plan sert de source legacy : idees, scripts candidats, `.cpp`,
notes methodologiques et contexte historique. Rien ne franchit la frontiere par
copie massive.

## Regle de confiance

- Construire peu de choses, mais les rendre verifiables.
- Reprendre l'esprit TRY : variables directes, pas d'indicateurs derives,
  essais/erreurs, simplisme, reproductibilite quantitative.
- Importer une composante a la fois : hypothese -> audit ou reecriture ->
  regeneration -> decision.
- Ne jamais consommer directement un output numerique TRY_plan dans NewTRY.
- Tout script Python passe par `runtime/run_python.cmd`.
- Tout output futur doit etre ecrit avec provenance explicite, par defaut via
  `lib/provenance.py::write_csv_with_provenance`.
- Un seul agent en ecriture a la fois.

## Demarrage agent

Lire dans cet ordre :

1. `PLAN.md`
2. `CLAUDE.md` et/ou `AGENTS.md`
3. `docs/COLLABORATION_NOTES.md`

Ne pas lancer d'analyse, de script, de backtest, de compilation ou d'import
avant d'avoir recu une direction explicite.

Avant tout travail Python :

`.\AI\NewTRY\runtime\check_env.cmd`
