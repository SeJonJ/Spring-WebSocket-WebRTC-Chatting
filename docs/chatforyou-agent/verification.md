# ChatForYou Verification Extension

`scripts/verify-changes.sh` is a project-local deterministic gate and must survive SAGE upgrades unchanged. It collects tracked and untracked changes, classifies component and risk impact, runs per-file checks, supports URL-prefix and base selection, and preserves the existing degraded/block exit behavior.

Required regression commands:

```bash
bash scripts/test-verify-changes.sh
bash scripts/test-verify-committed-tree.sh
bash scripts/test-verify-doc-mapping.sh
```

For L2/L3 work, run the project gate at the declared level and record the exact result in Phase 03 and Phase 04.
