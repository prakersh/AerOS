# AEROS — AI Procurement OS

> **Single source of truth** for design + implementation tracking + sub-agent dispatch.
> On plan approval, this file is mirrored to `/Users/prakersh/projects/aerchain/IMPLMENTETION_PLAN_CONTEXT.md` (project root) and kept in sync.

---

## 0. Context

Aerchain-style assignment:

> Build an end-to-end working prototype where a **buyer drafts an RFx in conversation with an AI co-pilot**, the RFx goes out to vendors over **email (or any channel)**, vendors reply in **whatever format they like — PDF, Word, Excel, scanned proforma, photographed rate card, or even an email body** — and the system **reads each response and consolidates them into a single side-by-side comparison**. Liberty over framework, models, channels, storage, UI, persona, sample data. Stubs OK for plumbing; **AI loops must be real and functional**. Deliverable: a **working prototype ready for live demo**.

We are not building one feature. We are building **AEROS — a procurement OS** that mirrors aerchain Aera's multi-agent framing (Intake → Sourcing → Vendor Onboarding → Evaluation → Negotiation → Contract → Invoice → Analytics).

**Persona**: procurement agent at a Blinkit/Zepto-style dark store. Manages a catalog of daily-purchase SKUs (produce, dairy, packaged FMCG), keeps a directory of preferred vendors per category, and conversationally drafts purchase requests.

**Authenticated users (two roles)**: Buyer and Vendor — both with chat + upload.

**Channels (unified)**: in-app chat (web), Email (SMTP/IMAP), Telegram bot. Any inbound reply on any channel — tagged with a signed correlation token — routes to the same RFx thread.

**Demo brand**: AEROS.

---

## 1. Assignment ↔ Plan Traceability Matrix

| Requirement | Where covered | Status |
|---|---|---|
| Buyer drafts RFx via AI co-pilot conversation | §3 IntakeAgent + §5 buyer chat UI | planned |
| RFx out to vendors over email (or any channel) | §4 channels (SMTP + Telegram + in-app) | planned |
| Vendor reply: PDF | §3.4 `extractors/pdf.py` (PyMuPDF + vision for scanned) | planned |
| Vendor reply: Word | §3.4 `extractors/word.py` (python-docx + LLM normalizer) | planned |
| Vendor reply: Excel | §3.4 `extractors/excel.py` (openpyxl + LLM normalizer) | planned |
| Vendor reply: CSV/TSV | §3.4 `extractors/spreadsheet.py` (covers Excel + CSV) | planned |
| Vendor reply: scanned proforma (PDF) | §3.4 `extractors/pdf.py` scanned-branch → vision per page | planned |
| Vendor reply: photographed rate card (image) | §3.4 `extractors/image.py` → vision | planned |
| Vendor reply: email body | §3.4 `extractors/email_body.py` (HTML sanitize + plaintext + forwarded-chain) | planned |
| Multi-attachment fusion (body + PDF + image in one reply) | §3.4 `OfferFusionService` | planned |
| Reads each response (real AI loop) | §3 EvaluationAgent + NIM vision/chat | planned |
| Side-by-side comparison | §5 ComparisonMatrix UI + §3 OfferService | planned |
| AI loops real, not stubs | NIM + Groq direct SDK; VCR for tests | planned |
| Working prototype, live demo | §8 build order, §9 demo script | planned |

---

## 2. Decisions Confirmed (running log)

| # | Decision | Choice | Date |
|---|---|---|---|
| D1 | Product scope | AEROS — full procurement OS, mirroring Aera's 8 agents; ship 4 real, stub 4 as "Coming Soon" | confirmed |
| D2 | Persona | Procurement agent at Blinkit/Zepto-style dark store; daily-purchase SKUs | confirmed |
| D3 | Authenticated roles | **Buyer + Vendor + Admin** (3-tier RBAC). Admin module modeled on memo.sbs (DB-backed AI config, user mgmt, cross-tenant observability, full audit). See §3.8. | confirmed |
| D4 | Channels | In-app chat + Email (SMTP+IMAP) + Telegram bot, unified via signed correlation tokens | confirmed |
| D5 | Channel implementation order | **Web (in-app) FIRST → Email second → Telegram last** | confirmed |
| D6 | AI provider primary | **NVIDIA NIM** (free tier) via OpenAI-compatible SDK at `https://integrate.api.nvidia.com/v1` | confirmed |
| D7 | Provider-agnostic | Thin `ChatProvider` protocol → any OpenAI-compat OR Anthropic-compat endpoint | confirmed |
| D8 | ASR | Groq `whisper-large-v3-turbo` | confirmed |
| D9 | Voice scope | **Both buyer AND vendor chat** have mic button | confirmed |
| D10 | Language | **Hindi + Hinglish + English (auto-detect)** | confirmed |
| D11 | Framework | **Direct SDK + Pydantic + plain Python agent classes** — no LangChain, no LangGraph (see §3.1 for rationale) | confirmed |
| D12 | Backend | FastAPI + SQLModel + SQLite + Alembic + Huey | confirmed |
| D13 | Frontend | React 19 + Vite + Tailwind v4 + TanStack Query + Zustand, built using `/ui-ux-pro-max` skill | confirmed |
| D14 | TDD | Unit + Integration + E2E (Playwright). Coverage ≥80% backend. | confirmed |
| D15 | Post-award action | **Generate PO PDF + email to awarded vendor(s)** (reportlab/weasyprint) | confirmed |
| D16 | User profile defaults | Each buyer-user has default terms (payment, delivery, validity, currency, tax, delivery window); each vendor has standard offered terms; IntakeAgent **proactively confirms** defaults during chat draft | confirmed (this turn) |
| D17 | Sub-agent development | Plan structured as **parallelizable work-packets** with checkboxes; each maps to a sub-agent type (feature-implementer, ui-tester, test-runner, etc.) | confirmed |
| D18 | Implementation plan doc | Mirror this file to `/Users/prakersh/projects/aerchain/IMPLMENTETION_PLAN_CONTEXT.md` as the first implementation step | confirmed |
| D19 | UserDefaults scope | **Per-user** (not per-org); applied to RFx at draft time, overridable per RFx | confirmed |
| D20 | Confirmation UX | **Proactive Terms chip** in chat: IntakeAgent shows inline editable card with payment/delivery/validity/currency/tax; click-to-edit or chat to change; explicit before dispatch | confirmed |
| D21 | RFx types in prototype | **RFQ only** for demo; `RFxRun.type` enum already supports RFI/RFP for future | confirmed |
| D22 | Vendor onboarding | **Seed-only** (8 vendor users pre-created with known passwords); no self-signup in prototype | confirmed |
| D23 | Compliance depth | **Prod-leaning architecture + prototype implementation**: all OWASP + AI guardrails shipped & tested; encryption envelope / append-only triggers / GDPR delete worker / hash-chain checksum / dep-scan in CI documented but stubbed | confirmed |
| D24 | Guardrails-first | Phase 2 explicitly includes `ai/guardrails/` + tests before any agent ships (see P2.8) | confirmed |
| D25 | TDD enforcement | Pre-commit hook blocks impl without test; CI fails on coverage drop; ≥80% backend, 100% on `agents/`, `ai/guardrails/`, `security/`, `channels/correlation.py` | confirmed |
| D26 | Observability & Stats | First-class observability layer modeled on memo.sbs: per-LLM-call telemetry (model, latency, tokens, cost, cache hit), per-agent-run telemetry, per-chat pipeline report (which tools fired + timings), aggregate stats dashboard. See §3.7. | confirmed |
| D27 | Admin module | Dedicated `/admin/*` shell: DB-backed AI provider/model config (toggle, default, per-model token cap), user management (list/create/suspend/role-change), system settings (retention, rate limits, budgets), cross-tenant observability + audit-log full view, vendor KYC approval. RBAC enforced at router + service + DB-query layer. See §3.8. | confirmed |
| D28 | Commit & Push discipline | Every significant step commits + pushes to `origin/main`; phase-level mandatory checkpoints; tags at end of Day 1 (`v0.1-day1`) and Day 2 (`v0.2-demo`). See §8.0. | confirmed |
| D29 | Realistic procurement flows | Vendor decline (with reason), buyer withdraw/cancel RFx, offer revision history (resubmit before deadline keeps prior versions via `superseded_by_offer_id`), multi-stage reminders (T-24h + T-2h + final, idempotent per slot via `reminders_sent_json`). See §3.10. | confirmed |
| D30 | Vendor suggestion strategy | Hybrid ranking inside IntakeAgent: filter by `Vendor.category_ids` (deterministic), rank within category by `nv-embed-v1` cosine similarity of RFx line-item SKU names to vendor's served-SKU embeddings, tie-break by `performance_score × preferred_rank`. Returns top-N (default 5). | confirmed |
| D31 | Late offer policy | Offers arriving after `response_deadline` are accepted but flagged (`Offer.is_late=true`); ComparisonMatrix shows a "late" badge; buyer chooses whether to include in award. No silent drops. | confirmed |
| D32 | AI provider failover | `AIProviderConfig` rows carry `priority_rank` per kind (chat/vision/asr/embedding). On provider error or timeout >5s, `ai/factory.py` falls through to the next enabled provider of the same kind; chat surfaces a one-line "switched to backup model" notice. Admin tunable in `/admin/ai/providers`. | confirmed |
| D33 | Confidence thresholds | Per-field confidence <0.7 → yellow badge + "review" CTA; overall offer confidence = MIN of all line-item field confidences (worst-link); offers with overall <0.5 auto-flag for buyer review and cannot be awarded without explicit acknowledge. | confirmed |
| D34 | In-app canonical thread | Whatever channel a dispatch went over (email / Telegram / in-app), the vendor's `/vendor/inbox` always shows the full thread (all messages, AI co-pilot replies, attachments, channel-of-origin badge). Vendor can always reply in-app regardless of invitation channel. Implication: email-bounce / Telegram-blocked are NOT blocking failure modes — vendor self-serves by logging in. See §3.6. | confirmed |
| D35 | SourcingAgent channel confirmation | SourcingAgent **proposes** a dispatch plan (channel per vendor) based on vendor's available channels (priority: in-app > email > Telegram) and **asks the buyer to confirm** via a "Dispatch Plan" chat card before sending. Buyer can override per-vendor channel or approve. No silent dispatch. See §3.4. | confirmed |

---

## 3. Architecture

### 3.1 Framework rationale (the one the user asked to think through)

After evaluating Direct SDK, LangChain, LangGraph, and Pydantic AI against AEROS' actual needs (provider-agnostic NVIDIA NIM, multimodal extraction quality, omnichannel orchestration, 1–2 day budget, live demo, TDD):

**Choice: Direct SDK (OpenAI-compatible client) behind a thin `ChatProvider` protocol — no LangChain, no LangGraph.**

| Aspect | Direct SDK (chosen) | LangChain | LangGraph | Pydantic AI |
|---|---|---|---|---|
| Dep weight | ~3 packages | 10+ packages, transitive bloat | langchain-core + own runtime | small but adds layer |
| Multimodal contract | direct, full control | leaky abstractions on vision | same as direct (calls inside nodes) | thinner multimodal |
| Provider-swap | trivial via protocol | `init_chat_model` works but multimodal varies | provider-agnostic | model classes |
| Stateful orchestration | DB-backed state machine | basic | excellent + interrupts | basic |
| Live-demo debuggability | every line is ours | stack traces dive into framework | similar to LangChain | smaller surface |
| Demo "wow" graph | render Mermaid from DB ourselves | n/a | built-in graph viz | n/a |
| TDD friction | low (just classes) | mock framework primitives | checkpointer adds setup | typed = good |
| Matches user 4DPocket philosophy | yes | no | partial | no |

**Why no LangGraph despite stateful orchestration**: The orchestration is small enough (≤6 statuses on `RFxRun`) that a DB-backed state machine is clearer and ships faster. We **render the agent graph for the demo from our own state model** — same wow factor, zero framework risk.

**Multi-agent ≠ agent framework.** Each Aera-style agent (Intake, Sourcing, Vendor, Evaluation) is a plain Python class in `src/aeros/agents/` with one public `run(ctx, input) → AgentResult` method and Pydantic input/output schemas. This **is** a multi-agent system.

### 3.2 Stack

