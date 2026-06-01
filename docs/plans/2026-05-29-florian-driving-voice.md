# Florian Driving Voice Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Keep private data local. Do not expose Hermes tools or transcripts to public endpoints.

**Goal:** Build a hands-free, driving-safe voice interface to Florian that can be invoked from iPhone/CarPlay, presents a native Apple call-like interface, and routes audio/control securely through Cloudflare.

**Architecture:** Use a small native iOS app with CallKit for the system call UI, App Intents/Siri Shortcuts for hands-free start, and a WebRTC audio session to a local macOS voice gateway. Cloudflare protects the control plane with Tunnel + Access; media uses either Cloudflare Realtime/TURN or a WebRTC provider selected after the MVP latency test. The backend never exposes raw Hermes access publicly and only mints short-lived voice session tokens for Patryk's devices.

**Tech Stack:** SwiftUI, CallKit, AVAudioSession, App Intents/Siri Shortcuts, LiveKit iOS SDK or WebRTC.framework, FastAPI or Node backend, Cloudflare Tunnel, Cloudflare Access, optional Cloudflare Realtime/TURN, Hermes local CLI/API, OpenAI Realtime or local STT/TTS pipeline depending on latency/privacy tradeoff.

---

## Research summary

### What others have done

- `fluxions-ai/vui` - real-time WebRTC voice assistant with faster-whisper, local LLM, local TTS, OpenAI Realtime compatibility. Useful for local-first voice pipeline patterns. GitHub: https://github.com/fluxions-ai/vui
- `den-vasyliev/voice-mcp-agent` - LiveKit Agents voice assistant with MCP tools. Useful reference for connecting real-time voice to tool ecosystems. MIT. GitHub: https://github.com/den-vasyliev/voice-mcp-agent
- `ahmad2b/langgraph-voice-call-agent` - LiveKit voice/call agent pattern for connecting a full-duplex voice session to an agent graph. MIT. GitHub: https://github.com/ahmad2b/langgraph-voice-call-agent
- `PatterAI/Patter` - open-source Vapi/Retell-style voice AI SDK, supports phone numbers through Twilio/Telnyx. MIT. Useful if we later add SIP/PSTN. GitHub: https://github.com/PatterAI/Patter
- X search found a highly relevant public thread by Cocoanetics describing a Swift voice assistant using OpenAI Realtime + CallKit. Key lesson: CallKit gives the native phone UI and car/Bluetooth audio routing, but audio routing required trial-and-error.
- X search also surfaced production signals: Uber appears to be experimenting with an OpenAI Realtime/WebRTC voice booking agent in its iOS app. This supports the architecture direction: native iOS + WebRTC/realtime voice.

### Apple constraints

- CallKit is the right API for a native Phone/FaceTime-like call UI. Apple describes it as displaying the system-calling UI for VoIP services and coordinating calls with the system.
- CarPlay supports messaging and VoIP apps that support SiriKit intents; voice-based conversational apps are now explicitly mentioned in Apple's CarPlay developer page. A full CarPlay app generally needs a CarPlay entitlement request, but CallKit/AVAudioSession should still route audio through the car even before a dedicated CarPlay UI exists.
- Siri/App Intents can start the app/session hands-free. The likely invocation is a custom phrase like “Start Florian call” or a Shortcut named “Call Florian”.
- True “FaceTime contact” behavior is not available. The closest native UX is CallKit inside our own iOS app.

### Cloudflare constraints

- Cloudflare Tunnel securely publishes HTTP/WSS origins without exposing a public IP.
- Cloudflare Access can protect the web/control plane, but native mobile flows need either Access service tokens, OIDC, WARP device posture, or a custom one-time pairing token. Do not hardcode long-lived tokens in the app.
- WebRTC media cannot be treated like ordinary HTTP. The design needs a media path: Cloudflare Realtime, Cloudflare TURN, LiveKit/RealtimeKit, or a TCP/TLS TURN fallback. The control API can be protected by Access; the media session must use short-lived tokens and room/session scoping.

## Security model

