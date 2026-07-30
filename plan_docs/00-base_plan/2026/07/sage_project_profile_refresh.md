# SAGE Project Profile Refresh

Cycle-Stem: sage_project_profile_refresh
Risk Level: L2

## Context

ChatForYou v2 adopts the SAGE v0.9.72 profile split between shared project policy and local machine capability. The shared profile should describe the project default, while private paths and per-user runtime availability stay in `sage/project-profile.local.yaml`.

The pin was originally authored against `0.9.70`, then moved to `0.9.71` for the project-authored asset stamp fix (engine-owned extractor test paths no longer written into project asset `test` fields). `0.9.72` follows the cycle-stem declaration fix: on a long-lived branch the gate infers the cycle stem from the branch leaf, so a complete `00~03` set still read as missing and the block text pointed at writing documents that already existed. The gate now names the inferred leaf, offers `SAGE_CYCLE_STEM`, and audits declared stems to `.sage/override.jsonl`.

Leaving the pin behind the installed toolchain makes the shared profile disagree with the installed, generated, and runtime versions, so `sage validate` reports a three-line version WARN and advises downgrading.

## Scope

- Set the exact required SAGE version to `0.9.72`.
- Keep both `codex` and `claude` as supported installed hosts.
- Set the shared default active host to `claude`.
- Set cross-model policy to `recommended`.
- Enable this machine's local cross-model capability.
- Upgrade acceptance report policy to L2 advisory and L3 enforce with explicit waiver support.
- Enable context compaction snapshots.

## Risk

L2 governance/configuration change. The change affects SAGE gate behavior and review routing, but does not modify product runtime code.

## Out Of Scope

- ChatForYou backend/frontend source changes.
- SAGE upstream runtime code changes.
- Commit creation.
