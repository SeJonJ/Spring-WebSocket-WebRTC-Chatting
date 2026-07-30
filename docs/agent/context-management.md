# Context Snapshot and Restore

SAGE restores durable repository context, not a host model's hidden conversation state.

## Profile Contract

```yaml
context_management:
  compaction:
    enabled: true
    preserve: [architectural_decisions, open_bugs, file_ownership, pending_verifications]
    max_snapshot_bytes: 1048576
```

When disabled, SAGE skills do not create context packets and `sage context snapshot`
rejects the request. `preserve` controls which exact phase documents are materialized
into a resume briefing; SAGE does not infer facts from free-form Markdown.

## Phase Boundary

After a phase's evidence anchor is complete:

```bash
sage context snapshot --cycle-stem <exact-stem> --phase <phase-id>
```

The packet under `.sage/context/snapshots/` binds the profile, manifest, and exact
Cycle-Stem phase documents by SHA-256. It contains paths and hashes, not document bodies.
The digest detects accidental packet corruption; it is not a remote identity signature or
server-side attestation, and it does not checkpoint every application source file.

## Resume

After opening another session or manually switching to another installed host:

```bash
sage context restore --snapshot .sage/context/snapshots/<stem>/<packet>.json
```

Restore accepts an active-host-only profile change for the manual double-host workflow.
Any other profile semantic change, manifest change, phase document change, malformed
packet, symlink, or byte-limit violation fails closed. Read the generated
`.sage/context/restored/*.md` briefing before continuing the SAGE skill.

SAGE never launches the peer host, switches phases automatically, or mutates the
profile/phase documents during restore.
