# Risk classification

Changes are classified into L0–L3 from `profile.risk`, not from hardcoded
domain knowledge (independence: the engine carries no domain values).

- **L0** — docs / plan files (`profile.risk.l0_pass_globs`). Pass immediately.
- **L1** — low blast radius, e.g. UI/markup (`profile.risk.l1_path_globs`).
- **L2** — source/config (`profile.risk.l2_path_globs`).
- **L3** — high-risk domains (`profile.risk.l3_filename_globs`), or content
  matching `profile.risk.l3_content_keywords`.

Escalation: L1/L2 content matching `l3_content_keywords` escalates to L3; L1
content matching `l2_content_keywords` escalates to L2. The effective level is
`max(detected, user-declared)`.

A "do-not-edit" mirror/sync path can be declared via
`profile.risk.desktop_block_glob` (with `desktop_block_hint` for the message);
direct edits there are blocked.

This policy is implemented by `pre-implementation-gate` (canonical core, pure +
profile-driven).