1. Backend binds to `127.0.0.1` only.
2. Cloudflare Tunnel exposes only the voice control origin, never Hermes internals.
3. Cloudflare Access restricts access to Patryk's identity/device.
4. First run performs pairing from the local Mac and stores a device key in iOS Keychain.
5. The backend mints short-lived session tokens for WebRTC rooms, scoped to one call and expiring in minutes.
6. Voice mode has a driving-safe policy: short replies, no complex multi-step execution while driving unless explicitly safe, and follow-up summaries via Telegram/iMessage after the call.
7. No transcripts by default for driving calls. If transcript storage is later enabled, store locally and encrypt.
8. Sensitive tools remain local. External STT/TTS/model calls follow Patryk's provider policy: OpenAI is acceptable for sensitive/personal data per current memory; xAI/Grok is not used for private voice sessions.
9. Cloudflare credentials stay in Keychain or Cloudflare-managed tunnel config. Avoid `cloudflared ... --token ...` showing tokens in process lists.
10. Rate-limit calls/session creation and reject all unpaired devices.

## Product design

### iOS app name

Working name: **Florian Drive**.

### Visual style

- Native SwiftUI, SF Pro, system colors, Dynamic Type.
- One primary screen: large circular **Call Florian** button, connection status, last successful route, and privacy status.
- In-call screen is mostly CallKit/system UI. If the user returns to the app, show a calm waveform, elapsed time, mute/end controls, and a small “Driving mode active” label.
- Avoid dashboards while driving. No dense text, no long controls.
- Dark mode first, with light mode support.

### App states

- Not paired: “Pair with Florian on your Mac” + QR/deep link.
- Ready: “Call Florian”.
- Connecting: system call UI starts, backend session token requested.
- In call: CallKit controls audio; app shows minimal waveform if opened.
- Ended: “Call ended” + optional button to send a written summary to Telegram.

### Siri/CarPlay UX

- App Intent: `StartFlorianCallIntent`.
- Shortcut phrase: “Call Florian” or “Start Florian”.
- CarPlay path: Siri launches the Shortcut/App Intent; CallKit surfaces the call UI and routes audio to car/Bluetooth.
- Dedicated CarPlay UI is Phase 4 after Apple entitlement feasibility.

## Open technical decisions

1. **Media stack:** LiveKit vs raw WebRTC vs Cloudflare RealtimeKit.
   - Preferred MVP: LiveKit-style abstraction, because it has iOS SDKs and agent examples.
   - Preferred secure routing: Cloudflare Access for control + Cloudflare TURN/Realtime or private LiveKit ingress with strict tokens.
2. **Voice brain:** OpenAI Realtime vs local STT/TTS + Hermes CLI turns.
   - Fastest natural conversation: OpenAI Realtime with tool bridge to Hermes.
   - Most local/private: WebRTC audio to local VAD/STT/TTS pipeline, then Hermes text turns.
   - MVP should measure latency with both if practical.
3. **Hermes integration API:** use an internal localhost endpoint or a controlled `hermes chat` subprocess session for early prototype, then promote to a proper gateway platform/plugin.
4. **Apple entitlements:** CallKit works for VoIP-like UX; dedicated CarPlay app visibility may require an entitlement request and possibly SiriKit VoIP/messaging intents.

---

## Phase 0: Project placement and guardrails

### Task 0.1: Create project workspace outside the Hermes core repo

**Objective:** Avoid polluting the Hermes core repository, which currently has unrelated local modifications.

**Files:**
- Create: `/Volumes/T7/hermes/projects/florian-driving-voice/README.md`
- Create: `/Volumes/T7/hermes/projects/florian-driving-voice/.gitignore`
- Create: `/Volumes/T7/hermes/projects/florian-driving-voice/docs/security.md`

**Steps:**
1. Create the project directory.
2. Initialize a separate git repository.
3. Add `.gitignore` for `.env`, tokens, Xcode derived data, build artifacts, recordings, transcripts.
4. Add `docs/security.md` with the security model above.
5. Run `git status` and confirm no secrets are tracked.

**Verification:**
- `git status -sb` shows only intended scaffold files.
- `grep -R "token\|secret\|password\|key" .` shows no credential values.

### Task 0.2: Define driving-mode safety policy

**Objective:** Create a policy file used by backend and prompts.

**Files:**
- Create: `docs/driving-mode-policy.md`

**Content requirements:**
- Short spoken replies by default.
- No reading long documents while driving.
- Can capture notes/reminders and send follow-up summaries.
- Can control safe smart-home/media actions only when unambiguous.
- Confirmation required before sending messages/emails/posts.
- Emergency disclaimers: not a substitute for emergency services.