| Layer | Tech | Notes |
|---|---|---|
| Backend | FastAPI 0.115+, Python 3.12+, sync `def` handlers | matches 4DPocket convention |
| ORM | SQLModel + Alembic | |
| DB | SQLite (default, single-file) | demo-friendly; PostgreSQL later via DSN swap |
| Background | Huey (SQLite backend) | IMAP poll, Telegram poll-fallback, offer extraction, notifications, PO render |
| Frontend | React 19 + TypeScript + Vite + Tailwind v4 + Lucide + TanStack Query + Zustand + Framer Motion | built via `/ui-ux-pro-max` skill |
| Streaming | FastAPI SSE for chat + WebSocket for in-app channel | |
| AI primary | NVIDIA NIM via OpenAI SDK pointed at `https://integrate.api.nvidia.com/v1` | chat: `nvidia/llama-3.1-nemotron-70b-instruct` (configurable) |
| AI vision | NIM `/v1/vision/extract` (`nvidia/neva-22b`) with `microsoft/phi-3.5-vision-instruct` fallback; vision-language chat: `meta/llama-3.2-90b-vision-instruct` for richer cases | |
| AI embeddings | NIM `nvidia/nv-embed-v1` for vendor-by-SKU semantic matching | |
| ASR | Groq `whisper-large-v3-turbo` | voice notes from buyer + vendor |
| Email out | `aiosmtplib` (TLS, dedicated SMTP) | |
| Email in | `IMAPClient` polled by Huey (every 30s) | |
| Telegram | `python-telegram-bot` v21 (webhook + polling fallback) | |
| In-app chat | FastAPI WebSocket | |
| Auth | PyJWT + bcrypt direct (4DPocket pattern, NO passlib) | HttpOnly + Secure + SameSite cookies, 15-min access + 7-day refresh rotation |
| PO render | `weasyprint` (HTML→PDF) | fallback `reportlab` |
| Doc parsing | `pymupdf4llm`/`PyMuPDF` (PDF), `python-docx` (Word), `openpyxl` (Excel), `csv` stdlib + sniffer, `bleach` (HTML email sanitize) | |
| Testing | `pytest` + `pytest-asyncio` + `VCR.py` + `aiosmtpd` + `Playwright` + `Vitest` + `httpx` TestClient | |
| Logging | `structlog` JSON | |
| Observability | self-hosted `audit_log` + `llm_cache` tables | no LangSmith |
| Storage | local `data/uploads/<rfx_id>/<vendor_id>/`, behind `StorageService` interface | S3/R2 swap is one file |
| Dev tooling | `uv` (deps), `ruff` (lint+format), `mypy --strict` (typing) | |

### 3.3 Data Model (SQLModel tables, DB-level)

```
User(id, email, password_hash, role[buyer|vendor|admin], display_name,
     telegram_chat_id?, notification_prefs{email, telegram, in_app},
     language_pref[en|hi|hi_en|auto], status[active|suspended|pending],
     created_at, last_login_at, suspended_at?, suspended_by_admin_id?,
     org_id_fk)

Organization(id, name, type[buyer|vendor], gst_number?, address, created_at)

UserDefaults(id, user_id, payment_terms_default, delivery_terms_default,
             quote_validity_days_default, currency_default, tax_treatment_default,
             delivery_window_default, auto_reminder_hours_before_deadline,
             escalation_emails_csv, updated_at)
             # buyer: what they want from vendors
             # vendor: what they typically offer

Category(id, name, sort_order)

SKU(id, org_id, code, name, category_id, unit[kg|g|ltr|ml|pcs|dozen|crate],
    pack_size?, reorder_point, last_price, last_vendor_id?, image_url?,
    aliases_json, gst_pct?)

Vendor(id, owning_buyer_org_id, vendor_user_id, vendor_org_id, name,
       primary_email, telegram_chat_id?, phone?, category_ids_csv,
       performance_score, preferred_rank, kyc_status, created_at)

RFxRun(id, buyer_id, type[RFQ|RFI|RFP], status[drafting|awaiting_approval|
       dispatched|collecting|comparing|awarded|closed|cancelled],
       title, delivery_window_start, delivery_window_end, response_deadline,
       payment_terms_for_this_rfx, delivery_terms_for_this_rfx,
       quote_validity_days_for_this_rfx, currency_for_this_rfx,
       tax_treatment_for_this_rfx, notes_for_vendors,
       cancelled_at?, cancelled_by_user_id?, cancelled_reason?,    # D29 buyer withdraw
       created_at, updated_at)
       # *_for_this_rfx fields default-copied from UserDefaults at draft time,
       # buyer can override during chat ("change validity to 3 days")

RFxLineItem(id, rfx_id, sku_id, qty, unit_override?, target_price?,
            target_lead_time_hours?, notes?)

RFxVendor(id, rfx_id, vendor_id, correlation_token_hash, dispatched_at,
          last_seen_at, status[invited|viewed|quoted|declined|expired],
          decline_reason?, declined_at?,                             # D29 vendor decline
          reminders_sent_json)   # D29: [{slot[T-24h|T-2h|final], sent_at, channel}]

Thread(id, rfx_id, vendor_id, created_at)   # one per (RFx, vendor)

Message(id, thread_id, sender_user_id_or_null, sender_kind[buyer|vendor|system|agent],
        channel[email|telegram|in_app|system], body_text, body_html?,
        raw_payload_json, parent_message_id?, created_at)

Attachment(id, message_id, filename, mime_type, storage_path, size_bytes,
           sha256, extraction_status[pending|extracted|failed],
           extraction_attempts, extracted_at?)

Offer(id, rfx_id, vendor_id,
      line_items_json,        # [{sku_id, qty, unit_price, total, lead_time_hours,
                              #   moq, confidence_per_field{...}}]
      total_quote, currency, lead_time_hours,
      payment_terms, delivery_terms, validity_until,
      tax_treatment, gst_pct?, additional_charges_json,
      vendor_remarks, extraction_confidence_overall,
      source_message_ids_csv, raw_extraction_json, manual_overrides_json,
      revision_no, superseded_by_offer_id?,        # D29 revision history
      is_late,                                     # D31 late-flag
      total_quote_inr,                             # currency-converted via forex_service for matrix sort
      created_at, updated_at)

Award(id, rfx_id, decisions_json,  # [{line_item_id, vendor_id, qty, unit_price}]
      awarded_at, awarded_by_user_id, po_pdf_path?, po_sent_status,
      po_sent_message_ids_csv)

PurchaseOrder(id, award_id, vendor_id, po_number, total_amount,
              currency, terms_json, line_items_json, pdf_path,
              issued_at, signed_at?)

AuditLog(id, actor_user_id, actor_role, action, entity_type, entity_id,
         before_json?, after_json?, ip_address?, user_agent?, created_at)

LLMCache(id, content_hash, provider, model, prompt_hash, response_json,
         input_tokens, output_tokens, latency_ms, created_at)

Notification(id, user_id, channel, subject, body, status[queued|sent|failed],
             related_entity_type, related_entity_id, sent_at?, error?)

# --- Observability / telemetry (D26, see §3.8) ---
LLMCallLog(id, request_id, parent_agent_run_id?, provider, model,
           kind[chat|vision|asr|embedding], prompt_hash, input_tokens, output_tokens,
           total_tokens, cost_estimate_cents, latency_ms, cache_hit, ttfb_ms?,
           finish_reason, error?, created_at)

AgentRunLog(id, agent_name, rfx_id?, thread_id?, user_id?, input_summary,
            output_summary, tool_calls_json, llm_calls_count,
            total_input_tokens, total_output_tokens, total_cost_cents,
            total_latency_ms, status, error?, trace_id, started_at, ended_at)

ChannelEventLog(id, channel, direction, rfx_id?, vendor_id?, message_id?,
                latency_ms, status, error?, payload_size_bytes, created_at)

PipelineReport(id, chat_turn_id, user_id, rfx_id?, agent_run_id,
               total_latency_ms, llm_calls_summary_json, tools_used_json,
               cache_hits, retries, guardrail_blocks, created_at)
```

Seed: 1 buyer org with 40 SKUs across 5 categories, 8 vendor orgs with realistic dark-store-vendor names + emails (FreshFarm Dairy, Sabzi Mandi Co, Bakery Bros, etc.), 3 historical RFx for demo color, demo buyer + vendor users.

### 3.4 Multi-Agent Architecture (mirrors Aera)

```
                                 ┌──────────────────┐
   buyer chat ─────► IntakeAgent ─►  drafts RFx,    │── confirms defaults
                                 │  validates SKUs,  │   from UserDefaults
                                 │  suggests vendors │   ("Use NET30 + 7d
                                 │  per category     │    validity? or
                                 │  + AI clarifies   │    change?")
                                 └────────┬─────────┘
                                          ▼ (approval gate: buyer clicks "Send")
                                 ┌──────────────────┐
                                 │  SourcingAgent   │── proposes dispatch plan:
                                 │  picks channel   │   per vendor (D35), shows
                                 │  per vendor,     │   "Dispatch Plan" card,
                                 │  asks buyer to   │   buyer confirms/overrides,
                                 │  confirm, signs  │   then fan-out + sign tokens
                                 │  token, sends,   │   + schedule reminders
                                 │  schedules       │
                                 │  reminder        │
                                 └────────┬─────────┘
                                          ▼
            ┌──────────── inbound: any channel ─────────┐
            │  email (IMAP)  │  Telegram  │  in-app chat │
            └────────────────────┬──────────────────────┘
                                 ▼
                                 ┌──────────────────┐
                                 │  VendorAgent     │── vendor co-pilot:
                                 │  answers Qs,     │   explains RFx,
                                 │  collects offer, │   prompts missing fields,
                                 │  voice→text      │   asks buyer-side clarifies
                                 └────────┬─────────┘
                                          ▼
                                 ┌──────────────────┐
                                 │ EvaluationAgent  │── format router → extractor
                                 │  multi-attach    │   → fusion → Offer schema
                                 │  fusion + norm   │   → confidence per field
                                 │  units/currency  │
                                 └────────┬─────────┘
                                          ▼
                          ComparisonMatrix (UI) + AwardAction
                                          ▼
                                 ┌──────────────────┐
                                 │   POAgent        │── render PO PDF,
                                 │  (post-award)    │   email awarded vendor(s),
                                 │                  │   record PurchaseOrder
                                 └──────────────────┘
```

**Ship as real**: IntakeAgent, SourcingAgent, VendorAgent, EvaluationAgent, POAgent.
**Stub as "Coming Soon" with placeholder route + no-op `BaseAgent` subclass**: NegotiationAgent, ContractAgent, InvoiceAgent, AnalyticsAgent.

### 3.5 Extractor design (format-agnostic)

| Format | Extractor | Strategy |
|---|---|---|
| PDF (digital, text layer) | `extractors/pdf.py` | `pymupdf4llm` → markdown → LLM normalizer |
| PDF (scanned, no text) | `extractors/pdf.py` (auto-detect) | rasterize page → NIM vision per page → fuse |
| Word `.docx` | `extractors/word.py` | `python-docx` → text + tables → LLM normalizer |
| Word `.doc` (legacy) | `extractors/word.py` | LibreOffice headless to docx → above (fallback: vision on PDF print) |
| Excel `.xlsx`, `.xls` | `extractors/spreadsheet.py` | `openpyxl` → rows + headers → LLM normalizer |
| CSV / TSV | `extractors/spreadsheet.py` | stdlib `csv` + sniffer → LLM normalizer |
| Image (jpg/png/webp) | `extractors/image.py` | NIM vision (`/v1/vision/extract`) → LLM normalizer |
| Email body (HTML) | `extractors/email_body.py` | `bleach` sanitize → readability → strip forwarded chains → LLM normalizer |
| Email body (plain) | `extractors/email_body.py` | strip quoted `>` chains → LLM normalizer |
| Mixed: body + N attachments | `OfferFusionService` | run each extractor, then **fusion LLM call** that takes all snippets + asks "produce one Offer JSON; cite sources" |

**Normalizer** (shared): a single Pydantic-schema'd LLM call (`extract_offer(snippets: list[ExtractionSnippet]) → Offer`) that handles unit/currency/MOQ/validity/payment/delivery extraction with per-field confidence. Uses **gleaning** (4DPocket pattern): second pass that reviews initial output to catch missed fields.

**Unit normalization** (`ai/normalization.py`): kg↔g↔lbs, ltr↔ml, dozen↔pcs, crate→qty-per-crate (looked up via SKU.pack_size). LLM extracts raw; deterministic normalizer converts to SKU canonical unit.

**Currency normalization**: default INR; if vendor quotes in USD/EUR, store both raw + INR-converted using a stub `forex_service` (hardcoded rates for prototype, abstracted for future).

**Per-field confidence** (D33): returned by normalizer LLM as `{field: {value, confidence: 0–1, source: "page 2 line 5"}}`. Shown in ComparisonMatrix as colored badges: <0.7 yellow + "review" CTA, <0.5 red + auto-flag. Overall offer confidence = MIN of all field confidences (worst-link rule); overall <0.5 cannot be awarded without explicit buyer acknowledge.

