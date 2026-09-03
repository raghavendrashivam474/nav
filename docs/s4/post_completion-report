---

# NAV v0 — Sprint 4 Post-Sprint Report

**To:** Senior Developer / Tech Lead
**From:** Junior Developer
**Date:** September 4, 2025
**Project:** NAV (Navigate · Augment · Venture) v0
**Sprint:** S4 — Voice Pipeline
**Duration:** 1 day
**Status:** ✅ Complete — Ready for review and merge

---

## 1. Executive Summary

Sprint 4 is complete. NAV has transitioned from a purely text-driven system to one with its first real human interface: voice.

The complete voice loop is now functional: a user speaks into a microphone, NAV transcribes the audio locally, routes the resulting text through the existing S3 cognition pipeline (Orchestrator → Cognition → AIGateway → Ollama), receives an AI-generated response, synthesizes it into speech, and plays it back through the speakers.

Critically, **zero files under `core/`, `capabilities/`, or `ai/` were modified.** Voice was implemented strictly as a communication modality layered on top of the existing architecture, exactly as the S4 brief prescribed. The S3 baseline of 30 passing tests remains fully intact, and 34 new tests have been added on top.

---

## 2. Sprint Objective vs. Outcome

### Primary Question (from the brief)

> *"Can NAV naturally communicate through voice without contaminating the Core with modality-specific logic?"*

### Answer

**Yes.** The VoiceInterface constructs a standard `Request(request_id="voice_...", payload={"prompt": transcript})` and passes it to `Orchestrator.route_request("cognition", request)`. From the Orchestrator's perspective, a voice-originated request is byte-for-byte identical to a text-originated request. Cognition, the AI Gateway, and the AI providers have no awareness that voice exists.

### The §27 Replacement Test

> *"If tomorrow we remove the voice interface completely, NAV Core still works exactly as before."*

**Confirmed.** The `interfaces/voice/` module has zero inbound dependencies from Core, Capabilities, or AI. Deleting the entire `interfaces/` directory would leave the S1/S2/S3 pipeline fully functional.

> *"If tomorrow we replace the STT or TTS provider, the Core, Cognition, Orchestrator, and AI layer don't care."*

**Confirmed.** Both STT and TTS are behind abstract base classes (`SpeechToText`, `TextToSpeech`). Swapping `faster-whisper` for Azure Speech or `pyttsx3` for ElevenLabs requires only a new adapter class and an environment variable change. No other file needs to be touched.

---

## 3. What Was Built

### 3.1 Audio Abstractions (`interfaces/voice/audio.py`)

Two frozen dataclasses — `AudioInput` and `AudioOutput` — that serve as provider-neutral containers for audio data. The `samples` field is typed as `Any` deliberately: different providers produce different native types (numpy arrays for Whisper, raw bytes for mocks, OS handles for pyttsx3), and the abstraction exists only to prevent those types from leaking into the rest of NAV. This is not an audio framework; it is a boundary membrane.

### 3.2 Contracts (`interfaces/voice/contracts.py`)

Two abstract base classes mirroring the S3 `AIGateway` pattern:

- `SpeechToText` with a single method: `transcribe(audio: AudioInput) -> str`
- `TextToSpeech` with a single method: `synthesize(text: str) -> AudioOutput`

Both also expose a `name` property for logging. The rest of NAV depends only on these interfaces, never on concrete implementations.

### 3.3 Error Hierarchy (`interfaces/voice/errors.py`)

Mirrors the `ai/errors.py` pattern from S3:

```
VoiceError (base)
 ├── ConfigurationError   — missing env vars, missing optional deps
 ├── MicrophoneError      — hardware capture failures, silence detection
 ├── STTError             — transcription failures
 ├── TTSError             — synthesis failures
 └── PlaybackError        — speaker output failures
```

All voice-layer exceptions inherit from `VoiceError`, so callers can catch voice failures uniformly without importing provider-specific exception types.

