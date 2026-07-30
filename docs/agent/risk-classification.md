# Risk classification

Changes are classified into L0–L3 from `profile.risk`, not from hardcoded
domain knowledge (independence: the engine carries no domain values).

- **L0** — docs / plan files (`profile.risk.l0_pass_globs`). Pass immediately unless
  the path also matches a bound `profile.risk.l0_exclude_globs` entry.
- **L1** — low blast radius, e.g. UI/markup (`profile.risk.l1_path_globs`).
- **L2** — source/config (`profile.risk.l2_path_globs`).
- **L3** — high-risk domains (`profile.risk.l3_filename_globs`), or content
  matching `profile.risk.l3_content_keywords`.

Escalation: L1/L2 content matching `l3_content_keywords` escalates to L3; L1
content matching `l2_content_keywords` escalates to L2. The effective level is
`max(detected, user-declared)`.

`l0_exclude_globs` is not a standalone risk tier. Every entry must exactly match an
L1/L2/L3 path glob; otherwise profile validation fails and the runtime core degrades
the orphan match to L3. `risk.domains[].path_globs` are automatically materialized
into this exclusion set, so a broad asset L0 rule cannot mask a specific higher-risk
domain path. Profiles without exclusions preserve the historical L0-first behavior.

A "do-not-edit" mirror/sync path can be declared via
`profile.risk.desktop_block_glob` (with `desktop_block_hint` for the message);
direct edits there are blocked.

This policy is implemented by `pre-implementation-gate` (canonical core, pure +
profile-driven).