### 3.6 Omnichannel Reply Routing

Single rule: **any inbound message tagged with a valid signed correlation token routes to its RFx thread.**

- **Token format**: `rfx_<rfx_id>_<vendor_id>_<nonce>` + HMAC-SHA256 base64-url. Verified server-side, replay-protected (nonce stored, single-use for state transitions).
- **Email outbound**: `Reply-To: procurement+<token>@<aeros-domain>`. `Subject: [RFX-<short_id>] <title>`. IMAP poller extracts token from To/Reply chain (regex), falls back to subject short_id.
- **Telegram outbound**: first message includes deep link `https://t.me/<bot>?start=<token>`. `/start` handler binds Telegram `chat_id` to vendor + thread. Subsequent messages route automatically.
- **In-app outbound**: WebSocket push; UI shows thread.

Each channel's inbound handler normalizes to one `Message{thread_id, sender, channel, body, attachments[]}` record. EvaluationAgent runs on the union of attachments + body for that thread, regardless of channel.

**In-app is the canonical thread view (D34).** Regardless of which channel the dispatch went over, the vendor's `/vendor/inbox` always renders the complete thread: every `Message` row for that `(rfx_id, vendor_id)` — including AI co-pilot replies, attachments, and a `ChannelBadge` indicating each message's channel-of-origin. Vendor can always reply in-app even if the invitation arrived via email or Telegram. This is why email-bounce and Telegram-blocked are NOT blocking failure modes for AEROS — the vendor self-serves by logging in. We therefore do not implement bounce-retry, auto-channel-switching, or out-of-office detection.

### 3.7 Observability & Statistics layer (D26 — memo.sbs-style)

A first-class telemetry layer captures every AI call, every agent run, every channel event, and surfaces them to (a) the developer (logs + admin dashboard) and (b) the buyer (per-chat pipeline report + activity timeline). Aggregate stats live on an Observability dashboard.

**Telemetry tables** (additions to §3.3):

```
LLMCallLog(id, request_id, parent_agent_run_id?, provider, model, kind[chat|vision|asr|embedding],
           prompt_hash, input_tokens, output_tokens, total_tokens, cost_estimate_cents,
           latency_ms, cache_hit, ttfb_ms?, finish_reason, error?, created_at)

AgentRunLog(id, agent_name, rfx_id?, thread_id?, user_id?, input_summary,
            output_summary, tool_calls_json,    # list of {name, args, result_summary, latency_ms}
            llm_calls_count, total_input_tokens, total_output_tokens, total_cost_cents,
            total_latency_ms, status[success|partial|failed], error?,
            trace_id, started_at, ended_at)

ChannelEventLog(id, channel[email|telegram|in_app], direction[out|in], rfx_id?,
                vendor_id?, message_id?, latency_ms, status, error?, payload_size_bytes,
                created_at)

PipelineReport(id, chat_turn_id, user_id, rfx_id?, agent_run_id, total_latency_ms,
               llm_calls_summary_json,   # [{model, tokens, latency}]
               tools_used_json,          # [{name, latency_ms, success}]
               cache_hits, retries, guardrail_blocks, created_at)
```

**Per-LLM-call instrumentation**: `ChatProvider.generate(...)` wrapped with a decorator that captures provider, model, tokens (from API response), latency (timer), cost estimate (from a per-model price table in `ai/pricing.py`), cache hit/miss, and writes an `LLMCallLog` row. Failures captured with truncated error string.

**Per-agent-run instrumentation**: `BaseAgent.run(ctx, input)` wrapped in a context manager that starts a span (`trace_id` UUID), records every nested LLM call + tool call against the parent `AgentRunLog`, and finalizes status. Trace IDs propagate through Huey task headers.

**Per-channel-event instrumentation**: `channels/*.py` dispatch and inbound parse functions log `ChannelEventLog` (outbound = send, inbound = parsed-and-routed). Surfaces SMTP failures, IMAP poll lag, Telegram webhook latency.

**Per-chat pipeline report** (the memo.sbs moment): each buyer/vendor chat turn returns a JSON pipeline report alongside the agent response. The UI shows it as a collapsible "Inspect" panel under the message bubble:

```
Inspect this turn
  ├─ 2.3 s  total
  ├─ LLM calls       3
  │   ├─ nim:llama-3.1-nemotron-70b   ↓ 1842 ↑ 142 tok  •  920 ms
  │   ├─ nim:llama-3.1-nemotron-70b   ↓ 2031 ↑ 87  tok  •  840 ms  (cache miss)
  │   └─ nim:neva-22b  (vision)        ↓ image       •  510 ms
  ├─ Tools fired     2
  │   ├─ inventory.lookup_skus              ✓ 12 ms
  │   └─ vendors.suggest_for_category       ✓ 45 ms
  ├─ Guardrails      input ✓ · output ✓ · intent ✓
  ├─ Cost            ₹0.34
  └─ Cache           2 hits / 1 miss
```

**Aggregate stats dashboard** (buyer-admin route `/buyer/observability`):

- **Cards (last 24h)**: total LLM calls, total tokens, total cost, p50 / p95 / p99 latency, cache hit rate, error rate, guardrail-blocks, RFx dispatched, offers extracted.
- **Charts**: calls-per-hour, tokens-per-hour, cost-per-hour (stacked by model), latency distribution (histogram), error rate over time.
- **Tables**: top-N agents by cost, top-N models by usage, top-N RFx by AI cost, recent failures with trace_id link.
- **Per-RFx Timeline**: visual swimlane (buyer agent, sourcing, vendor A, vendor B, vendor C, eval, PO) showing every event with timestamps. Click an event → drill into its `AgentRunLog` + nested `LLMCallLog` rows.

**System metrics** (HTTP + DB + workers): `structlog` JSON logs include `request_id`, `trace_id`, `user_id`, `route`, `status`, `latency_ms`. Optional Prometheus exporter at `/metrics` (planned, low priority).

**Frontend telemetry**: tiny client-side beacon (`/api/telemetry/client`) for unhandled JS errors + route timings. Privacy-respecting (no PII).

**Retention**: `LLMCallLog` + `AgentRunLog` + `ChannelEventLog` retained 30 days (configurable); `PipelineReport` kept alongside its `Message` (lifetime same as RFx, 7y default per §4.3).

**Cost model** (`ai/pricing.py`): per-model price table (input + output token rates). NIM free tier modeled at 0 with a flag, so the dashboard works realistically when the user switches to a paid provider.

**Tests added** (§7.3): `test_llm_call_log_decorator.py`, `test_agent_run_log_context.py`, `test_pipeline_report_attached_to_chat.py`, `test_observability_dashboard_aggregations.py`, `test_channel_event_log.py`, `test_log_redaction_in_telemetry.py` (no secrets/PII in telemetry rows).

### 3.8 Admin Module + 3-tier RBAC (D27 — memo.sbs-style)

**Three roles**, hierarchical permissions:

| Role | Can do | Can NOT do |
|---|---|---|
| **Vendor** | View own threads, reply to RFx in own threads, upload, manage own profile + defaults, voice input, see own observability (own pipeline reports) | View other vendors' threads, view buyer-org internals, change model config, see audit log beyond own actions |
| **Buyer** | Everything in own buyer-org scope: inventory, vendors, draft + dispatch + award RFx, comparison matrix, override extractions, see own + buyer-org observability, audit log scoped to own org | Cross-org reads, manage models/providers, manage other users, suspend users, see vendor's internal defaults beyond what's in the RFx |
| **Admin** | Everything: cross-tenant observability, model/provider config (DB-backed), user management (list/create/suspend/role-change), system settings (retention, rate limits, AI budget caps), full audit log, vendor KYC approval, manual PII redaction triggers | Bypass tested safety controls (correlation tokens, append-only audit, encryption-at-rest envelope still apply) |

**Enforcement (defence in depth, 3 layers — all tested):**

1. **Router layer**: every endpoint declares `required_role: list[Role]` via FastAPI dependency `require_role(*roles)`. Returns 403 with audit log entry.
2. **Service layer**: every service method takes a `caller: AuthContext` and re-checks role + org scope before any DB hit. Tests assert that bypassing the router (e.g. via direct service import) still rejects.
3. **DB-query layer**: helper `for_user(caller)` builds query filters by role — buyers see only own-org rows, vendors see only own-thread rows, admins see all. Used as a wrapper on every list/get query (`select(Offer).where(*for_user(caller, Offer))`). Tests assert that omitting the wrapper raises a `MissingAuthFilter` lint error.

**Admin patterns adopted from memo.sbs** (`/Users/prakersh/projects/memo.sbs/src/ai/providers.py` + admin pages):

- **DB-backed AI provider config**: `AIProviderConfig(provider, model, enabled, is_default, context_window, max_output_tokens, cost_per_1k_input, cost_per_1k_output, base_url_override?, api_key_env_var, created_by_admin_id, updated_at)`. `.env` provides initial defaults; admin panel can override per provider/model at runtime. `ai/factory.py` reads from DB first, falls back to env.
- **Runtime toggle**: admin can disable a misbehaving model in one click; agents fall through to the next enabled model.
- **Per-model token cap & cost budget**: live-editable. Breach triggers circuit breaker (§2 D24 / P2.9) — agents return a polite error and admin gets an alert.
- **Knowledge Hub-style settings page**: AI config + system settings (retention days, rate limits, AI budget caps) under one `/admin/settings`.

**Admin shell** (`/admin/*`, separate from `/buyer` and `/vendor`):

- `/admin/dashboard` — KPIs across all orgs (RFx count, offers extracted, cost, error rate, p95 latency).
- `/admin/users` — list/filter/create/suspend/role-change/reset-password; force-logout.
- `/admin/orgs` — list buyer + vendor organizations.
- `/admin/vendors/kyc` — approve/reject vendor KYC (`Vendor.kyc_status` flow).
- `/admin/ai/providers` — DB-backed provider + model config table.
- `/admin/ai/budgets` — per-user + per-RFx token caps; circuit-breaker tuning.
- `/admin/settings` — retention, rate limits, CORS allow-list, JWT TTLs, log redaction patterns.
- `/admin/observability` — superset of buyer observability: cross-tenant, full trace_id drill-down.
- `/admin/audit` — full immutable audit log view + export.
- `/admin/incidents` — runbook actions (revoke token, force-rotate HMAC secret, replay failed Huey tasks).

**Bootstrap**: first migration creates a single `admin@aeros.local` seeded user with a random password printed to stdout on first run and immediately rotated via the admin panel.

**Audit**: every admin action writes `AuditLog` with `actor_role=admin` and is non-redactable (admin actions are always preserved for compliance).

**Security note**: admin role does NOT grant power to silently read vendor↔buyer chat content beyond what's stored as data — even admins viewing a thread create an audit entry visible to the parties involved (transparency over surveillance).

**New tables** (added to §3.3):

```
AIProviderConfig(id, provider, model, kind[chat|vision|asr|embedding],
                 enabled, is_default, context_window, max_output_tokens,
                 cost_per_1k_input_cents, cost_per_1k_output_cents,
                 base_url_override?, api_key_env_var, created_by_admin_id,
                 created_at, updated_at)

SystemSetting(key, value_json, updated_by_admin_id, updated_at)
              # retention_days_telemetry, retention_days_audit, rate_limit_chat_per_min,
              # ai_budget_per_user_daily_cents, ai_budget_per_rfx_cents,
              # cors_allowed_origins_csv, jwt_access_ttl_min, jwt_refresh_ttl_days,
              # log_redaction_patterns_json, ...
```

### 3.9 User Profile Defaults + AI Confirmation (D16)

**`UserDefaults` table** seeded on user creation with sensible defaults:

Buyer defaults (example): `payment_terms=NET30`, `delivery_terms=doorstep`, `quote_validity_days=7`, `currency=INR`, `tax_treatment=exclusive`, `delivery_window=05:00–07:00`, `auto_reminder_hours=12`.

Vendor defaults (example): `payment_terms_offered=[NET15, NET30, advance]`, `delivery_terms_offered=[doorstep, ex-warehouse]`, `validity_days_offered=5`.

**Edit anytime**: `/buyer/settings/defaults` and `/vendor/profile` pages with forms.

**AI confirmation pattern** (IntakeAgent during chat):

1. After capturing line items + delivery window, IntakeAgent reads `UserDefaults` via Context.
2. Agent shows inline "Terms" chip card with current defaults visible in chat:
   > "I'll dispatch with your standard terms: **NET30**, **doorstep**, **7-day validity**, **INR**, **tax-exclusive**. Want to change any of these for this RFx? Reply or click to edit."
