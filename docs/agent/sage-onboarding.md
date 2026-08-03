# SAGE Team Onboarding

Host: `codex`
Selected Codex CORE skill scope: `global`

Global CORE skills live under the effective `$CODEX_HOME/skills` and are not carried by the repository.
The SAGE CLI/runtime and CORE skill install are per-user: each teammate installs the CLI, then runs `sage install --host codex --skill-scope global --dest <repo>`.

Run `sage-init` only for the first shared+local bootstrap. When the shared profile is already bootstrapped, each teammate runs `sage-init-local` to create only `sage/project-profile.local.yaml`.

Do not keep duplicate global, `.codex/skills`, and `.agents/skills` copies of the same `$sage-*` CORE skill. Run `sage doctor` after installation; the manifest receipt records intent, while host precedence is treated as ambiguous when duplicate copies exist.