**Verification:**
- Policy is under 1 page and can be embedded in prompts.

---

## Phase 1: Minimal secure voice backend

### Task 1.1: Build localhost-only voice control API

**Objective:** Provide a small API that mints short-lived voice sessions after local/dev auth.

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/florian_voice/__init__.py`
- Create: `backend/florian_voice/app.py`
- Create: `backend/tests/test_sessions.py`

**Implementation shape:**
- FastAPI app binds to `127.0.0.1`.
- Endpoints:
  - `GET /health` returns `{status: "ok"}`.
  - `POST /pair/start` creates one-time pairing code for local setup.
  - `POST /session` returns a short-lived signed session token for a paired device.
- Use Python stdlib `secrets` and `hmac` initially; store dev pairing state in a local file excluded from git.

**Verification:**
- `pytest backend/tests -q` passes.
- `curl http://127.0.0.1:<port>/health` returns ok.
- Binding check confirms no `0.0.0.0` listener.

### Task 1.2: Add Hermes text-turn bridge

**Objective:** Let the voice backend send a transcript turn to Hermes locally and receive a short response.

**Files:**
- Modify: `backend/florian_voice/app.py`
- Create: `backend/florian_voice/hermes_bridge.py`
- Create: `backend/tests/test_hermes_bridge.py`

**Implementation shape:**
- Start with a narrow `POST /turn` endpoint accepting `{session_id, text}`.
- Internally call a local Hermes subprocess or local API with a bounded timeout.
- Use a driving-mode prompt prefix.
- Strip/limit long outputs to spoken-safe length.

**Verification:**
- Unit test mocks subprocess/API.
- Manual test with “say hello in one sentence” returns a short response.

### Task 1.3: Add WebRTC media prototype

**Objective:** Establish full-duplex audio session between browser/iOS client and backend/media agent.

**Files:**
- Create: `backend/florian_voice/media.py`
- Create: `web-prototype/` or `ios/FlorianDrive/` depending on selected media SDK.

**Preferred route:**
- Use LiveKit/Pipecat style first if it reduces WebRTC complexity.
- If Cloudflare RealtimeKit is viable with native iOS SDK, spike it before committing.

**Verification:**
- Local call transmits microphone audio and receives synthesized audio.
- Barge-in/interruption behavior is measured.
- Latency log includes capture -> transcript -> response -> audio timings.

---

## Phase 2: Cloudflare secure routing

### Task 2.1: Create Cloudflare Tunnel route for control API

**Objective:** Publish the control API through Cloudflare without exposing the Mac directly.

**Files:**
- Create: `infra/cloudflare/README.md`
- Create: `infra/cloudflare/tunnel.example.yml`

**Steps:**
1. Use existing Cloudflare setup if available.
2. Configure hostname, e.g. `voice.<domain>`.
3. Route only to `http://127.0.0.1:<voice-port>`.
4. Protect with Cloudflare Access.
5. Validate Access token server-side where possible.
6. Ensure no tunnel tokens are visible in process arguments.

**Verification:**
- Remote unauthenticated request denied.
- Authenticated request to `/health` succeeds.
- Backend still binds localhost only.

### Task 2.2: Design WebRTC media path through Cloudflare

**Objective:** Pick the secure media route before shipping to iPhone.

**Options to test:**
- Cloudflare RealtimeKit/SFU.
- Cloudflare TURN service with LiveKit/raw WebRTC.
- WARP private network to local LiveKit, only if CarPlay cellular behavior is acceptable.

**Verification:**
- iPhone on cellular can connect without LAN/VPN fiddling.
- Audio survives lock screen and route changes.
- No inbound public ports on the Mac.

---

## Phase 3: Native iOS CallKit app

### Task 3.1: Create SwiftUI iOS project

**Objective:** Scaffold a native app with simple design and pairing/settings screens.

**Files:**
- Create: `ios/FlorianDrive/FlorianDrive.xcodeproj` or XcodeGen project files.
- Create: `ios/FlorianDrive/FlorianDrive/App.swift`
- Create: `ios/FlorianDrive/FlorianDrive/Views/ReadyView.swift`
- Create: `ios/FlorianDrive/FlorianDrive/Views/PairingView.swift`
- Create: `ios/FlorianDrive/FlorianDrive/Services/KeychainStore.swift`

