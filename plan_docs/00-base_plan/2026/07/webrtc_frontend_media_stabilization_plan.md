# [Base Plan] WebRTC Frontend Media Stabilization

## 0. Cycle Declaration

This is a new independent L3 cycle, separate from issue #138.

Baseline:
- The #138 WebRTC frontend split is already complete.
- `kurento-service.js` is already separated from `kurento-screen-share.js` and `kurento-subtitle-ui.js`.
- No #138 file is treated as trusted by assumption. All affected files must be re-read and re-grepped in this cycle.

Turn boundary:
- Initial user boundary was Phase 03 first.
- The user later approved continuing PDCA, so Phase 04, Phase 05, and Phase 06 were completed in the same cycle.
- Commit, push, and shipping remain out of scope for this pass.

## 1. Scope Freeze

In scope:
- Performance: consolidate the 2-second screen-share monitoring path so a single tick does not call `RTCPeerConnection.getStats()` three times.
- Performance: stop/pause the monitoring interval when the full screen-share panel is hidden. Collapse/minimal mode is not treated as full hidden and must not pause monitoring.
- Bug fix: remove the structural double-audio playback path created by the remote participant `video` element and paired `audio` element.
- Consolidation: reduce duplication across these eight RTC files while preserving behavior except where explicitly allowed:
  - `nodejs-frontend/static/js/rtc/SystemAudioCapture.js`
  - `nodejs-frontend/static/js/rtc/speechSubtitleManager.js`
  - `nodejs-frontend/static/js/rtc/recording.js`
  - `nodejs-frontend/static/js/rtc/mediaDevice.js`
  - `nodejs-frontend/static/js/rtc/kurento-subtitle-ui.js`
  - `nodejs-frontend/static/js/rtc/kurento-service.js`
  - `nodejs-frontend/static/js/rtc/kurento-screen-share.js`
  - `nodejs-frontend/static/js/rtc/AudioMixer.js`
- Required support files:
  - `nodejs-frontend/static/js/rtc/participant.js`
  - `nodejs-frontend/templates/room/kurentoroom.html` only if a script or panel hook must change.
- Desktop build-related inspection:
  - `chatforyou-desktop/build-scripts/build.js`
  - `chatforyou-desktop/build-scripts/sync-frontend.js`
  - `chatforyou-desktop/build-scripts/validate-sync.js`
  - `chatforyou-desktop/build-scripts/lib/sync-engine.js`
  - `chatforyou-desktop/build-scripts/lib/convert_path.js`
  - `chatforyou-desktop/build-scripts/convert_path.json`
  - `chatforyou-desktop/package.json`

Out of scope:
- Backend changes.
- WebSocket message contract changes.
- SDP, ICE, TURN, reconnect state-machine, and Kurento endpoint lifecycle changes.
- Direct edits under `chatforyou-desktop/src`.
- ES module migration. The existing classic global script model remains in force.
- Removing `SystemAudioCapture.js` only because it appears lightly referenced. Deletion requires a separate proof.

## 2. Behavior Change Boundary

Allowed non-behavior-preserving change:
- Double-audio fix only. The current behavior is defective because remote audio can be played by both `video` and `audio` elements.

Must remain behavior-preserving:
- `getStats()` consolidation.
- Screen-share quality decision semantics except for removing redundant stats reads.
- Full panel-hidden interval control, except for the explicit resource-saving behavior. Collapse/minimal mode must preserve monitoring behavior.
- Eight-file consolidation and duplicate removal.
- Recording, subtitle, device switching, system audio, and audio mixer behavior.

If performance or consolidation requires signaling, reconnect, SDP/ICE, or backend contract changes, stop and request a new scope decision.

## 3. Verified Current Facts

### 3.1 Performance Hot Path

Current `kurento-screen-share.js` evidence:

| Function | Evidence | Current issue |
|----------|----------|---------------|
| `detectNetworkQuality()` | `kurento-screen-share.js:86`, `getStats()` at `:92` | Reads stats for network grade. |
| `detectDevicePerformance()` | `kurento-screen-share.js:176`, `getStats()` at `:182` | Reads stats for device grade. |
| `updateScreenShareStats()` | `kurento-screen-share.js:423`, `getStats()` at `:433` | Reads stats for UI metrics. |
| `startScreenShareMonitoring()` | `kurento-screen-share.js:737`, interval at `:744` | One 2-second tick calls `updateScreenShareStats()` and then quality adjustment. |
| `determineOptimalQuality()` | `kurento-screen-share.js:283` | Calls both network and device detection. |

Result: one monitoring tick can perform three stats reads.

Panel visibility evidence at cycle start:
- `stopScreenShareMonitoring()` clears the interval at `kurento-screen-share.js:764`.
- `hideScreenShareControls()` exists at `kurento-screen-share.js:797` and again at `:2305`.
- `toggleScreenShareControls()` is at `kurento-screen-share.js:1206`.
- The panel hide path does not currently own interval pause/resume semantics.

Implementation outcome:
- Full `#screenShareControls` hidden state pauses monitoring.
- `toggleScreenShareControls()` and `toggleMinimalMode()` hide internal UI sections only and do not pause monitoring.

### 3.2 Double Audio Root Cause

