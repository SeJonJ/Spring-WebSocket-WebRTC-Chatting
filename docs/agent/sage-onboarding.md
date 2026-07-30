# SAGE Team Onboarding

Host: `claude`  
Selected Codex CORE skill scope: `project-local`

Claude CORE skills are repository-local under `.claude/skills` and can be committed with the project.
A teammate still installs the SAGE CLI/runtime separately to run `sage`, `sage-hook`, hooks, and validation.

Run `sage-init` only for the first shared+local bootstrap. When the shared profile is already bootstrapped, each teammate runs `sage-init-local` to create only `sage/project-profile.local.yaml`.

Do not keep duplicate global, `.codex/skills`, and `.agents/skills` copies of the same `$sage-*` CORE skill. Run `sage doctor` after installation; the manifest receipt records intent, while host precedence is treated as ambiguous when duplicate copies exist.