3. Buyer can chat (`"change validity to 3 days"`) or click-edit (UI exposes the chip as editable). Agent uses a tool call `set_rfx_terms(overrides)` to apply.
4. Agent shows updated chip + asks for final confirmation before SourcingAgent fires.

Vendor side: VendorAgent reads vendor's `UserDefaults` and pre-fills the quote with vendor's standard terms; vendor can adjust per RFx.

### 3.10 Realistic procurement flows (D29)

Beyond the happy path, the demo must handle these four flows. Each is small (≤1 model field + 1 service method + 1 UI element + 1 test) but visible.

**Vendor decline.** `/vendor/rfx/<id>` has a **"Decline this RFx"** button next to the reply chat. Click → modal collects a reason (free-text + category dropdown: out-of-stock / pricing / capacity / other). Submit → `VendorAgent.decline_rfx(reason)` tool call → `RFxVendor.status='declined'`, `decline_reason`, `declined_at` set, AuditLog entry. Buyer's ComparisonMatrix renders a **"Declined"** tile with the reason in that vendor's lane (no offer card). Counts toward `Vendor.performance_score` as a response (not a lost-sale).

**Buyer withdraw / cancel RFx.** `/buyer/rfx/<id>` header has a **"Withdraw RFx"** action. Click → confirmation modal lists invited vendors + asks for an optional reason. Submit → `RFxService.cancel(reason, by_user)` → `RFxRun.status='cancelled'`, `cancelled_at/by/reason` set, a system `Message` ("Buyer has withdrawn this RFx") is fanned out to every `RFxVendor` thread on each vendor's preferred channel, further extraction on incoming attachments for this RFx is disabled. Fully audited.

**Offer revisions.** A vendor who has already submitted may resubmit before `response_deadline`. Each resubmit creates a **new** `Offer` row with `revision_no = prev + 1` and the prior row's `superseded_by_offer_id` set to the new id (so revision history is preserved, not lost). ComparisonMatrix shows the latest by default with a small **"v2 / v3"** badge; a hover-toggle reveals prior revisions side-by-side. Any buyer override on a prior revision is migrated forward to the latest revision (audited).

**Multi-stage reminders.** `RFxVendor.reminders_sent_json` is an append-only array of `{slot: 'T-24h' | 'T-2h' | 'final', sent_at, channel}`. The reminder worker scans every 5 min; for each unsent slot whose trigger time has passed (relative to `response_deadline`), it sends via vendor's preferred channel (falls through to next preference on failure) and appends to the array. Per-slot idempotency is enforced by the array — a slot never fires twice even on worker crash + restart.

---

## 4. Security, Guardrails & Compliance (hard requirement — non-negotiable)

### 4.1 Application security baseline (OWASP Top 10 aligned)

| Area | Control | Tests |
|---|---|---|
| Auth (A07) | bcrypt cost 12, PyJWT direct, HttpOnly+Secure+SameSite cookie, 15-min access + 7-day refresh rotation, lockout after 5 fails | `test_auth_service.py`, `test_api_auth.py` |
| CSRF (A01) | Double-submit cookie on state-changing requests; SameSite=Lax | `test_security_csrf.py` |
| RBAC (A01) | **3-tier (buyer/vendor/admin)**. Every route declares `require_role(*roles)` via FastAPI dep; service layer re-checks; DB-query layer wraps every list/get with `for_user(caller)` scope filter. `MissingAuthFilter` lint blocks unscoped queries at CI. Cross-vendor + cross-org access proven impossible | `test_security_rbac.py`, `test_admin_rbac.py`, `test_db_query_scope_filter.py` |
| Correlation tokens | HMAC-SHA256 signed, single-use nonce, replay-protected, hashed in DB, never logged | `test_correlation_hmac.py`, `test_security_token_replay.py` |
| Upload safety (A03/A04) | Server-side MIME sniff via magic bytes, 25 MB cap, extension+magic must agree, filename sanitized, separate origin path, `Content-Disposition: attachment`, virus-scan hook (clamav optional) | `test_security_upload_mime_spoof.py`, `test_file_service_mime_sniff.py` |
| Injection (A03) | Parameterized queries only (SQLModel/SQLAlchemy); HTML email sanitized via `bleach`; no `eval`/`exec` anywhere | `test_security_sqli.py`, `test_security_xss.py` |
| IMAP/SMTP | TLS-only, creds from env, SMTP rate-limit per minute, SPF/DKIM headers respected | `test_email_*` |
| Telegram | Webhook secret token verified on every callback, chat_id binding requires valid correlation token + nonce | `test_telegram_*` |
| Secrets (A05) | Nothing committed; `.env.example` only; pre-commit hook scans for secret patterns (regex + entropy) | `test_no_secrets_in_repo.py` |
| AI cost cap | Per-RFx token budget + circuit-breaker via `llm_cache`; per-user daily cap | `test_llm_cache.py`, `test_ai_cost_cap.py` |
| Audit (A09) | Every state-changing action writes `AuditLog` (actor, action, before/after, IP, UA); append-only enforced at DB level | `test_audit_service.py` |
| Rate-limit (A04) | `slowapi` on auth/chat/upload/inbound endpoints; per-IP + per-user | `test_rate_limit.py` |
| CORS (A05) | Explicit allow-list, credentials only for known origins | `test_cors.py` |
| PII | Vendor contact info gated by buyer-org membership; vendors see only their own threads; logs use IDs not bodies | `test_security_pii.py` |
| HTTP headers (A05) | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, strict CSP (script-src self) | `test_security_headers.py` |
| Logging (A09) | `structlog` JSON; redactor middleware strips secrets/tokens/PII; never log full message bodies, only IDs + hashes | `test_log_redaction.py` |
| Dep scanning (A06) | `pip-audit` + `npm audit` in CI; `safety` for Python | CI job |
| Crypto (A02) | TLS 1.2+ only, no MD5/SHA1, HMAC-SHA256 for tokens, bcrypt for passwords | static-check |

### 4.2 AI Guardrails (input + output + behavior)

| Layer | Control | Implementation |
|---|---|---|
| **Input — system prompts** | All system prompts versioned in `ai/prompts/` as constants; reviewed before merge; never user-controlled | unit tests assert immutability + content checksum |
| **Input — user content boundary** | Every untrusted input (vendor message, buyer free text, extracted doc content) wrapped in explicit delimiters with instructions to the LLM that content inside is **data, not instructions** | `prompts/wrap.py` `wrap_untrusted(text, kind)` helper |
| **Input — content classifier** | Lightweight pre-filter (regex + keyword) rejects obvious jailbreak patterns ("ignore previous", "you are now", "system:", "</system>", "DAN", base64-encoded instruction blocks, prompt-leak attempts) before reaching the main LLM | `ai/guardrails/input_filter.py` + `test_guardrails_input.py` |
| **Input — dual-LLM evaluator (high-risk paths)** | For tool-calling decisions that produce side effects (dispatch RFx, send email, award PO), a small evaluator LLM call validates the intent against the raw user message. Mismatch → human-in-loop | `ai/guardrails/intent_validator.py` + `test_guardrails_intent.py` |
| **Output — schema validation** | Every LLM output that drives an action is parsed against a Pydantic schema; validation failure → retry once with stricter prompt → fail closed (refuse) | enforced in every agent |
| **Output — action allow-list** | LLM tool calls restricted to a fixed enum of named tools; unknown tool name → reject without execution | `agents/base.py` `Tool.registry` |
| **Output — content filter** | Output passed through a redactor that strips email addresses, phone numbers, credit-card patterns, API-key patterns before display | `ai/guardrails/output_filter.py` |
| **Output — refusal patterns** | If the model is asked to do anything outside procurement scope, system prompt directs it to refuse politely and stay on task; tested with off-topic prompts | `test_guardrails_refusal.py` |
| **Behavior — confirmation gate** | High-stakes actions (Send to vendors, Award) require explicit buyer click — never auto-executed even if AI suggests | UI + backend enforced |
| **Behavior — tool-call audit** | Every tool call logged with input + output + actor; surfaced in Activity panel | `audit_service.py` |
| **Behavior — cost circuit-breaker** | Per-RFx + per-user token budget; breached → AI loop halts and asks buyer | `services/ai_budget_service.py` |
| **Behavior — vendor-side isolation** | VendorAgent's tools cannot touch other vendors' threads, cannot read buyer defaults beyond what was sent in the RFx; tested | `test_security_rbac.py` |
| **Cross-prompt-injection (the big one)** | Vendor-supplied extracted content (PDF text, image OCR, email body) **never** passes through to the buyer's chat as instructions. EvaluationAgent runs in an isolated context with its own system prompt and outputs only structured `Offer` JSON. The Offer JSON is then displayed in the comparison matrix, **not fed back as a string into the buyer's chat history**. | architectural separation + `test_security_cross_prompt_injection.py` |

### 4.3 Production/Compliance design (SOC2-leaning, even pre-certification)

| Area | Design |
|---|---|
| **Data classification** | `data_classification` column tag on every model row (`public`, `internal`, `confidential`, `pii`); enforced by query helpers + tests |
| **Encryption at rest** | DB filesystem encryption (OS-level or LUKS in prod); uploaded files stored with per-tenant encryption envelope (libsodium); secrets via env, never in DB |
| **Encryption in transit** | TLS 1.2+ for all external traffic; internal services on private network in prod |
| **Access logging** | Every API hit logs (timestamp, actor, path, status, latency); immutable retention 90 days |
| **Audit immutability** | `AuditLog` table append-only enforced via DB trigger; periodic hash-chain checksum to detect tampering |
| **Data retention** | Configurable per entity; default: RFx 7y, AuditLog 7y, Message 7y, Notification 90d, LLMCache 30d; documented in `SECURITY.md` |
| **Right-to-delete / GDPR readiness** | User-soft-delete + redaction worker that scrubs PII on request; tested |
| **Backups** | Plan documents nightly DB + filesystem backups in prod (out of scope for prototype, but documented) |
| **Vendor risk** | NIM, Groq, SMTP provider listed in `SECURITY.md` with data-flow diagram |
| **Incident response** | `SECURITY.md` lists runbook entries: leaked token, prompt-injection breakthrough, SMTP credentials compromised |
| **Change management** | Every merge requires green CI: ruff + mypy --strict + pytest + Playwright + dep-audit + secret-scan |
| **Least privilege** | DB user has only required grants; production secrets never in dev env |
| **Vulnerability disclosure** | `SECURITY.md` includes contact + policy |

### 4.4 TDD as a primary, non-negotiable discipline

**Rule: no implementation code is committed without a failing test that motivates it. CI fails any merge that decreases coverage.**

- **Pre-commit hook**: blocks commits where new `.py` files lack corresponding `tests/unit/test_*.py` or where coverage on the touched file falls below threshold.
- **Sequence per packet** (enforced via PR template):
  1. Define Pydantic schema + write round-trip unit test.
  2. Write failing unit test for the service interface.
  3. Implement minimum code to pass.
  4. Refactor.
  5. Write failing integration test (with VCR cassette for AI calls).
  6. Wire glue.
  7. Write failing E2E (Playwright) test for user-visible behavior.
  8. Wire UI.
- **Test categories required for every agent / service / channel / extractor**:
  - Happy path
  - At least 2 error paths
  - 1 security/guardrail test (injection, role bypass, malformed input)
  - 1 idempotency test (where applicable)
- **Coverage gates** (CI-enforced):
  - Backend overall: ≥80% line, ≥75% branch
  - `agents/`, `ai/guardrails/`, `security/`, `channels/correlation.py`: 100% line
  - Frontend `components/ComparisonMatrix`, `components/Chat/*`, `components/UploadZone`: ≥90% statements
- **Mutation testing (stretch)**: `mutmut` over `agents/` and `security/` in CI weekly.
- **Property-based tests**: `hypothesis` for `ai/normalization.py` (units/currency) and `channels/correlation.py` (HMAC round-trip).
- **Test fixtures versioned**: every `fixtures/sample_offers/*` file is checked in; VCR cassettes checked in; re-record gated behind `RECORD_VCR=1`.
- **Demo-day insurance**: full suite must be green and a recorded 60-second loom of the demo is captured as backup.

---

## 5. Frontend (`/ui-ux-pro-max` skill during impl)

Two role-aware shells sharing components:

**Buyer shell** (`/buyer`):
- **Dashboard** — open RFx tiles (status, vendor count, time-to-quote), recent activity, "Draft new request" CTA, KPI cards (open RFx, awaiting quotes, awarded today).
- **Chat co-pilot** (headline) — full-page conversation with IntakeAgent. SSE streams. Inline cards: detected SKU pulls from inventory, suggested vendors, draft preview, **Terms chip** (D16 confirmation). Mic button → Groq Whisper → transcript injected. "Approve & Send" gate.
- **Inventory** — SKU table with categories, last price, reorder points, aliases. Inline edit.
- **Vendors** — directory grouped by category, per-vendor performance, preferred rank drag-handle, last-contact, response-rate.
- **RFx detail** — header (status, delivery window, deadline countdown, **Withdraw RFx** action with confirmation modal), per-vendor lanes showing every Message with **ChannelBadge** (email/telegram/in-app), Offer card per vendor as it arrives with **revision badge** (v2/v3) and **late badge** if applicable, **ComparisonMatrix** (side-by-side, sortable, lowest-price/best-lead-time highlights, per-field confidence badges with <0.7 yellow / <0.5 red auto-flag, manual override pencil, **per-line-item Award** with split-award support). Declined vendors render as "Declined" tiles with reason instead of offer card.
- **Settings → Defaults** — form for `UserDefaults`.
- **Activity** — audit log feed.
- **Coming-Soon tabs**: Negotiation, Contract, Invoice, Analytics (placeholder with mocked screenshot).

**Vendor shell** (`/vendor`):
- **Inbox** — list of RFx received, status, deadline countdown.
- **RFx detail + Reply chat** — full thread visible (all messages from all channels merged per D34, with ChannelBadge per message), VendorAgent co-pilot walks vendor through the quote ("here's what they need: 150kg tomatoes…; paste your prices or drop a file"), upload zone (PDF/Word/Excel/CSV/image), submit button (resubmit creates a new revision per D29), extraction-status badge, **mic button** (D9), **"Decline this RFx"** action with reason modal.
- **Profile** — categories served, notification prefs (email/Telegram toggles, Telegram bind via deep-link button), **Defaults form**.

**Admin shell** (`/admin`, D27):
- **Dashboard** — cross-tenant KPIs (RFx count, offers extracted, cost, latency, error rate).
- **Users** — list/filter/create/suspend/role-change/reset-password/force-logout.
- **Orgs** — buyer + vendor organizations.
- **Vendors → KYC** — approve/reject vendor KYC (`Vendor.kyc_status`).
- **AI → Providers** — DB-backed model config: toggle, set default, per-model token cap.
- **AI → Budgets** — per-user + per-RFx caps, circuit-breaker tuning.
- **Settings** — retention, rate limits, CORS, JWT TTLs, log redaction patterns.
- **Observability** — superset of buyer observability: cross-tenant + trace drill-down.
- **Audit** — full immutable log + CSV export.
- **Incidents** — runbook actions (revoke token, rotate HMAC, replay failed Huey tasks).

**Shared**: login/register, role-aware redirect (`/buyer` | `/vendor` | `/admin`), dark-mode-friendly Tailwind theme, Command Palette (Cmd+K), Toaster (sonner-style), responsive (≥1024px primary, ≥390px functional).

**UX language**: code-switching aware — UI strings in English, but chat responses follow `User.language_pref`. Voice transcripts auto-detect.

---

## 6. File Tree (project root `/Users/prakersh/projects/aerchain/`)

```
aerchain/
├── IMPLMENTETION_PLAN_CONTEXT.md       # mirror of this plan file
├── README.md
├── ARCHITECTURE.md
├── SECURITY.md
├── DEMO_SCRIPT.md
├── pyproject.toml
├── alembic.ini
├── app.sh                              # lifecycle (4DPocket pattern)
├── docker-compose.yml                  # optional, for MailHog + later PG
├── .env.example
├── src/aeros/
│   ├── main.py                         # FastAPI app, routers, WS, lifespan
│   ├── config.py                       # pydantic-settings
│   ├── db.py                           # engine, session, registry
│   ├── api/
│   │   ├── auth.py                     # /api/auth/{login,register,logout,me,refresh}
│   │   ├── buyer.py                    # /api/buyer/{inventory,vendors,rfx,defaults,activity}
│   │   ├── vendor.py                   # /api/vendor/{inbox,reply,upload,profile,defaults}
│   │   ├── admin.py                    # /api/admin/{users,orgs,vendors/kyc,ai/providers,ai/budgets,settings,observability,audit,incidents}
│   │   ├── chat.py                     # POST /api/chat (SSE) + WS /ws/chat
│   │   ├── inbound_email.py            # /api/webhooks/email-imap-trigger (manual replay)
│   │   ├── inbound_telegram.py         # /api/webhooks/telegram + /api/test/telegram-fake (dev)
│   │   ├── files.py                    # /api/files/<id> (signed, role-gated)
│   │   └── po.py                       # /api/buyer/award/<id>/po (download)
│   ├── agents/
│   │   ├── base.py                     # BaseAgent ABC, AgentContext, AgentResult
│   │   ├── intake.py                   # IntakeAgent (buyer chat → RFxDraft + defaults confirm)
│   │   ├── sourcing.py                 # SourcingAgent (compose + dispatch + schedule reminder)
│   │   ├── vendor_copilot.py           # VendorAgent (vendor chat + collect + clarify-with-buyer)
│   │   ├── evaluation.py               # EvaluationAgent (multimodal fusion → Offer)
│   │   ├── po.py                       # POAgent (render + email PO)
│   │   └── _stubs/                     # NegotiationAgent, ContractAgent, InvoiceAgent, AnalyticsAgent
│   ├── ai/
│   │   ├── base.py                     # ChatProvider, EmbeddingProvider, VisionProvider, ASRProvider protocols
│   │   ├── factory.py                  # get_chat_provider / vision / asr / embedding
│   │   ├── openai_compatible.py        # NIM / OpenAI-compat impl
│   │   ├── anthropic_compatible.py     # Anthropic-compat impl (Bedrock, Vertex, native)
│   │   ├── nim_vision.py               # NIM /v1/vision/extract + image-url fallback
│   │   ├── groq_asr.py                 # Whisper transcribe
│   │   ├── llm_cache.py                # content-hash response cache
│   │   ├── pricing.py                  # per-model input/output token rates → cost_estimate
│   │   ├── schemas.py                  # Pydantic: Offer, LineItem, RFxDraft, ExtractionSnippet, ChatTurn
│   │   ├── normalization.py            # unit + currency converters
│   │   ├── extractors/
│   │   │   ├── router.py
│   │   │   ├── pdf.py
│   │   │   ├── word.py
│   │   │   ├── spreadsheet.py          # xlsx + csv + tsv
│   │   │   ├── image.py
│   │   │   └── email_body.py
│   │   ├── prompts/                    # system prompts as .py constants
│   │   │   ├── intake.py sourcing.py vendor.py evaluation.py po.py
│   │   │   ├── wrap.py                 # wrap_untrusted(text, kind) → delimiter-bound
│   │   │   └── _checksums.py           # immutability assertion hashes
│   │   └── guardrails/
│   │       ├── input_filter.py         # jailbreak regex + keyword pre-filter
│   │       ├── intent_validator.py     # dual-LLM intent check for high-stakes actions
│   │       ├── output_filter.py        # PII / secret redaction on LLM output
│   │       └── action_allowlist.py     # named-tool registry; unknown → reject
│   ├── channels/
│   │   ├── email_out.py                # aiosmtplib + token in Reply-To
│   │   ├── email_in.py                 # IMAPClient poller (Huey task)
│   │   ├── telegram_bot.py             # python-telegram-bot + /start <token>
│   │   ├── in_app.py                   # WS broadcast helpers
│   │   ├── correlation.py              # HMAC sign/verify
│   │   └── notifications.py            # fan-out service
│   ├── models/                         # SQLModel tables
│   │   ├── user.py vendor.py sku.py rfx.py message.py
│   │   ├── offer.py award.py po.py audit.py llm_cache.py
│   │   └── user_defaults.py notification.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── inventory_service.py
│   │   ├── vendor_service.py
│   │   ├── rfx_service.py              # state machine transitions + audit hooks
│   │   ├── thread_service.py
│   │   ├── offer_service.py
│   │   ├── offer_fusion_service.py     # multi-attachment fusion per message
│   │   ├── file_service.py             # mime-sniff, magic, size, virus hook
│   │   ├── audit_service.py
│   │   ├── defaults_service.py         # UserDefaults CRUD + merging into RFx
│   │   ├── po_service.py               # PO render + dispatch
│   │   ├── reminder_service.py         # scheduled vendor reminders
│   │   ├── ai_budget_service.py        # per-RFx + per-user token cap + circuit breaker
│   │   ├── telemetry_service.py        # write LLMCallLog / AgentRunLog / ChannelEventLog / PipelineReport
│   │   ├── observability_service.py    # aggregations for dashboard (cards, charts, tables, timeline)
│   │   ├── admin_service.py            # user mgmt: list/create/suspend/role-change/reset/force-logout
│   │   ├── ai_config_service.py        # DB-backed AIProviderConfig CRUD (memo.sbs-style)
│   │   ├── system_settings_service.py  # CRUD on SystemSetting (retention, rate limits, budgets, CORS, ...)
│   │   └── forex_service.py            # stub rates
│   ├── workers/
│   │   ├── huey_app.py
│   │   ├── imap_poll.py
│   │   ├── extract_offer.py
│   │   ├── notifications.py
│   │   ├── reminders.py
│   │   └── po_render.py
│   ├── security/
│   │   ├── hmac.py jwt.py csrf.py rate_limit.py headers.py
│   ├── storage/
│   │   └── local.py
│   └── seed/
│       └── dark_store.py               # 1 buyer org + 40 SKUs + 8 vendors + 3 historical RFx
├── frontend/
│   ├── package.json
│   ├── vite.config.ts tailwind.config.ts tsconfig.json
│   ├── src/
│   │   ├── main.tsx App.tsx routes.tsx
│   │   ├── pages/
│   │   │   ├── auth/{Login,Register,VendorOnboarding}.tsx
│   │   │   ├── buyer/{Dashboard,ChatCopilot,Inventory,Vendors,RFxDetail,Settings,Activity,Observability,*ComingSoon}.tsx
│   │   │   ├── vendor/{Inbox,RFxReply,Profile}.tsx
│   │   │   └── admin/{Dashboard,Users,Orgs,VendorsKYC,AIProviders,AIBudgets,Settings,Observability,Audit,Incidents}.tsx
│   │   ├── components/
│   │   │   ├── Chat/{ChatStream,ChatInput,MicButton,TermsChip,SuggestedVendorsCard,DraftPreview}.tsx
│   │   │   ├── ComparisonMatrix.tsx
│   │   │   ├── RFxCard.tsx ThreadView.tsx ChannelBadge.tsx ConfidenceBadge.tsx
│   │   │   ├── UploadZone.tsx CommandPalette.tsx ToastHost.tsx
│   │   │   ├── InspectPanel.tsx        # memo.sbs-style per-chat pipeline report
│   │   │   ├── ObservabilityCards.tsx ObservabilityCharts.tsx TraceDrillDown.tsx
│   │   │   └── layouts/{BuyerShell,VendorShell,AdminShell,AuthShell}.tsx
│   │   ├── hooks/{useSSE,useWS,useAuth,useChatStream,useUpload,useVoice}.ts
│   │   ├── api/{client.ts,buyer.ts,vendor.ts,chat.ts,files.ts}.ts
│   │   └── stores/{auth,chatDraft,ui}.ts
│   └── e2e/                            # Playwright specs (see §7)
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/                            # backend-side e2e harness, calls frontend e2e
│   └── fixtures/
│       ├── sample_offers/
│       │   ├── acme_dairy.pdf (digital)
│       │   ├── freshfarm_rates.xlsx
│       │   ├── kirana_proforma.jpg (photographed)
│       │   ├── sabzi_scan.pdf (scanned)
│       │   ├── bakery_quote.docx
│       │   ├── greens_csv.csv
│       │   └── mailbody.txt (forwarded chain)
│       └── vcr/                        # NIM/Groq cassettes
└── docs/
    ├── ARCHITECTURE.md
    ├── SECURITY.md
    ├── DEMO_SCRIPT.md
    └── API.md
```

---

## 7. TDD Plan

### 7.1 Cadence per module

1. Pydantic schema + round-trip unit test.
2. Service interface + failing unit test.
3. Implementation. Test passes.
4. Integration test (DB + provider via VCR cassette). Failing → glue → passing.
5. E2E spec (Playwright). Failing → wire UI → passing.

### 7.2 Coverage targets

