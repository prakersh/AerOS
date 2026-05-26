# AEROS — AI Procurement OS

> A working-prototype procurement OS where a buyer drafts purchase requests
> conversationally with an AI co-pilot, dispatches them to vendors across
> multiple channels, and consolidates every reply — in any format — into a
> single side-by-side comparison.

Built around a Blinkit/Zepto-style dark-store procurement persona, AEROS
mirrors aerchain Aera's multi-agent framing (Intake → Sourcing → Vendor
Onboarding → Evaluation → Negotiation → Contract → Invoice → Analytics) and
ships four real agents end-to-end with the rest staged as extensible stubs.

## Why

Procurement teams lose hours to **format chaos** — vendors quote in PDFs,
Excels, photographed price lists, scanned proformas, and free-form email
bodies. AEROS turns every reply, on every channel, into one normalized
`Offer` schema and surfaces them in a comparison matrix the buyer can act on.

## Highlights

- **Conversational RFx drafting** — voice or text, English / Hindi / Hinglish
  auto-detect, with a proactive Terms chip that confirms the buyer's
  defaults (payment, delivery, validity, currency, tax) before dispatch.
- **Omnichannel reply routing** — every RFx thread can be replied to via
  in-app chat, email (SMTP/IMAP), or Telegram bot; signed correlation
  tokens fuse them into one thread regardless of channel.
- **Format-agnostic intake** — PDF (digital + scanned), Word, Excel, CSV,
  images, photographed price lists, and email bodies (HTML + plaintext +
  forwarded chains) are extracted via NVIDIA NIM vision + chat, then fused
  per-message into a single confidence-scored offer.
- **Side-by-side comparison + split award** — per-line-item award decisions
  highlight lowest price and best lead time with per-field confidence
  badges; the buyer can manually override extracted fields.
- **Post-award PO** — a PDF PO is generated and emailed automatically to
  the awarded vendor(s).
- **Multi-agent architecture** — Intake, Sourcing, Vendor co-pilot,
  Evaluation, and PO agents, with Negotiation / Contract / Invoice /
  Analytics scaffolded as Coming-Soon tabs.
- **Observability layer** — per-LLM-call telemetry (model, tokens, cost,
  latency, cache), per-agent trace IDs, per-chat pipeline-report panel,
  and a buyer observability dashboard.
- **Security & guardrails by design** — bcrypt + JWT auth, RBAC enforced
  in the service layer, HMAC-signed correlation tokens, magic-byte upload
  validation, prompt-injection isolation, dual-LLM intent validation on
  high-stakes actions, append-only audit log, log redaction.
- **TDD as a primary discipline** — unit + integration + Playwright E2E,
  ≥80% backend line coverage, 100% on agents / guardrails / security /
  correlation, VCR cassettes for offline AI replay.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI · SQLModel · SQLite · Alembic · Huey · structlog |
| Frontend | React 19 · Vite · TypeScript · Tailwind v4 · TanStack Query · Zustand |
| AI primary | NVIDIA NIM (OpenAI-compatible) — chat + vision + embeddings |
| ASR | Groq Whisper (`whisper-large-v3-turbo`) |
| Provider abstraction | thin `ChatProvider` protocol — any OpenAI- or Anthropic-compatible endpoint |
| Auth | PyJWT + bcrypt direct (no passlib) |
| Channels | aiosmtplib + IMAPClient · python-telegram-bot · FastAPI WebSocket |
| PO render | weasyprint (HTML → PDF) |
| Testing | pytest · pytest-asyncio · VCR.py · aiosmtpd · Vitest · Playwright |

## Status

**Planning complete. Implementation pending.**

See [`IMPLMENTETION_PLAN_CONTEXT.md`](./IMPLMENTETION_PLAN_CONTEXT.md) for
the full design, work-packet tracker, and live progress checkboxes.

## License

TBD.
