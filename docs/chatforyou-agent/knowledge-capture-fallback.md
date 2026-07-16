# ChatForYou Knowledge Capture Fallback

Use this project-local fallback only when a required Obsidian knowledge write-back
cannot reach or write the configured vault path. An unavailable MCP alone is not a
failure when the local `knowledge_capture.vault_path` remains writable.

## Required Behavior

1. Read the vault root `AGENT_GUIDE.md` from the configured path before authoring when
   it is accessible. If it is not accessible, use the last confirmed ChatForYou vault
   conventions from `.local/local_agent_guide.md` and mark that limitation.
2. Finish the document as a wiki-ready draft. Do not leave a short placeholder or only
   a command transcript.
3. Save it under `.sage/pending-wiki/{YYYY-MM-DD}-{cycle-stem}.md`. Add a numeric suffix
   instead of overwriting an existing draft.
4. Include the intended prefix, title, tags, target wiki path, creation time, failure
   reason, and `status: pending` in the draft frontmatter.
5. Keep the vault's required frontmatter, Takeaway callout, deep-note structure, and
   `[[wikilink]]` conventions in the body so later migration is mechanical.
6. Report `Knowledge: DEGRADED/PENDING` with the saved path in Phase 06 and the final
   response. A local draft is not successful vault capture.
7. Do not update `wiki/index.md` or `wiki/log.md` outside the vault while it is
   unavailable, and do not invent substitute copies elsewhere in the repository.

## Draft Envelope

```yaml
---
status: pending
target_prefix: TECH
target_title: Example title
target_note: wiki/TECH - Example title.md
tags: [tech, chatforyou]
created_at: 2026-07-16T00:00:00+09:00
failure_reason: vault path unavailable
---
```

Replace the example values with the intended note metadata. Never include secret,
token, private-key, certificate, or credential values in a pending draft.

## Later Migration

When the vault is writable again, read the pending draft and re-run the normal
`sage knowledge write-back` flow. Apply the current vault `AGENT_GUIDE.md` at that time,
remove fallback-only metadata such as `status` and `failure_reason`, then update the
vault's configured index and log through the normal write-back path. Delete the local
pending file only after the vault note and required index/log updates are confirmed.

There is no automatic flush or deletion. Migration remains an explicit user-visible
operation.