- Backend: ≥80% line coverage (`pytest --cov=src/aeros --cov-fail-under=80`).
- Agents: 100% covered for happy + 2 error paths.
- Frontend: component-level Vitest for ChatStream, ComparisonMatrix, TermsChip, UploadZone, MicButton; full flows in Playwright.
- VCR cassettes for every NIM/Groq call; replay-by-default, opt-in re-record via `RECORD_VCR=1 pytest`.

### 7.3 Test suite layout

```
tests/unit/
  test_chat_provider_protocol.py
  test_nim_openai_compat.py                # VCR
  test_anthropic_compat.py                 # VCR
  test_groq_whisper.py                     # VCR
  test_correlation_hmac.py                 # + hypothesis property-based
  test_normalization_units.py              # + hypothesis
  test_normalization_currency.py           # + hypothesis
  test_extractor_pdf_digital.py
  test_extractor_pdf_scanned.py
  test_extractor_word.py
  test_extractor_spreadsheet.py
  test_extractor_image.py
  test_extractor_email_body.py
  test_offer_fusion_service.py
  test_intake_agent.py
  test_sourcing_agent.py
  test_vendor_agent.py
  test_evaluation_agent.py
  test_po_agent.py
  test_rfx_state_machine.py
  test_defaults_service.py
  test_auth_service.py
  test_audit_service.py
  test_reminder_service.py
  test_file_service_mime_sniff.py
  # --- AI guardrails ---
  test_guardrails_input.py                 # jailbreak/prompt-leak detection
  test_guardrails_intent.py                # dual-LLM intent validator
  test_guardrails_output.py                # PII/secret redaction
  test_guardrails_refusal.py               # off-topic rejection
  test_guardrails_action_allowlist.py      # unknown tool name rejected
  test_prompt_immutability.py              # system-prompt checksums
  test_ai_budget_service.py                # token cap + circuit breaker
  # --- App security ---
  test_log_redaction.py
  test_security_headers.py
  test_security_csrf.py
  test_rate_limit.py
  test_cors.py
  test_no_secrets_in_repo.py               # regex+entropy scan

tests/integration/
  test_api_auth.py
  test_api_inventory.py
  test_api_vendors.py
  test_api_rfx_lifecycle.py
  test_chat_sse_streaming.py
  test_chat_websocket.py
  test_email_outbound_aiosmtpd.py
  test_email_inbound_fake_imap.py
  test_telegram_inbound_mocked.py
  test_telegram_start_token_binding.py
  test_offer_extraction_pipeline_end_to_end.py
  test_multi_attachment_fusion.py
  test_security_rbac.py
  test_security_token_replay.py
  test_security_upload_mime_spoof.py
  test_security_sqli.py
  test_security_xss.py
  test_security_pii.py
  test_security_cross_prompt_injection.py  # vendor content cannot hijack buyer chat
  test_po_render_and_email.py

tests/e2e/  (Playwright)
  test_buyer_drafts_and_dispatches.spec.ts
  test_buyer_terms_confirmation.spec.ts        # D16
  test_vendor_replies_in_app_with_pdf.spec.ts
  test_vendor_replies_in_app_with_excel.spec.ts
  test_vendor_replies_in_app_with_image.spec.ts
  test_vendor_replies_in_app_with_voice.spec.ts
  test_vendor_replies_via_email_pdf.spec.ts
  test_vendor_replies_via_telegram_stub.spec.ts
  test_comparison_matrix_and_split_award.spec.ts
  test_po_pdf_generated_and_emailed.spec.ts
  test_hindi_chat_input.spec.ts
```

### 7.4 UAT (User Acceptance Test) scripts

`docs/UAT.md` — manual + Playwright-automatable scripts covering:

1. **UAT-1 Buyer drafts in Hinglish via voice → dispatches**
2. **UAT-2 Vendor receives via in-app, replies with PDF → buyer sees extracted offer**
3. **UAT-3 Vendor receives via email, replies with photographed price list → buyer sees extracted offer**
4. **UAT-4 Vendor receives via Telegram, replies with Excel → buyer sees extracted offer**
5. **UAT-5 Side-by-side compare → split award per line item → PO PDF emailed**
6. **UAT-6 Buyer overrides extracted field manually → audit log records change**
7. **UAT-7 Vendor asks clarification mid-quote → buyer answers via chat → vendor resumes**
8. **UAT-8 Deadline reminder fires automatically**
9. **UAT-9 Security: vendor A cannot read vendor B's thread (403)**
10. **UAT-10 Security: tampered correlation token rejected**

---

## 8. Build Order & Sub-Agent Work Packets (multi-agent dev)