**Design:**
- One large call button.
- Privacy/auth state visible.
- No clutter.
- Dynamic Type and VoiceOver labels.

**Verification:**
- Builds in simulator.
- Snapshot/manual visual check in light and dark mode.

### Task 3.2: Add CallKit call lifecycle

**Objective:** Present native call UI and route audio like a VoIP call.

**Files:**
- Create: `ios/FlorianDrive/FlorianDrive/Services/CallManager.swift`
- Create: `ios/FlorianDrive/FlorianDrive/Services/AudioSessionManager.swift`
- Modify: `ios/FlorianDrive/FlorianDrive/Views/ReadyView.swift`

**Implementation shape:**
- `CXProvider` and `CXCallController` for outgoing call to “Florian”.
- Configure `AVAudioSession` for voice chat.
- Handle answer/end/mute/route changes.

**Verification:**
- Starting a call shows system call UI.
- Ending from system UI tears down the media session.
- Bluetooth route appears in audio options on device.

### Task 3.3: Add WebRTC client connection

**Objective:** Connect CallKit audio lifecycle to the WebRTC voice backend.

**Files:**
- Create: `ios/FlorianDrive/FlorianDrive/Services/VoiceSessionClient.swift`
- Modify: `CallManager.swift`

**Verification:**
- End-to-end call connects from iPhone to backend.
- The app handles network loss and call end cleanly.
- No token printed in logs.

### Task 3.4: Add Siri/App Intent

**Objective:** Start a Florian call hands-free.

**Files:**
- Create: `ios/FlorianDrive/FlorianDrive/Intents/StartFlorianCallIntent.swift`
- Modify app entitlements/capabilities as needed.

**Verification:**
- Shortcut appears in Shortcuts app.
- Siri phrase can start the CallKit flow.
- Works from locked phone if Apple permits the configured intent.

---

## Phase 4: CarPlay hardening

### Task 4.1: Physical CarPlay test matrix

**Objective:** Validate hands-free behavior in the actual car environment.

**Tests:**
- Siri starts “Call Florian”.
- Audio routes to car speakers/mic.
- Lock screen behavior works.
- Interruption from real phone call pauses/ends safely.
- Poor network behavior fails gracefully.

**Verification:**
- Pass/fail notes in `docs/carplay-test-log.md`.

### Task 4.2: CarPlay entitlement decision

**Objective:** Decide whether a dedicated CarPlay UI is worth an entitlement request.

**Criteria:**
- If CallKit + Siri covers the use case, skip dedicated CarPlay UI.
- If app visibility in CarPlay launcher is needed, prepare entitlement request and app category justification.

---

## Phase 5: Operationalization

### Task 5.1: LaunchAgent for backend

**Objective:** Run the voice backend on the Mac safely.

**Files:**
- Create: `infra/launchd/cc.patpatpat.florian-voice.plist`
- Create: `scripts/install-launchagent.sh`

**Verification:**
- Backend restarts after reboot.
- Logs rotate or stay bounded.
- Service binds localhost only.

### Task 5.2: Monitoring and kill switch

**Objective:** Make it safe to disable quickly.

**Files:**
- Create: `scripts/status.sh`
- Create: `scripts/stop.sh`
- Create: `scripts/security-check.sh`

**Verification:**
- One command shows backend/tunnel/media status.
- One command stops voice access.
- Security check confirms no public listeners and no token strings in tracked files.

---

## Implementation discipline

- Use a separate git repo under `/Volumes/T7/hermes/projects/florian-driving-voice`.
- Use TDD for backend session/auth logic.
- Do not commit recordings, transcripts, `.env`, tokens, derived data, or pairing state.
- After every task, run tests and inspect `git diff` for secrets.
- Use subagents for isolated research/review/code tasks when the configured subagent model is working; current delegation failed due provider credits, so do not rely on it until routing is fixed.
- Before any Cloudflare changes with external exposure, verify the hostname, Access policy, and rollback path.

## Immediate next step

Start with Phase 0 and Task 1.1. This creates a safe project skeleton and a localhost-only control API. Do not touch Cloudflare or iOS signing until the local API and security checks are green.