### 3.4 Speech-to-Text Layer (`interfaces/voice/stt/`)

Three files:

- **`whisper_stt.py`** — Local STT using `faster-whisper`. Model is loaded lazily on first call to avoid startup cost. Configurable via `NAV_WHISPER_MODEL` (defaults to `base`). Runs on CPU with int8 quantization.
- **`mock_stt.py`** — Deterministic test double. Returns a pre-configured transcript. Can be configured to raise `STTError` for failure-path testing. Records all calls for assertion.
- **`factory.py`** — Reads `NAV_STT_PROVIDER` from the environment and returns the appropriate implementation. Defaults to `whisper`. Raises `ConfigurationError` for unknown providers.

### 3.5 Text-to-Speech Layer (`interfaces/voice/tts/`)

Three files:

- **`pyttsx3_tts.py`** — Offline TTS using the operating system's native voice engine (SAPI5 on Windows, NSSpeechSynthesizer on macOS, espeak on Linux). No API key, no network, no cost. Notably, pyttsx3 speaks directly through the OS audio stack rather than returning a buffer, so the adapter returns an `AudioOutput` with `metadata={"self_played": True}`. The VoiceInterface checks this flag and skips the Speaker step when the TTS provider has already handled playback. This keeps the abstraction honest without forcing an unnatural buffer-return pattern on a library that doesn't support it.
- **`mock_tts.py`** — Deterministic test double. Returns a canned `AudioOutput` containing the UTF-8 bytes of the input text. Records all calls.
- **`factory.py`** — Reads `NAV_TTS_PROVIDER` from the environment. Defaults to `pyttsx3`.

### 3.6 Hardware Boundaries (`interfaces/voice/microphone.py`, `speaker.py`)

- **`Microphone`** — Blocking press-to-talk capture via `sounddevice`. Records a fixed-duration mono PCM buffer at 16 kHz. Includes a basic silence detector (RMS threshold) that raises `MicrophoneError` if the recording is near-silent, preventing wasted STT cycles.
- **`Speaker`** — Blocking playback via `sounddevice`.
- **`FakeMicrophone`** / **`FakeSpeaker`** — Test doubles that require zero audio hardware. `FakeMicrophone` returns a pre-configured `AudioInput` and can simulate hardware failures. `FakeSpeaker` records all `AudioOutput` objects it receives for assertion.

All real hardware imports (`sounddevice`, `numpy`) are deferred to method call time, so importing `interfaces.voice` on a base NAV install (without voice extras) never fails.

### 3.7 VoiceInterface (`interfaces/voice/interface.py`)

The orchestration boundary. A single public method:

```python
def run_once(self, max_seconds: float = 8.0) -> Response:
```

Executes one complete press-to-talk cycle:

1. Capture audio via the injected `MicrophoneProtocol`
2. Transcribe via the injected `SpeechToText`
3. Construct a `Request(request_id="voice_...", payload={"prompt": transcript})`
4. Route through the injected `Orchestrator` to the configured capability (default: `"cognition"`)
5. Synthesize the reply via the injected `TextToSpeech`
6. Play via the injected `SpeakerProtocol` (unless TTS self-played)

Every failure at every stage is caught and translated into a failed `Response` with a descriptive `error` string. Callers never see a bare Python exception. When cognition fails, the interface makes a best-effort attempt to speak the error message to the user before returning the failed response.

### 3.8 Configuration

