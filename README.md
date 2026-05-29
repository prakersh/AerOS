# AerOS by Prakersh — AI Procurement OS

> A working-prototype procurement OS where a buyer drafts purchase requests
> conversationally with an AI co-pilot, dispatches them to vendors across
> multiple channels, and consolidates every reply — in any format — into a
> single side-by-side comparison.

Built around a Blinkit/Zepto-style dark-store procurement persona, AerOS
mirrors aerchain Aera's multi-agent framing (Intake → Sourcing → Vendor
Onboarding → Evaluation → Negotiation → Contract → Invoice → Analytics).
Six agents run end-to-end (buyer Procurement co-pilot, Sourcing, Intake,
Evaluation, Vendor co-pilot, post-award PO); Negotiation, Contract, Invoice,
and Analytics ship as extensible Coming-Soon stubs.

## Demo

📺 **[`demos/demo.mp4`](demos/demo.mp4)** — a single, captioned end-to-end
walkthrough on one RFx: the buyer signs in and **drafts a request in plain
language** (rendered as a line-item table), the co-pilot **dispatches it and
auto-invites the matching vendors**, **two vendors reply** in different formats
(a spreadsheet read by AI, then a scanned photo read by the vision model), and
the buyer **compares the offers side-by-side and awards** them. Each step is
introduced by a title card naming the actor and account.

The live-demo runbook (prompts, accounts, and sample vendor attachments in
every supported format) lives in [`demo/SCRIPT.md`](demo/SCRIPT.md).

## Why

Procurement teams lose hours to **format chaos** — vendors quote in PDFs,
Excels, photographed price lists, scanned proformas, and free-form email
bodies. AerOS turns every reply, on every channel, into one normalized
`Offer` schema and surfaces them in a comparison matrix the buyer can act on.

## Highlights

- **Conversational RFx drafting** — voice or text; the co-pilot gathers items
  and applies the buyer's saved defaults (payment, delivery, validity, currency,
  tax) when drafting and sending the request.
- **Omnichannel reply routing** — every RFx thread can be replied to via
  in-app chat, email (SMTP/IMAP), or Telegram bot; HMAC-signed correlation
  tokens fuse them into one thread regardless of channel.
- **Format-agnostic intake** — PDF (digital + scanned), Word, Excel, CSV,
  images, photographed price lists, and email bodies are extracted via a
  vision-capable LLM, then fused per-message into a single confidence-scored
  offer.
- **Side-by-side comparison + split award** — per-line-item award decisions
  highlight lowest price and best lead time with per-field confidence badges;
  the buyer can manually override extracted fields.
- **Post-award PO** — a PDF PO is generated (WeasyPrint) and emailed
  automatically to the awarded vendor(s).
- **Structured agent responses** — the chat co-pilot streams its progress live
  (Server-Sent Events), then renders typed `AgentBlocks` (text, tables, cards,
  key-value, lists, actions) in the UI, XSS-safe.
- **Observability layer** — per-LLM-call telemetry (model, tokens, cost,
  latency, cache), per-chat pipeline-report panel, and a buyer observability
  dashboard.
- **Security & guardrails by design** — bcrypt + JWT auth, RBAC enforced in
  the service layer, HMAC-signed correlation tokens, magic-byte upload
  validation, prompt-injection isolation, append-only audit log, log redaction.
- **TDD as a primary discipline** — unit + integration + Playwright E2E,
  ≥80% backend line coverage enforced in CI, VCR cassettes for offline AI replay.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI · SQLModel · SQLite · Alembic · Huey · structlog |
| Frontend | React 19 · Vite · TypeScript · Tailwind v4 · TanStack Query · Zustand · React Router 7 |
| AI chat + vision | MiMo (`mimo-v2.5`) by default, via an OpenAI-compatible endpoint |
| AI embeddings | NVIDIA NIM (`nvidia/nv-embed-v1`) for vendor-by-SKU matching |
| ASR | Groq Whisper (`whisper-large-v3-turbo`) for voice input |
| Provider abstraction | thin `ChatProvider` protocol — any OpenAI-compatible endpoint (MiMo, NVIDIA NIM, OpenAI, Anthropic, Azure) |
| Auth | PyJWT + bcrypt direct (no passlib) |
| Channels | aiosmtplib + IMAPClient · python-telegram-bot · FastAPI WebSocket |
| PO render | WeasyPrint (HTML → PDF) |
| Testing | pytest · pytest-asyncio · VCR.py · aiosmtpd · Playwright |

## Getting Started

**Prerequisites:** Python 3.12+, [`uv`](https://docs.astral.sh/uv/), Node 18+
(pnpm or npm).

```bash
./app.sh setup     # install deps, copy .env.example -> .env, migrate, seed demo data
# edit .env: set AEROS_MIMO_API_KEY (chat/vision) and AEROS_GROQ_API_KEY (voice)
./app.sh start     # backend :4040, Huey worker, frontend :5173
```

- Frontend: <http://localhost:5173>
- Backend: <http://localhost:4040> · API docs: <http://localhost:4040/docs>

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

## Status

**Prototype complete and demo-ready.** The six functional agents are fully
implemented with real LLM calls through the OpenAI-compatible provider
(MiMo by default). Format-agnostic extraction covers PDF, Word, Excel, CSV,
images, and email bodies. The side-by-side comparison matrix with
per-line-item award and automatic PO generation is functional.

## License

Copyright (C) 2026 Prakersh. Licensed under the GNU General Public License
v3.0 — see [LICENSE](LICENSE).