**Legend**: `[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked
**Owner**: sub-agent type to dispatch (`feature-implementer`, `prototype-builder`, `ui-tester`, `test-runner`, `bug-resolver`, `code-quality-checker`, `documentation-writer`).
**Deps**: prerequisite packets (must be done before this packet starts).
**Parallel**: packets in the same Parallel Group can run concurrently.

### 8.0 Commit & Push Discipline (mandatory)

> **Rule: every significant step is committed and pushed to `origin/main` before moving on.** No accumulated uncommitted work; demo-day insurance + small reviewable diffs.

**What counts as a significant step:**
- Every completed phase (Phase 0, 1, 2, …) — **mandatory `P*.CP` commit checkpoint**.
- Within a phase, any standalone packet that adds passing tests + working code (≥30 min of work) — recommended sub-checkpoint.
- Schema migrations — always their own commit so `alembic revision` history stays clean.
- Security / guardrails / observability work — always tagged in the commit message for grep-ability.

**Convention:**
```bash
# At end of each work packet (after tests pass)
git add <touched files>
git status            # human eyeball: no .env, no secrets, no junk
git diff --cached      # spot-check
git commit -m "phase-N: <imperative summary>"
git push               # always push, never accumulate
```

**Commit message template:** `phase-<N>: <verb> <object>` — e.g.
`phase-2: add NIM OpenAI-compat provider + VCR cassettes`,
`phase-6: add multimodal offer fusion with confidence scoring`.

**Tag at meaningful stops:**
- End of Day 1 → `git tag v0.1-day1 && git push --tags`
- End of Day 2 (demo-ready) → `git tag v0.2-demo && git push --tags`
- Any production-leaning milestone → `vX.Y` tag

**Pre-commit safety (CI + local hook):**
- Block any commit that stages `.env*`, `*.key`, `*.pem`, or anything matching the secret-pattern regex (P0.6).
- Block any commit that drops backend coverage below 80% (P0.7 sets this up after Phase 1).
- Block any commit that introduces new Python files without a paired `tests/unit/test_*.py`.

**Branching:**
- Single `main` branch for the prototype (1–2 day budget; no PR friction).
- Each phase's first packet may use a topic branch (`phase-N-<slug>`) **only if** a sub-agent is dispatched in isolation; merge back to `main` on phase completion with `--ff-only`.
- Force-push to `main` is forbidden.

**Pre-push CI gate (when CI lands in P0.7):** ruff + mypy --strict + pytest + secret-scan + dep-audit. Demo failure modes: silenced.

### Phase 0 — Scaffolding (Day 1 morning, ~2.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P0.1 | Create `IMPLMENTETION_PLAN_CONTEXT.md` in project root (mirror of this file) | claude (main) | — | `[x]` |
| P0.2 | Init project structure (`src/aeros/`, `frontend/`, `tests/`, `pyproject.toml`, `alembic.ini`, `app.sh`, `.env.example`, `docker-compose.yml`) | feature-implementer | P0.1 | `[x]` |
| P0.3 | FastAPI app shell, config loader, DB engine + session, SQLModel registry, lifespan hooks | feature-implementer | P0.2 | `[x]` |
| P0.4 | Frontend scaffold via `/ui-ux-pro-max` (Vite + React 19 + Tailwind v4 + routes + auth shell + role-aware redirect for buyer/vendor/admin) | feature-implementer (invoke `/ui-ux-pro-max` skill in prompt) | P0.2 | `[x]` |
| P0.5 | First migration (Alembic) + seed script | feature-implementer | P0.3 | `[x]` |
| P0.6 | **Pre-commit hook**: secret-pattern scan (.env regex + entropy), block `*.env` / `*.key` / `*.pem` staging, `ruff check`, `ruff format --check` | feature-implementer | P0.2 | `[ ]` |
| P0.7 | **CI workflow** (`.github/workflows/ci.yml`): ruff + mypy --strict + pytest + coverage gate + secret-scan + dep-audit | feature-implementer | P0.6 | `[ ]` |
| P0.CP | **Commit checkpoint**: `git add . && git commit -m "phase-0: scaffold + pre-commit + CI" && git push` | claude (main) | P0.2–P0.7 | `[x]` |

### Phase 1 — Auth + 3-tier RBAC + Audit (Day 1 morning, ~2.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P1.1 | `security/jwt.py`, `security/hmac.py`, `security/csrf.py`, `security/headers.py`, `security/rate_limit.py` | feature-implementer | P0.3 | `[x]` (jwt+hmac done, csrf/headers/rate-limit deferred) |
| P1.2 | `models/user.py` (role enum buyer|vendor|admin, status), `models/organization.py`, `models/user_defaults.py`, `models/audit.py`, `models/system_setting.py`, `models/ai_provider_config.py` + migration | feature-implementer | P0.5 | `[x]` |
| P1.3 | `services/auth_service.py`, `services/audit_service.py`, `services/defaults_service.py`, `security/auth_context.py` (`AuthContext` dataclass + `require_role(*roles)` dep) | feature-implementer | P1.1, P1.2 | `[x]` |
| P1.3b | **`db/scope.py`** — `for_user(caller, Model)` query-scope filter helper for 3-tier RBAC (buyer→own-org, vendor→own-threads, admin→all) + `MissingAuthFilter` lint rule for unscoped queries + unit tests `test_db_query_scope_filter.py` | feature-implementer | P1.2 | `[ ]` |
| P1.4 | `api/auth.py` (register/login/logout/refresh/me) + tests/unit + tests/integration | feature-implementer + test-runner | P1.3 | `[x]` |
| P1.5 | Frontend auth pages (Login/Register/RoleRedirect) — redirects to `/buyer`, `/vendor`, or `/admin` per role | feature-implementer (UI skill) | P0.4, P1.4 | `[x]` |
| P1.6 | Security RBAC tests: buyer↔vendor isolation, admin elevation paths, token-tamper, scope-filter omission detection | test-runner | P1.4, P1.3b | `[ ]` |
| P1.7 | Bootstrap admin: seed migration creates `admin@aeros.local` with random password printed once + forced rotation; tests | feature-implementer | P1.2 | `[x]` |
| P1.CP | **Commit checkpoint**: `git add . && git commit -m "phase-1: 3-tier RBAC auth + audit + admin bootstrap" && git push` | claude (main) | P1.1–P1.7 | `[x]` |

### Phase 2 — Provider abstraction + AI primitives (Day 1 midday, ~2h) — **PARALLELIZABLE**

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P2.1 | `ai/base.py` protocols + `ai/factory.py` + `ai/llm_cache.py` + `ai/schemas.py` | feature-implementer | P0.3 | `[x]` |
| P2.2 | `ai/openai_compatible.py` (NIM impl) + VCR tests | feature-implementer | P2.1 | `[x]` (impl done, VCR deferred) |
| P2.3 | `ai/anthropic_compatible.py` + VCR tests (parallel with P2.2) | feature-implementer | P2.1 | `[ ]` (deferred — NIM-only for prototype) |
| P2.4 | `ai/nim_vision.py` + VCR tests (parallel with P2.2) | feature-implementer | P2.1 | `[x]` (vision via openai_compatible) |
| P2.5 | `ai/groq_asr.py` + VCR tests (parallel with P2.2) | feature-implementer | P2.1 | `[x]` |
| P2.6 | `ai/normalization.py` (units + currency) + unit tests (property-based via hypothesis) | feature-implementer | P2.1 | `[ ]` |
| P2.7 | `ai/prompts/` (system prompts incl. Hindi/Hinglish/English handling) + `prompts/wrap.py` (untrusted-content delimiter helper) + immutability checksum tests | feature-implementer | P2.1 | `[x]` (intake + evaluation prompts done) |
| P2.8 | **`ai/guardrails/` — input filter (jailbreak regex), intent validator (dual-LLM), output filter (PII redactor), action allow-list registry** + tests for each + cross-prompt-injection test suite | feature-implementer + test-runner | P2.1, P2.2, P2.7 | `[ ]` |
| P2.9 | `services/ai_budget_service.py` (per-RFx + per-user token cap + circuit breaker) + tests | feature-implementer | P2.1 | `[ ]` |
| P2.CP | **Commit checkpoint**: `git commit -m "phase-2: provider abstraction + guardrails + budget" && git push` | claude (main) | P2.1–P2.9 | `[x]` |

### Phase 3 — Inventory + Vendors + Defaults (Day 1 afternoon, ~2h) — **PARALLELIZABLE**

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P3.1 | `models/sku.py`, `models/vendor.py` + migration | feature-implementer | P0.5 | `[x]` |
| P3.2 | `services/inventory_service.py`, `services/vendor_service.py` + unit tests | feature-implementer | P3.1 | `[x]` |
| P3.3 | `api/buyer.py` (inventory + vendors + defaults endpoints) + integration tests | feature-implementer + test-runner | P3.2, P1.3 | `[x]` |
| P3.4 | `seed/dark_store.py` (1 buyer org + 40 SKUs + 8 vendors + 3 historical RFx) | feature-implementer | P3.1 | `[x]` |
| P3.5 | Frontend: Inventory page + Vendors page + Settings/Defaults page | feature-implementer (UI skill) | P3.3 | `[~]` (in progress — agent building) |
| P3.CP | **Commit checkpoint**: `git commit -m "phase-3: inventory + vendors + defaults" && git push` | claude (main) | P3.1–P3.5 | `[x]` |

### Phase 4 — RFx state machine + IntakeAgent + Chat (Day 1 evening, ~3h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P4.1 | `models/rfx.py`, `models/message.py`, `models/notification.py` + migration | feature-implementer | P0.5 | `[x]` |
| P4.2 | `services/rfx_service.py` (state machine + audit hooks) + unit tests | feature-implementer | P4.1, P1.3 | `[x]` |
| P4.3 | `services/thread_service.py` + unit tests | feature-implementer | P4.1 | `[ ]` |
| P4.4 | `agents/base.py` + `agents/intake.py` (Hindi/Hinglish prompts, defaults confirmation via tool calls) + unit tests | feature-implementer | P2.*, P4.2, P1.3 | `[x]` |
| P4.5 | `api/chat.py` (SSE for buyer chat + WS for in-app vendor chat) + integration tests | feature-implementer + test-runner | P4.4 | `[x]` |
| P4.6 | Frontend: Buyer ChatCopilot (SSE stream, TermsChip, SuggestedVendors, DraftPreview, MicButton) | feature-implementer (UI skill) | P4.5 | `[ ]` |
| P4.7 | Frontend: Buyer Dashboard + RFx tile | feature-implementer (UI skill) | P4.5 | `[ ]` |
| P4.8 | E2E: `test_buyer_drafts_and_dispatches.spec.ts`, `test_buyer_terms_confirmation.spec.ts`, `test_hindi_chat_input.spec.ts` | ui-tester | P4.6 | `[ ]` |
| P4.CP | **Commit checkpoint + Day-1 tag**: `git commit -m "phase-4: intake agent + buyer chat (Day 1 done)" && git push && git tag v0.1-day1 && git push --tags` | claude (main) | P4.1–P4.8 | `[ ]` |

### Phase 5 — Channel 1: In-app reply (web FIRST, per D5) (Day 2 morning, ~2h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P5.1 | `channels/in_app.py` + `channels/correlation.py` + unit tests | feature-implementer | P1.1, P4.2 | `[ ]` |
| P5.2 | `agents/vendor_copilot.py` (vendor co-pilot chat) + unit tests | feature-implementer | P4.4 | `[ ]` |
| P5.3 | `api/vendor.py` (inbox + reply + upload) + integration tests | feature-implementer + test-runner | P5.2 | `[ ]` |
| P5.3a | **Vendor decline (D29)**: `decline_rfx` tool in VendorAgent + `POST /api/vendor/rfx/<id>/decline` + service method on `RFxService` + audit + tests + UI button & reason modal | feature-implementer + test-runner | P5.3 | `[ ]` |
| P5.4 | Frontend: Vendor Inbox + Vendor RFxReply chat (UploadZone, MicButton, extraction-status badge, **all-channel thread view per D34**, **resubmit-as-new-revision per D29**) | feature-implementer (UI skill) | P5.3 | `[ ]` |
| P5.5 | E2E: `test_vendor_replies_in_app_with_pdf/excel/image/voice.spec.ts` | ui-tester | P5.4 | `[ ]` |
| P5.CP | **Commit checkpoint**: `git commit -m "phase-5: web channel + vendor co-pilot" && git push` | claude (main) | P5.1–P5.5 | `[ ]` |

### Phase 6 — Extractors + Evaluation + Comparison (Day 2 morning, ~3h) — **PARALLELIZABLE EXTRACTORS**

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P6.1 | `services/file_service.py` (MIME sniff, magic, size, virus hook) + unit tests | feature-implementer | P0.3 | `[ ]` |
| P6.2 | `ai/extractors/router.py` + `ai/extractors/pdf.py` (digital + scanned detection) + unit tests | feature-implementer | P2.2, P2.4, P2.6 | `[ ]` |
| P6.3 | `ai/extractors/word.py` + unit tests (parallel with P6.2) | feature-implementer | P2.2, P2.6 | `[ ]` |
| P6.4 | `ai/extractors/spreadsheet.py` (xlsx + csv + tsv) + unit tests (parallel with P6.2) | feature-implementer | P2.2, P2.6 | `[ ]` |
| P6.5 | `ai/extractors/image.py` + unit tests (parallel with P6.2) | feature-implementer | P2.4, P2.6 | `[ ]` |
| P6.6 | `ai/extractors/email_body.py` (HTML + plaintext + forwarded chain) + unit tests | feature-implementer | P2.2 | `[ ]` |
| P6.7 | `services/offer_fusion_service.py` (multi-attachment fusion) + unit tests | feature-implementer | P6.2–P6.6 | `[ ]` |
| P6.8 | `agents/evaluation.py` + integration tests | feature-implementer + test-runner | P6.7 | `[ ]` |
| P6.9 | `models/offer.py` + `services/offer_service.py` + migration + unit tests | feature-implementer | P4.1 | `[ ]` |
| P6.10 | `workers/extract_offer.py` (Huey task) + integration tests | feature-implementer | P6.8, P6.9 | `[ ]` |
| P6.11 | Frontend: RFx detail with ComparisonMatrix (side-by-side, sortable, per-field confidence badges per D33, manual override, **split-award**) | feature-implementer (UI skill) | P6.9 | `[ ]` |
| P6.11a | **Realistic flows UI (D29/D31/D33)**: header **Withdraw RFx** action + confirmation modal + `RFxService.cancel` + system-message fan-out + revision badge (v2/v3) on Offer cards with hover-history toggle + late badge + low-confidence auto-flag with "must-acknowledge" gate before award + declined-vendor tile + offer-revision migration of overrides + tests | feature-implementer + test-runner | P6.11 | `[ ]` |
| P6.12 | E2E: `test_comparison_matrix_and_split_award.spec.ts`, `test_multi_attachment_fusion`, `test_buyer_withdraws_rfx.spec.ts`, `test_offer_revision_visible.spec.ts`, `test_vendor_declines.spec.ts` | ui-tester + test-runner | P6.11a | `[ ]` |
| P6.CP | **Commit checkpoint**: `git commit -m "phase-6: extractors + evaluation + comparison matrix" && git push` | claude (main) | P6.1–P6.12 | `[ ]` |

### Phase 7 — Channel 2: Email (Day 2 afternoon, ~2.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P7.1 | `channels/email_out.py` (aiosmtplib + Reply-To token + portal link) + tests | feature-implementer | P5.1 | `[ ]` |
| P7.2 | `agents/sourcing.py` (compose + dispatch + schedule reminder via channels) + unit tests | feature-implementer | P4.4, P7.1, P5.1 | `[ ]` |
| P7.3 | `channels/email_in.py` (IMAP poll, attachment download, threading) + `workers/imap_poll.py` + integration tests with aiosmtpd + fake IMAP | feature-implementer + test-runner | P7.1, P6.10 | `[ ]` |
| P7.4 | `services/reminder_service.py` + `workers/reminders.py` with **multi-slot schedule (T-24h, T-2h, final) per D29**, per-slot idempotency via `RFxVendor.reminders_sent_json`, channel-fallback on per-send failure + tests | feature-implementer | P7.2 | `[ ]` |
| P7.5 | E2E: `test_vendor_replies_via_email_pdf.spec.ts` (uses aiosmtpd + fake IMAP) | ui-tester | P7.3 | `[ ]` |
| P7.CP | **Commit checkpoint**: `git commit -m "phase-7: email channel (SMTP + IMAP) + reminders" && git push` | claude (main) | P7.1–P7.5 | `[ ]` |

### Phase 8 — Channel 3: Telegram (Day 2 afternoon, ~2h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P8.1 | `channels/telegram_bot.py` (`/start <token>` binding, message + photo + document handlers, webhook secret) + unit tests with mocked updates | feature-implementer | P5.1, P6.10 | `[ ]` |
| P8.2 | `api/inbound_telegram.py` (webhook + `/api/test/telegram-fake` dev endpoint for simulated updates) + integration tests | feature-implementer + test-runner | P8.1 | `[ ]` |
| P8.3 | Hook Telegram channel into `agents/sourcing.py` dispatch + `channels/notifications.py` fan-out | feature-implementer | P8.1, P7.2 | `[ ]` |
| P8.4 | Frontend: Telegram-bind button on vendor Profile (deep-link to bot with token) | feature-implementer (UI skill) | P8.2 | `[ ]` |
| P8.5 | E2E: `test_vendor_replies_via_telegram_stub.spec.ts` (uses simulated update endpoint) | ui-tester | P8.4 | `[ ]` |
| P8.CP | **Commit checkpoint**: `git commit -m "phase-8: telegram channel (bot + webhook + token binding)" && git push` | claude (main) | P8.1–P8.5 | `[ ]` |

### Phase 9 — Post-Award PO (Day 2 evening, ~1.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P9.1 | `models/award.py`, `models/po.py` + migration | feature-implementer | P4.1 | `[ ]` |
| P9.2 | `agents/po.py` + `services/po_service.py` (weasyprint HTML→PDF template) + unit tests | feature-implementer | P9.1, P7.1 | `[ ]` |
| P9.3 | `workers/po_render.py` (Huey task) + integration tests | feature-implementer | P9.2 | `[ ]` |
| P9.4 | `api/po.py` (download endpoint, signed) + `api/buyer.py` award endpoint | feature-implementer | P9.2 | `[ ]` |
| P9.5 | Frontend: Award button on ComparisonMatrix + PO preview modal | feature-implementer (UI skill) | P9.4, P6.11 | `[ ]` |
| P9.6 | E2E: `test_po_pdf_generated_and_emailed.spec.ts` | ui-tester | P9.5 | `[ ]` |
| P9.CP | **Commit checkpoint**: `git commit -m "phase-9: post-award PO render + dispatch" && git push` | claude (main) | P9.1–P9.6 | `[ ]` |

### Phase 9.5 — Observability & Statistics layer (D26) — **THREADS THROUGH ALL AGENTS**

This phase is split across two windows. Scaffolding (§9.5a) lands early (right after Phase 2) so every subsequent agent/channel commit writes telemetry from day one. Dashboard (§9.5b) lands in Phase 10.

**§9.5a — Telemetry scaffolding (between Phase 2 and Phase 4)** (~1.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P9.5a.1 | `models/observability.py` (LLMCallLog, AgentRunLog, ChannelEventLog, PipelineReport) + migration | feature-implementer | P0.5 | `[ ]` |
| P9.5a.2 | `ai/pricing.py` (per-model token rates; NIM=0 flagged) + unit tests | feature-implementer | P2.1 | `[ ]` |
| P9.5a.3 | `services/telemetry_service.py` (write helpers, redaction, trace-id propagation) + unit tests including `test_log_redaction_in_telemetry.py` | feature-implementer | P9.5a.1, P9.5a.2 | `[ ]` |
| P9.5a.4 | LLM-call decorator wrapping every `ChatProvider`/`VisionProvider`/`ASRProvider` call → emits `LLMCallLog`; integrated into `ai/openai_compatible.py`, `ai/anthropic_compatible.py`, `ai/nim_vision.py`, `ai/groq_asr.py` | feature-implementer | P9.5a.3, P2.2–P2.5 | `[ ]` |
| P9.5a.5 | Agent-run context manager in `agents/base.py` → opens `AgentRunLog` span, captures child LLM-calls + tool-calls, propagates `trace_id` to Huey task headers | feature-implementer | P9.5a.3 | `[ ]` |
| P9.5a.6 | Channel-event hook in `channels/email_out.py`, `channels/email_in.py`, `channels/telegram_bot.py`, `channels/in_app.py` → emit `ChannelEventLog` | feature-implementer | P9.5a.3 | `[ ]` (lands as channels go in) |
| P9.5a.7 | `PipelineReport` attachment in `api/chat.py`: build summary from the chat turn's `AgentRunLog` + nested `LLMCallLog` rows; return alongside chat response | feature-implementer | P9.5a.5, P4.5 | `[ ]` |
| P9.5a.8 | Frontend: per-chat `<InspectPanel/>` (collapsible under the message bubble; renders the PipelineReport JSON memo.sbs-style) | feature-implementer (UI skill) | P9.5a.7, P4.6 | `[ ]` |
| P9.5a.9 | Tests: `test_llm_call_log_decorator.py`, `test_agent_run_log_context.py`, `test_pipeline_report_attached_to_chat.py`, `test_channel_event_log.py` | test-runner | P9.5a.4–P9.5a.7 | `[ ]` |
| P9.5a.CP | **Commit checkpoint**: `git commit -m "phase-9.5a: telemetry scaffolding + inspect panel" && git push` | claude (main) | P9.5a.1–P9.5a.9 | `[ ]` |

**§9.5b — Observability dashboard (Phase 10 slot)** (~1.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P9.5b.1 | `services/observability_service.py` (aggregations: cards, charts, tables, per-RFx timeline) + unit tests `test_observability_dashboard_aggregations.py` | feature-implementer + test-runner | P9.5a.* | `[ ]` |
| P9.5b.2 | `api/buyer.py` observability endpoints (`/api/buyer/observability/{summary,calls,timeline,trace/<id>}`) + integration tests | feature-implementer + test-runner | P9.5b.1 | `[ ]` |
| P9.5b.3 | Frontend: `/buyer/observability` page (cards + charts via recharts + tables + per-RFx timeline swimlane) | feature-implementer (UI skill) | P9.5b.2 | `[ ]` |
| P9.5b.4 | `/buyer/observability/trace/<id>` drill-down view (full `AgentRunLog` + nested `LLMCallLog` table) | feature-implementer (UI skill) | P9.5b.3 | `[ ]` |
| P9.5b.5 | Retention worker `workers/telemetry_retention.py` (30d default; configurable) + tests | feature-implementer | P9.5a.1 | `[ ]` |
| P9.5b.6 | E2E: `test_observability_dashboard.spec.ts` (cards populate, drill-down works, trace shows nested calls) | ui-tester | P9.5b.3 | `[ ]` |
| P9.5b.CP | **Commit checkpoint**: `git commit -m "phase-9.5b: observability dashboard + retention worker" && git push` | claude (main) | P9.5b.1–P9.5b.6 | `[ ]` |

### Phase 9.7 — Admin Shell (D27) (Day 2 evening, ~1.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P9.7.1 | `services/admin_service.py` (user CRUD, suspend, role-change, password-reset, force-logout) + unit tests | feature-implementer | P1.3 | `[ ]` |
| P9.7.2 | `services/ai_config_service.py` (DB-backed `AIProviderConfig` CRUD; `ai/factory.py` reads DB-first, env-fallback) + unit tests | feature-implementer | P2.1, P1.2 | `[ ]` |
| P9.7.3 | `services/system_settings_service.py` (CRUD on `SystemSetting`; consumers — rate-limit, budget, retention — read live) + unit tests | feature-implementer | P1.2 | `[ ]` |
| P9.7.4 | `api/admin.py` (`/api/admin/{users,orgs,vendors/kyc,ai/providers,ai/budgets,settings,observability,audit,incidents}`) + integration tests (`test_admin_rbac.py`) | feature-implementer + test-runner | P9.7.1–P9.7.3, P1.3b | `[ ]` |
| P9.7.5 | Frontend: `/admin/dashboard` (cross-tenant KPIs) | feature-implementer (UI skill) | P9.7.4 | `[ ]` |
| P9.7.6 | Frontend: `/admin/users` + `/admin/orgs` + `/admin/vendors/kyc` | feature-implementer (UI skill) | P9.7.4 | `[ ]` |
| P9.7.7 | Frontend: `/admin/ai/providers` (DB-backed model toggle, default-pick) + `/admin/ai/budgets` | feature-implementer (UI skill) | P9.7.4 | `[ ]` |
| P9.7.8 | Frontend: `/admin/settings` + `/admin/observability` (cross-tenant) + `/admin/audit` + `/admin/incidents` (runbook actions) | feature-implementer (UI skill) | P9.7.4, P9.5b.3 | `[ ]` |
| P9.7.9 | E2E: `test_admin_user_management.spec.ts`, `test_admin_ai_provider_toggle.spec.ts`, `test_admin_cannot_silently_read_thread_unaudited.spec.ts` | ui-tester | P9.7.5–P9.7.8 | `[ ]` |
| P9.7.CP | **Commit checkpoint**: `git commit -m "phase-9.7: admin shell + DB-backed AI config + cross-tenant observability" && git push` | claude (main) | P9.7.1–P9.7.9 | `[ ]` |

### Phase 10 — Activity Panel + Coming-Soon Stubs + Polish (Day 2 evening, ~1.5h) — **PARALLELIZABLE**

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P10.1 | Frontend: Activity (audit log) panel | feature-implementer (UI skill) | P1.6 | `[ ]` |
| P10.2 | Frontend: Coming-Soon tabs (Negotiation, Contract, Invoice, Analytics) with mocked screenshots | feature-implementer (UI skill) | P0.4 | `[ ]` |
| P10.3 | `agents/_stubs/*` placeholder classes + tests | feature-implementer | P4.4 | `[ ]` |
| P10.4 | Command Palette + Toaster + dark mode + responsive polish | feature-implementer (UI skill) | P0.4 | `[ ]` |
| P10.5 | Notifications fan-out service (`channels/notifications.py`) wiring email + telegram + in-app prefs | feature-implementer | P5.1, P7.1, P8.1 | `[ ]` |
| P10.CP | **Commit checkpoint**: `git commit -m "phase-10: activity panel + coming-soon stubs + polish" && git push` | claude (main) | P10.1–P10.5 | `[ ]` |

### Phase 11 — Final QA + Docs + Demo (Day 2 evening, ~1.5h)

| ID | Packet | Owner | Deps | Status |
|---|---|---|---|---|
| P11.1 | Run full test suite, fix failures | test-runner + bug-resolver | all | `[ ]` |
| P11.2 | Code-quality pass (ruff, mypy --strict, security review) | code-quality-checker | all | `[ ]` |
| P11.3 | `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `DEMO_SCRIPT.md`, `UAT.md`, `API.md` | documentation-writer | all | `[ ]` |
| P11.4 | Dry-run demo end-to-end on localhost; capture screenshots; record 60s loom for backup | ui-tester | all | `[ ]` |
| P11.5 | Mark `IMPLMENTETION_PLAN_CONTEXT.md` checkboxes as done; update Decisions Confirmed | claude (main) | all | `[ ]` |
| P11.CP | **Final commit + Day-2 tag**: `git commit -m "phase-11: docs + final QA (demo ready)" && git push && git tag v0.2-demo && git push --tags` | claude (main) | P11.1–P11.5 | `[ ]` |

**Parallel groups for sub-agent dispatch**:
- After P0.5: dispatch P1.1+P2.1+P3.1 in parallel.
- After P2.1: dispatch P2.2 / P2.3 / P2.4 / P2.5 / P2.6 / P2.7 in parallel (6 extractor / provider streams).
- After P6.1: dispatch P6.2 / P6.3 / P6.4 / P6.5 / P6.6 in parallel (5 extractor streams).
- After Phase 4 complete: dispatch Phase 5 (web) on its own, Phase 7 (email) and Phase 8 (Telegram) sequentially per D5 but Phase 6 (extractors) runs in parallel with Phase 5–8.

**Resume protocol**: this file's checkboxes are the canonical progress state. Any session can pick up by reading the first `[ ]` in earliest unfinished phase.

---

## 9. Verification (live demo, end-to-end)

1. `./app.sh setup` — installs deps, runs migrations, seeds dark-store inventory + vendors + buyer/vendor demo users + 3 historical RFx.
2. `./app.sh start` — backend `:4040`, frontend `:5173`, Huey worker, MailHog (`:8025`) for outbound capture in dev, ngrok URL for Telegram (printed).
3. Visit `http://localhost:5173`, log in as `buyer@aeros.demo`.
4. Open chat: voice input "मुझे कल सुबह 5 बजे तक 150 किलो टमाटर, 80 किलो प्याज और 500 लीटर दूध चाहिए" (Hindi). Watch IntakeAgent stream draft. Terms chip shows defaults; buyer clicks chip, changes validity to 3 days. Approve.
5. SourcingAgent dispatches: vendor A via in-app, vendor B via email (visible in MailHog), vendor C via Telegram (deep link in printed log).
6. Vendor A (in-app): log in → reply chat with VendorAgent → upload `freshfarm_rates.xlsx` → extraction confirmation badge.
7. Vendor B (email): aiosmtpd captures outbound, fake IMAP replays vendor reply with `acme_dairy.pdf` + body text → fusion → offer extracted.
8. Vendor C (Telegram): simulated update endpoint posts `kirana_proforma.jpg` → vision extracts → offer.
9. Buyer sees ComparisonMatrix populate live with three offers, per-field confidence badges, lowest-price highlight per line. Buyer overrides one extracted price (audit logged). Splits award (tomatoes to vendor B, milk to vendor A).
10. POAgent renders PO PDF, emails awarded vendors, surfaces download link.
11. Run `pytest -q && cd frontend && pnpm test && pnpm e2e` — all green, coverage ≥80%.

Demo can also run **without** voice/Hindi for international audiences (English fallback).

---

## 10. References to reuse (don't copy blindly)

- `/Users/prakersh/projects/4dpocket/src/fourdpocket/ai/base.py` — `ChatProvider` protocol shape.
- `/Users/prakersh/projects/4dpocket/src/fourdpocket/ai/openai_compatible.py:33-81` — NIM/OpenAI-compat client wrapping pattern.
- `/Users/prakersh/projects/4dpocket/src/fourdpocket/ai/extractor.py` — gleaning extraction loop; adapt for Offer extraction.
- `/Users/prakersh/projects/4dpocket/src/fourdpocket/ai/llm_cache.py` — content-hash response cache.
- `/Users/prakersh/projects/4dpocket/src/fourdpocket/workers/enrichment_pipeline.py` — Huey stage-DAG; adapt for offer pipeline.
- `/Users/prakersh/projects/4dpocket/src/fourdpocket/processors/pdf.py` — PyMuPDF + pymupdf4llm.
- `/Users/prakersh/projects/4dpocket/app.sh` — lifecycle script style.
- `/Users/prakersh/projects/nvidia/apps/proxy/app/clients/nvidia_client.py:15-57` — exact NIM call shapes (chat, vision, embeddings).
- `/Users/prakersh/projects/nvidia/apps/proxy/app/clients/groq_asr_client.py:30-90` — Groq Whisper call shape.
- `/Users/prakersh/projects/memo.sbs/src/templates/partials/_chat_component.html` + `_chat_component.js` — floating-chat UX pattern (port to React).
- `/Users/prakersh/projects/memo.sbs/src/ai/agent.py` — RAG-first agent JSON-plan pattern.

---

## 11. Clarifications resolved

All design questions resolved (see §2 Decisions Confirmed). The plan is implementation-ready.

**Operational notes for implementation start:**
- Phase 7 (Email) will use MailHog (`localhost:8025`) until user provides the dedicated SMTP credentials; swap is a `.env` change, no code change.
- Phase 8 (Telegram) will use the `/api/test/telegram-fake` simulated-update endpoint until user provides a BotFather token; swap is a `.env` change + setting webhook URL.
- All AI calls are recorded as VCR cassettes on first real run, so the test suite is offline-replayable thereafter.

---

## 12. Out-of-scope for this prototype

- Real production deployment (Docker compose + ingress + secrets manager) — `docker-compose.yml` ships but is not the demo target.
- ERP integrations (SAP/Oracle) — placeholder mention only.
- Spend analytics module — Coming-Soon tab.
- Contract lifecycle — Coming-Soon tab.
- Invoice 3-way match — Coming-Soon tab.
- Multi-tenancy beyond single buyer org + multiple vendor orgs.
- Mobile apps (PWA-friendly responsive only).
- 2FA / SSO (basic email+password only).
- Detailed permissions matrix beyond 2 roles.

Anything above can be added on top of the same data model and channel abstraction without rewrites.