New environment variables (documented in `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `NAV_STT_PROVIDER` | `whisper` | STT engine selection |
| `NAV_WHISPER_MODEL` | `base` | Whisper model size |
| `NAV_TTS_PROVIDER` | `pyttsx3` | TTS engine selection |
| `NAV_MICROPHONE_SAMPLE_RATE` | `16000` | Mic capture rate |
| `NAV_VOICE_LIVE` | `0` | Gates the live hardware test |

New optional dependency group in `pyproject.toml`:

```toml
[project.optional-dependencies]
voice = [
    "sounddevice>=0.4.6",
    "numpy>=1.24",
    "faster-whisper>=1.0.0",
    "pyttsx3>=2.90",
]
```

The base `pip install .` remains lean (only `httpx`). Voice dependencies are pulled in only via `pip install -e ".[voice]"`.

---

## 4. What Was Explicitly NOT Built

Per the S4 brief, the following were deliberately excluded to maintain sprint discipline:

- ❌ Wake-word detection
- ❌ Always-listening background service
- ❌ Continuous microphone monitoring / VAD
- ❌ Custom STT or TTS models
- ❌ Emotional voice synthesis
- ❌ Multi-device audio synchronization
- ❌ Interruption / barge-in handling
- ❌ AR avatar or physical NAV device
- ❌ Autonomous agents
- ❌ Persistent memory
- ❌ Research engine
- ❌ Model router
- ❌ Complex UI
- ❌ Cloud audio infrastructure
- ❌ Async rewrite of NAV Core

The S4 finish line was: **Press → Speak → NAV thinks → NAV speaks.** That is exactly what was delivered.

---

## 5. Verification Matrix

| Check | Target | Result |
|---|---|---|
| S1/S2/S3 existing tests | 30 tests | 30 passed ✅ |
| Audio value objects | 5 tests | 5 passed ✅ |
| Error hierarchy | 3 tests | 3 passed ✅ |
| STT unit + factory | 7 tests | 7 passed ✅ |
| TTS unit + factory | 7 tests | 7 passed ✅ |
| Voice pipeline happy path | 4 tests | 4 passed ✅ |
| Voice pipeline failure paths | 5 tests | 5 passed ✅ |
| Architectural invariant tests | 2 tests | 2 passed ✅ |
| Live voice test (gated) | 1 test | 1 skipped ✅ |
| Normal suite requires mic/speakers? | No | Confirmed ✅ |
| Normal suite requires API keys? | No | Confirmed ✅ |
| Ruff lint (`ruff check .`) | 0 errors | Clean ✅ |
| Ruff format (`ruff format --check .`) | 0 errors | Clean ✅ |
| Mypy (`mypy core/ ai/ capabilities/ interfaces/`) | 39 files | Clean ✅ |
| **Total tests** | **64** | **63 passed, 1 skipped** ✅ |

### Live Hardware Verification

The gated live test (`test_voice_live.py`) was also executed manually with real hardware:

```
pip install -e ".[voice]"
$env:NAV_VOICE_LIVE = "1"
python -m unittest tests.test_voice_live -v
```

Result: Microphone captured 8 seconds of audio → Whisper transcribed it → Ollama generated a response → pyttsx3 spoke it through the speakers. Full loop confirmed on real hardware.

---

## 6. Architecture Decisions and Rationale

| # | Decision | Rationale |
|---|---|---|
| 1 | Voice lives in `interfaces/voice/`, not `capabilities/voice/` | Voice is a communication modality, not a reasoning capability. Placing it under `capabilities/` would imply it provides intelligence, which it does not. |
| 2 | VoiceInterface talks to the Orchestrator, not Cognition directly | Preserves the existing routing architecture. If S5 adds a model router or S6 adds memory injection, voice automatically benefits without modification. |
| 3 | `AudioInput.samples` typed as `Any` | Different providers produce fundamentally different types (numpy arrays, bytes, file paths). Forcing a single type would either require expensive conversion or leak provider details. `Any` is honest. |
| 4 | Lazy imports for all optional dependencies | `import interfaces.voice` must never fail on a base install. Heavy libraries (faster-whisper, sounddevice, pyttsx3) are imported only inside the methods that need them. |
| 5 | Optional `[voice]` dependency group | Keeps the base NAV install minimal (one dep: httpx). Voice deps are opt-in. Mirrors the S3 philosophy of minimal runtime footprint. |
| 6 | Synchronous `run_once()` | S3 Core is sync. Introducing async at the voice boundary would require either an async-to-sync bridge or a Core rewrite, both of which violate the "don't touch Core" constraint. Async can be explored in a future sprint when there is actual concurrent I/O pressure. |
| 7 | pyttsx3 `self_played` metadata flag | pyttsx3 speaks directly through the OS audio stack and does not return an audio buffer. Rather than fighting the library or building a WAV capture wrapper, the adapter honestly reports that playback has already occurred. The VoiceInterface respects this flag. |
| 8 | Press-to-talk, no wake word | Dramatically reduces complexity. Wake-word detection requires continuous audio streaming, VAD, and background threading — all of which are separate engineering problems that would have dominated the sprint. |

---

## 7. Git History

S4 was committed in 7 logical chunks for clean bisectability:

```
e1e2878 docs(s4): compile Sprint 4 completion report
d1c269d feat(s4): implement VoiceInterface orchestration and verify full audio loop
62cbcd1 feat(s4): build physical and fake hardware boundaries for microphone and speaker
a78d73d feat(s4): implement text-to-speech layer with offline native pyttsx3 and mock adapters
c62dce1 feat(s4): implement speech-to-text layer with local Whisper and mock adapters
00a18d0 feat(s4): define core voice contracts, audio value objects, and error hierarchy
a812647 chore(s4): configure dependencies, environments, and type stubs for voice pipeline
```

All 7 commits are on `main`, ahead of `origin/main`. Working tree is clean.

---

## 8. Known Issues and Technical Debt

| # | Item | Severity | Notes |
|---|---|---|---|
| 1 | `sounddevice` DeprecationWarning on NumPy 2.5 | Low | `data.shape = -1, channels` in sounddevice internals. Upstream issue; will resolve when sounddevice releases a NumPy 2.5-compatible version. Does not affect functionality. |
| 2 | Whisper `base` model downloads ~140MB on first run | Low | Expected behavior. Model is cached locally by `huggingface-hub` and subsequent runs are instant. |
| 3 | No interruption / barge-in | Expected | Explicitly deferred per S4 brief. Will become relevant when S5+ introduces conversational turn-taking. |
| 4 | No streaming TTS | Expected | Current implementation waits for the full cognition response before synthesizing. Streaming would reduce perceived latency but requires async I/O and a streaming TTS provider. |
| 5 | `pyttsx3` voice quality | Low | OS-native voices are functional but not natural-sounding. A future TTS provider (ElevenLabs, Coqui, Piper) would improve this without any code changes to VoiceInterface. |

---

## 9. S5 Readiness

Sprint 4 leaves NAV in a strong position for S5 (Model Router & Complexity-Based Routing):

- The AI Gateway abstraction (`AIGateway.generate()`) is proven with two providers and untouched by S4.
- The VoiceInterface routes through the Orchestrator, so any routing intelligence added at the Gateway or Orchestrator level will automatically apply to voice-originated requests.
- The test suite is comprehensive (64 tests) and fast (~11 seconds including the live Ollama integration test).
- The codebase is clean (Ruff, Mypy) and well-documented.

---

## 10. Questions for Senior Developer

1. **S5 Model Router scope**: Should the router live inside `ai/gateway/` (replacing `DefaultAIGateway` with a smarter version) or as a separate layer between the Orchestrator and the Gateway? The current architecture supports either approach.

2. **Voice streaming**: At what sprint should we explore streaming TTS (speak while the model is still generating)? This would require async I/O and a streaming-capable TTS provider.

3. **Wake word**: Is S6 (Memory) still the planned next sprint after S5, or should we front-load wake-word detection? The current press-to-talk model is functional but not hands-free.

4. **Live test in CI**: The live voice test is gated by `NAV_VOICE_LIVE=1` and skipped by default. Should we set up a CI job that runs it on a machine with audio hardware, or keep it as a manual developer check?

---

**Sprint 4 is complete and ready for your review.** The branch is 7 commits ahead of `origin/main` and the working tree is clean. Let me know when you'd like to do the code review or if you want me to push.