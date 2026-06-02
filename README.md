# AerOS by Prakersh - AI Procurement OS

> A working-prototype procurement OS where a buyer drafts purchase requests
> conversationally with an AI co-pilot, dispatches them to vendors across
> multiple channels, and consolidates every reply - in any format - into a
> single side-by-side comparison.

Built around a Blinkit/Zepto-style dark-store procurement persona, AerOS
mirrors aerchain Aera's multi-agent framing (Intake → Sourcing → Vendor
Onboarding → Evaluation → Negotiation → Contract → Invoice → Analytics).
Six agents run end-to-end (buyer Procurement co-pilot, Sourcing, Intake,
Evaluation, Vendor co-pilot, post-award PO); Negotiation, Contract, Invoice,
and Analytics ship as extensible Coming-Soon stubs.

## Demo

📺 **[`demo/demo.mp4`](demo/demo.mp4)** - a single, captioned end-to-end
walkthrough on one RFx: the buyer signs in and **drafts a request in plain
language** (rendered as a line-item table), the co-pilot **dispatches it and
auto-invites the matching vendors**, **two vendors reply** in different formats
(a spreadsheet read by AI, then a scanned photo read by the vision model), and
the buyer **compares the offers side-by-side and awards** them. Each step is
introduced by a title card naming the actor and account.

The live-demo runbook (prompts, accounts, and sample vendor attachments in
every supported format) lives in [`demo/SCRIPT.md`](demo/SCRIPT.md).

## Why

Procurement teams lose hours to **format chaos** - vendors quote in PDFs,
Excels, photographed price lists, scanned proformas, and free-form email
bodies. AerOS turns every reply, on every channel, into one normalized
`Offer` schema and surfaces them in a comparison matrix the buyer can act on.

## Highlights

- **Conversational RFx drafting** - describe the need in plain text and the
  co-pilot drafts the line items, applying the buyer's saved defaults (payment,
  delivery, validity, currency, tax) when drafting and sending the request.
  Both the buyer procurement chat and the admin chat have access to inventory
  tools (add, find, and search items) so SKUs can be managed inline without
  leaving the conversation. (Voice input is in progress - see Status.)
- **Omnichannel reply routing** - every RFx thread can be replied to via
  in-app chat, email (SMTP/IMAP), or Telegram bot; HMAC-signed correlation
  tokens fuse them into one thread regardless of channel.
- **Format-agnostic intake** - PDF (digital + scanned), Word, Excel, CSV,
  images, photographed price lists, and email bodies are extracted via a
  vision-capable LLM, then fused per-message into a single confidence-scored
  offer.
- **Side-by-side comparison + split award** - per-line-item award decisions
  highlight lowest price and best lead time with per-field confidence badges;
  the buyer can manually override extracted fields.
- **Post-award PO** - a PDF PO is generated (WeasyPrint) and emailed
  automatically to the awarded vendor(s).
- **Structured agent responses** - the chat co-pilot streams its progress live
  (Server-Sent Events), then renders typed `AgentBlocks` (text, tables, cards,
  key-value, lists, actions) in the UI, XSS-safe.
- **Observability layer** - per-LLM-call telemetry (model, tokens, cost,
  latency, cache), per-chat pipeline-report panel, and a buyer observability
  dashboard.
- **Security & guardrails by design** - bcrypt + JWT auth, RBAC enforced in
  the service layer, HMAC-signed correlation tokens, magic-byte upload
  validation, prompt-injection isolation, append-only audit log, log redaction.
