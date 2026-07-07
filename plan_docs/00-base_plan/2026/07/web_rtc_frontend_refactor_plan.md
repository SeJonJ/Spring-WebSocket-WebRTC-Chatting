# [Base Plan] WebRTC Frontend Refactor

## 0. Prior Knowledge (Vault Scan)
| Type | Note | Key Takeaway |
|------|------|--------------|
| BUG | `BUG - kurento-service.js Peer 에러 Fallback 누락` | `handlePeerSetupError`, `clearFallbackState`, `reconnectMetaCache`, `showParticipantPlaceholder` ordering is fragile and must not be moved in the first refactor pass. |
| BUG | `BUG - WebRTC U001 경쟁조건 + leaveRoom 루프 패턴` | `wsMessageHandlers.error` must terminate K008/U001 locally and must not fall through to HTTP auth handling. |
| TECH | `TECH - WebRTC 통화 중 자동 재연결 (WebSocket 1006)` | Reconnect success is `existingParticipants`, not `onopen`; idle-based WebSocket close must not be reintroduced. |
| POSTMORTEM | `POSTMORTEM - 260619 coturn-kurento 배포 이슈` | TURN credential fallback and `buildIceServers()` null filtering must be preserved exactly. |

## 1. Summary (Goal & Scope)

Issue #138 requests frontend WebRTC cleanup because `nodejs-frontend/static/js/rtc/kurento-service.js` is over 4,000 lines and mixes signaling, peer lifecycle, reconnect, screen sharing, subtitle UI, and toast helpers.

This cycle is an L3 behavior-preserving refactor. Issue #138 is completed in one development pass, while intentionally avoiding WebSocket, Kurento message contract, ICE/SDP, and reconnect state-machine behavior changes.

In scope for this issue:
- Split screen-share stream/track/quality/UI/toast responsibility out of `kurento-service.js`.
- Split subtitle UI responsibility out of `kurento-service.js`.
- Keep classic browser `<script>` loading.
- Keep existing global function names used by `initScript()`, `initEvent()`, WebSocket handlers, `speechSubtitleManager`, and inline UI handlers.
- Update `kurentoroom.html` script order so separated files are loaded before `connectWebSocket()` can call `initScript()` / `initEvent()`.
- Record validation evidence in Phase 03.

Out of scope:
- ES module `import/export`.
- Backend changes.
- WebSocket message `id` / payload changes.
- `wsMessageHandlers`, `connectWebSocket`, `scheduleReconnect`, `doReconnect`, `receiveVideo`, `receiveVideoResponse`, `handlePeerSetupError`, `buildIceServers` relocation.
- Electron source direct edits under `chatforyou-desktop/src`.

## 2. Impact Analysis (Critical)

- [Backend]: No planned code changes. Backend signaling contract is intentionally frozen.
- [Frontend]: `kurento-service.js`, new `nodejs-frontend/static/js/rtc/*.js` files, and `kurentoroom.html` script order.
- [Desktop]: Two-part impact, both mandatory:
  1. `chatforyou-desktop/src` must not be edited directly; run `npm run sync` in `chatforyou-desktop` after frontend changes.
  2. `chatforyou-desktop/build/` and `chatforyou-desktop/build-scripts/` (excluding `src`, which only mirrors `nodejs-frontend`) must be checked for any assumption tied to the current single-file `kurento-service.js` — hardcoded filenames, file counts, or path lists that a file split could break. This check is required whenever frontend files under `nodejs-frontend` are added, split, renamed, or removed, not only for this issue.
- [QA]: Frontend syntax and deterministic L3 verification. Backend test code is not expected unless the contract changes, which is out of scope.

## 3. Technology & Risks

Risk Level: L3.

Reason:
- The touched source is WebRTC/Kurento frontend code and desktop-synced assets.
- Even behavior-preserving movement can break global binding availability, script load order, or screen-share media track lifecycle.

Primary risks:
- `initEvent()` calls `screenShare()` before the separated file is loaded.
- `initScript()` calls `initSubtitleUI()` before the separated file is loaded.
- `speechSubtitleManager` calls global `showToast()` at runtime.
- Screen share `stopScreenShare()` must keep `AudioContext`, `replaceTrack`, `shareView`, and monitor interval cleanup order.
- Duplicate `hideScreenShareControls()` behavior must preserve the later override cleanup that removes shortcuts, timer, and overlays.
- `chatforyou-desktop` packaging or sync could silently drop or mis-convert the two newly split files if any part of `build/` or `build-scripts/` assumes a fixed file list instead of scanning the source tree.

Risk controls:
- Move screen-share and subtitle blocks mechanically, then prove the moved files reconstruct the original `kurento-service.js` content.
- Load the extracted files immediately after `kurento-service.js` and before data channel / recording modules.
- Keep top-level function declarations in classic scripts instead of module exports.
- Do not rename externally referenced functions.
- Keep WebSocket, reconnect, TURN, peer setup, participant lifecycle, and send helpers in `kurento-service.js`.
- Before implementation, inspect `chatforyou-desktop/build-scripts/**` (`build.js`, `sync-frontend.js`, `lib/sync-engine.js`, `lib/convert_path.js`, `convert_path.json`) and `package.json`'s `electron-builder.files` for any filename- or count-based logic that a 1-file-to-3-file split would break. Record the finding and, after implementation, re-run `npm run sync` and confirm the two new files land under `chatforyou-desktop/src/static/js/rtc/` as Phase 03 evidence.

## 4. Final Conclusion & UX Guide

Proceed with the full #138 refactor in one pass:
1. Extract `kurento-service.js` screen-share/toast block into `kurento-screen-share.js`.
2. Extract `kurento-service.js` subtitle UI block into `kurento-subtitle-ui.js`.
3. Add both scripts after `kurento-service.js` in `kurentoroom.html`.
4. Leave WebSocket/peer/reconnect/TURN paths in `kurento-service.js`.
5. Validate syntax, reconstruction equivalence, deterministic checks, desktop sync, and review evidence.

This reduces `kurento-service.js` while keeping runtime behavior and existing global API stable.

## 5. Document Mapping (Checklist)

Restarted 2026-07-06: Phase 01–03 and the frontend component guide were deleted and will be rewritten from scratch because this Base Plan's Desktop impact scope changed (build/build-scripts check added in §2–3). Code changes from the prior pass were fully rolled back.

- [x] Requirements and data: `plan_docs/01-plan/web_rtc_frontend_refactor.md`
- [x] Interface and sequence: `plan_docs/02-design/web_rtc_frontend_refactor.md`
- [x] Implementation evidence: `plan_docs/03-implementation/web_rtc_frontend_refactor.md`
- [x] Frontend implementation guide: `nodejs-frontend/plan_docs/web_rtc_frontend_refactor_plan.md`
- [x] Gap analysis: `plan_docs/04-analyze/web_rtc_frontend_refactor.md`
- [ ] Expert review: `plan_docs/05-expert-review/web_rtc_frontend_refactor.md`
- [ ] Final report: `plan_docs/06-report/web_rtc_frontend_refactor.md`