Current `participant.js` evidence:
- `Participant` creates the participant media elements at `participant.js:214`.
- Remote participants receive both a `video` and an `audio` element.
- `video.muted = isMainParticipant()` at `participant.js:255`.
- `audio.muted = isMainParticipant()` at `participant.js:266`.
- For remote participants, both resolve to unmuted by default.

Current `kurento-service.js` evidence:
- `video.srcObject = event.stream` at `kurento-service.js:1734`, assigning the full remote stream to the video element.
- `audio.srcObject = audioOnlyStream` at `kurento-service.js:1739`.
- Both are initially muted at `kurento-service.js:1744-1745`.
- `audio.muted = false` at `kurento-service.js:1752` and fallback at `:1756`.
- `video.muted = false` at `kurento-service.js:1768`.

Conclusion: the same remote audio can be rendered by two DOM elements. This is a structural bug and the fix is an intentional behavior change.

### 3.3 Eight-file Inventory Requirement

The consolidation table in Phase 01/02 must be based on a fresh grep of all eight files from the start of this cycle. The #138 split files are included in the same re-verification group as the other files.

Known initial inventory:

| Area | Files | Initial finding |
|------|-------|-----------------|
| Stats and screen UI | `kurento-screen-share.js` | Stats collection, quality decision, toast, panel UI, system audio mixing are concentrated here. |
| Remote playback | `participant.js`, `kurento-service.js` | Video/audio element policy is split and currently inconsistent. |
| Recording mixer | `recording.js`, `AudioMixer.js` | Recording consumes mixer singleton and participant remote streams. |
| System audio capture | `SystemAudioCapture.js`, `kurento-screen-share.js` | Display/system audio capture responsibility is partially duplicated or disconnected. |
| Subtitle UI | `speechSubtitleManager.js`, `kurento-subtitle-ui.js`, `recording.js` | Subtitle button/status and recording-driven subtitle handling cross file boundaries. |
| Device switching | `mediaDevice.js`, `participant.js`, `recording.js` | Output sink and input replacement can affect playback and recording paths. |

## 4. Impact Analysis

- Backend: no planned changes.
- Frontend: WebRTC frontend architecture and media playback path are affected.
- Desktop: build/sync path must be inspected even though `chatforyou-desktop/src` is not edited directly.
- QA: static checks are insufficient for the double-audio fix. Actual listening test is required before ship, but that belongs to later QA/ship evidence, not this Phase 03-only pass.

## 5. Desktop Build-related Requirement

This cycle must explicitly inspect `chatforyou-desktop` build-related code, not only the `nodejs-frontend` source.

Current inspected facts:
- `chatforyou-desktop/package.json:20-22` exposes sync scripts.
- `chatforyou-desktop/package.json:68` includes `src/**/*` in packaging.
- `chatforyou-desktop/build-scripts/build.js:100-116` syncs frontend and compiles SCSS.
- `chatforyou-desktop/build-scripts/sync-frontend.js:63-71` validates, syncs, and converts paths.
- `chatforyou-desktop/build-scripts/lib/sync-engine.js:155-225` recursively copies static/template/config directories.
- `chatforyou-desktop/build-scripts/validate-sync.js:66-202` validates file existence, size, and path conversion.
- `chatforyou-desktop/build-scripts/lib/convert_path.js:355-508` applies generic path conversion rules.

Mandatory Phase 03 evidence slots:
- `node --check` for desktop build scripts.
- `npm run sync` in `chatforyou-desktop` after frontend source edits.
- `node build-scripts/validate-sync.js` after sync.
- Verify modified RTC files land under `chatforyou-desktop/src/static/js/rtc/` after sync.
- Do not directly edit `chatforyou-desktop/src`.

Desktop validation outcome:
- `npm run sync` passed.
- Synced desktop RTC JS copies passed `node --check`.
- `node build-scripts/validate-sync.js` was executed and failed on existing desktop template `static/...` path findings. Phase 05 review concluded this is not introduced by the RTC JS diff, but desktop validation is not fully green.

## 6. Review Context Requirement

Phase 05 review must explicitly include `plan_docs/00-base_plan/2026/07/web_rtc_frontend_refactor_plan.md` as baseline context because this cycle starts after the #138 split.

Review outcome:
- Project sub-agent 3-iteration review completed.
- Claude external review 3 iterations completed with the #138 refactor plan context included.
- Claude external re-review 3 iterations completed after rework.
- A final extra Claude retry after the last `setVolume()` tightening was attempted but could not complete because the Claude session limit was reached.

## 7. Document Mapping

- [x] Base plan: `plan_docs/00-base_plan/2026/07/webrtc_frontend_media_stabilization_plan.md`
- [x] Requirements plan: `plan_docs/01-plan/webrtc_frontend_media_stabilization.md`
- [x] Design: `plan_docs/02-design/webrtc_frontend_media_stabilization.md`
- [x] Implementation evidence: `plan_docs/03-implementation/webrtc_frontend_media_stabilization.md`
- [x] Frontend guide: `nodejs-frontend/plan_docs/webrtc_frontend_media_stabilization_plan.md`
- [x] Phase 04: `plan_docs/04-analyze/webrtc_frontend_media_stabilization.md`
- [x] Phase 05: `plan_docs/05-expert-review/webrtc_frontend_media_stabilization.md`
- [x] Phase 06: `plan_docs/06-report/webrtc_frontend_media_stabilization.md`