- **TDD as a primary discipline** - 773 backend tests (unit + integration) at
  81% line coverage (≥80% enforced in CI) plus Playwright E2E across the full
  RFx lifecycle; AI calls are mocked for deterministic offline runs. See
  [Testing & quality](#testing--quality).

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI · SQLModel · SQLite · Alembic · Huey · structlog |
| Frontend | React 19 · Vite · TypeScript · Tailwind v4 · TanStack Query · Zustand · React Router 7 |
| AI chat + vision | **Any OpenAI-compatible endpoint** - MiniMax M3 is the default, but you can point the base URL / model / key at OpenAI, Azure OpenAI, NVIDIA NIM, or a local server (Ollama, vLLM, llama.cpp). |
| AI embeddings *(optional)* | NVIDIA NIM (`nvidia/nv-embed-v1`) for vendor-by-SKU semantic matching |
| ASR *(in progress)* | Whisper for voice input - Groq-hosted (`whisper-large-v3-turbo`); not fully completed yet |
| Provider abstraction | thin `ChatProvider` protocol - any OpenAI-compatible endpoint (MiniMax, NVIDIA NIM, OpenAI, Anthropic, Azure) |
| Auth | PyJWT + bcrypt direct (no passlib) |
| Channels | aiosmtplib + IMAPClient · python-telegram-bot · FastAPI WebSocket |
| PO render | WeasyPrint (HTML → PDF) |
| Testing | pytest · pytest-asyncio · `unittest.mock` · aiosmtpd · Playwright · Vitest |

## Getting Started

**Prerequisites:** Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Node 18+
(pnpm or npm). No external services are needed to boot - the database is local
SQLite, created and seeded for you.

```bash
./app.sh setup     # install deps, copy .env.example -> .env, migrate, seed demo data
# edit .env: set ONE chat/vision endpoint (see "Configuration" below)
./app.sh start     # backend :4040, Huey worker, frontend :5173
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:4040> · API docs: <http://localhost:4040/docs>

### Configuration - what's required vs optional

The app **starts with no keys at all** (you can log in with the demo accounts
and click around). To exercise the AI features you only need **one** thing: an
OpenAI-compatible chat/vision endpoint.

**Required for the AI co-pilot** - a chat/vision endpoint:

```bash
AEROS_MIMO_API_KEY=...                                  # key for your endpoint
AEROS_MIMO_BASE_URL=https://api.minimax.io/v1           # default (MiniMax)
AEROS_DEFAULT_CHAT_MODEL=MiniMax-M3
AEROS_DEFAULT_VISION_MODEL=MiniMax-M3
```

These `AEROS_MIMO_*` / `AEROS_DEFAULT_*` values are just a generic
OpenAI-compatible config - **MiniMax M3 is the default**. AerOS talks to the
endpoint through the standard OpenAI `chat/completions` API (and the standard
`image_url` message content for vision), so any OpenAI-compatible endpoint works
unchanged: OpenAI, Azure OpenAI, NVIDIA NIM, Together, or a local server
(Ollama / vLLM / llama.cpp) - just supply that endpoint's base URL, key, and
model name.

> ⚠️ **Use a large multimodal (vision) model.** Format-agnostic intake sends
> PDFs, scanned proformas, photographed price lists, and images to the model as
> image input, so `AEROS_DEFAULT_VISION_MODEL` **must be a model that accepts
> images** (e.g. `MiniMax-M3`, `gpt-4o`, `qwen2.5-vl`, `llama-3.2-vision`). A
> text-only model still runs the chat co-pilot but will fail to read uploaded
> documents. The chat and vision models can differ, but both must be reachable
> at the same base URL.

**Optional - everything below degrades gracefully if left blank:**

| Feature | Env var | Without it |
|---|---|---|
| Voice input (Whisper ASR) - *in progress* | `AEROS_GROQ_API_KEY` | **Not fully completed yet** - deprioritized for time. Whisper is the intended ASR (Groq-hosted for now); type your messages in the meantime. |
| Vendor-by-SKU embeddings | `AEROS_NVIDIA_API_KEY` | Vendor matching falls back to category/keyword logic. |
| Email channel (SMTP/IMAP) | `AEROS_SMTP_*` / `AEROS_IMAP_*` | In-app reply still works; email reply/ingest is off. |
| Telegram channel | `AEROS_TELEGRAM_BOT_TOKEN` | In-app reply still works; the Telegram bot is off. |

Provider status (active/disabled per key) is visible in the app under
**Admin → AI Providers**. For production, also set `AEROS_JWT_SECRET` and
`AEROS_HMAC_SECRET` to random values.

Other `app.sh` commands: `stop`, `restart`, `test [--pytest-only|--test-uat-only]`,
`lint`, `migrate`, `upgrade`, `seed`, `logs <backend|frontend|worker>`.

Frontend-specific details are in [`frontend/README.md`](frontend/README.md).

### Demo accounts

Seeded by `./app.sh setup` (or `./app.sh seed`). Listed at
`GET /api/auth/demo-accounts` when `AEROS_SHOW_DEMO_CREDENTIALS=true`.

| Role | Email | Password |
|---|---|---|
| Buyer | `buyer@aeros.demo` | `buyer123` |
| Vendor | `freshfarm@vendor.demo` (and other `*@vendor.demo`) | `vendor123` |
| Admin | `admin@aeros.demo` | `admin123` |

## Testing & quality

Testing was treated as a first-class deliverable, not an afterthought.

- **773 backend tests** across **46 unit** and **13 integration** modules,
  **81% line coverage** with an **80% gate enforced in CI** (`pytest --cov`).
- **Unit** - services, the agentic pipeline (intent detection, tool selection,
  deterministic fallbacks, one-shot guards), offer parsing/normalization,
  guardrails, and RBAC. AI provider calls are mocked, so the suite is
  deterministic and runs fully offline with no API key.
- **Integration** - the full RFx lifecycle, the chat API, and the
  format-agnostic extraction pipeline (PDF, Word, Excel, CSV, image, email)
  exercised end-to-end against the real database and services.
- **End-to-end** - Playwright specs for auth, buyer, vendor, admin, and the
  complete RFx lifecycle drive the real React UI against the running backend.
  The captioned [`demo/demo.mp4`](demo/demo.mp4) walkthrough is itself a passing
  E2E spec that runs **draft → dispatch → vendor reply → compare → award**
  through the live UI and a real LLM - the same end-to-end path the assignment
  asks for.
- **Frontend** - Vitest component/unit specs.
- A separate live-LLM connectivity check runs when an API key is configured
  (skipped offline).

```bash
./app.sh test                 # full suite: backend (pytest + coverage) + Playwright E2E
./app.sh test --pytest-only   # backend only
./app.sh test --test-uat-only # Playwright E2E only
```

## Status

**Prototype complete and demo-ready.** The six functional agents are fully
implemented with real LLM calls through the OpenAI-compatible provider
(MiniMax M3 by default). Format-agnostic extraction covers PDF, Word, Excel, CSV,
images, and email bodies. The side-by-side comparison matrix with
per-line-item award and automatic PO generation is functional.

**In progress:** voice input (Whisper ASR) - the mic UI and provider are wired
but the end-to-end flow was not completed for this milestone due to time
limits; it is not required for any other feature, so type to use the co-pilot.

## License

Copyright (C) 2026 Prakersh. Licensed under the GNU General Public License
v3.0 - see [LICENSE](LICENSE).
