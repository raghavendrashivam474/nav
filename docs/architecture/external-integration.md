# NAV External Integration Architecture (Avni & External Systems)

**Sprint:** S11 — Foundation & v1 Architecture  
**Status:** Approved Specification  

---

## 1. Core Integration Principle

> **"NAV consumes external systems through stable, abstract provider boundaries. External systems remain independent repositories, independent lifecycles, and independent architectures."**

NAV must never:
- Directly import external system internal modules.
- Couple its Core contracts to third-party data models.
- Assume a specific external transport (HTTP, gRPC, IPC) inside Core.

---

## 2. The Provider / Adapter Model

```text
 ┌─────────────────────────────────────────────────────────────┐
 │                         NAV Core                            │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                 NAV Capability / Contract                   │
 │           (e.g., SpeechToText, TextToSpeech)                │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                   NAV Adapter / Provider                    │
 │               (e.g., AvniVoiceAdapter)                      │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                     Transport Boundary (Network / IPC / API)
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                      External System                        │
 │                   (e.g., AVNI Service)                      │
 └─────────────────────────────────────────────────────────────┘
```

---

## 3. Concrete Case: Avni Integration

### 3.1 What Avni Is to NAV
Avni is an independent, advanced voice / audio intelligence system. To NAV, Avni is an external service provider that can satisfy:
- **Speech-to-Text** (`SpeechToText` contract)
- **Text-to-Speech / Persona Rendering** (`TextToSpeech` contract)

### 3.2 Boundary Contract
Inside NAV:

```python
# interfaces/voice/contracts.py (already stable in v0.10)
from abc import ABC, abstractmethod
from interfaces.voice.audio import AudioInput, AudioOutput


class SpeechToText(ABC):
    @abstractmethod
    def transcribe(self, audio: AudioInput) -> str: ...


class TextToSpeech(ABC):
    @abstractmethod
    def synthesize(self, text: str) -> AudioOutput: ...
```

Inside an eventual `interfaces/voice/stt/avni_stt.py` and `interfaces/voice/tts/avni_tts.py`:
- `AvniSTTAdapter(SpeechToText)` communicates with Avni via its client protocol.
- `AvniTTSAdapter(TextToSpeech)` communicates with Avni via its client protocol.
- No Avni internals are imported into NAV.

### 3.3 Transport Flexibility
The adapter encapsulates the transport mechanism:
- **Local IPC / Unix Domain Socket / Named Pipe** (low latency).
- **Local HTTP / WebSocket Server** (standard service decoupling).
- **gRPC** (high-performance streaming audio).

NAV Core and `VoiceInterface` remain 100% agnostic to the transport choice.

---

## 4. Generalization to Future External Systems

This identical adapter pattern applies to:
- **Search Providers:** `SearchProvider` $\rightarrow$ Brave, DuckDuckGo, Tavily, Google.
- **AI Models:** `AIGateway` $\rightarrow$ Ollama, OpenAI, Anthropic, Local vLLM.
- **Execution Environments:** Tool / Code Sandbox $\rightarrow$ Docker, MicroVM, Local runner.
- **External Sensors / Hardware:** Audio capture, camera, robotics.

---

*Approved for S11 baseline.*
