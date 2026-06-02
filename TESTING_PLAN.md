# AerOS Testing Plan - Quality-First, Workflow-Driven

## Overview

The suite is organized around **business workflows** - the flows that directly
affect customers - rather than code layers. As of this writing it has **777
tests at 80.85% line coverage**, with **≥80% enforced** in CI
(`fail_under = 80` in `pyproject.toml`). The 7 bugs catalogued below were each
identified, reproduced with a failing test, then fixed; those regression tests
now pass.

Run the full suite (backend + Playwright E2E) with `./app.sh test`. The PO
rendering tests need WeasyPrint's native libraries - `./app.sh` exports the
Homebrew lib path on macOS automatically; running `pytest` directly without it
fails only those 4 tests.

**Principle**: every test must justify its existence by protecting a specific
business risk. No test exists solely to inflate a count.

---

## Confirmed Bugs - Caught and Fixed

All 7 were reproduced with a failing test, then fixed. Locations cite the
current function (line numbers omitted to avoid drift).

| # | Location | Bug | Impact | Status |
|---|----------|-----|--------|--------|
| 1 | `api/vendor.py` `submit_quote` | total used a hardcoded `* 1` instead of quantity | Every structured quote total was wrong | Fixed - multiplies by `line_item_qty_map` |
| 2 | `api/buyer.py` `award_rfx` | `except Exception: pass` swallowed PO generation errors | PO silently never created | Fixed - error logged via structlog |
| 3 | `services/rfx_service.py` | No status validation on `cancel_rfx` / `dispatch_rfx` / `award_rfx` | Cancelled RFx could be awarded | Fixed - invalid transitions raise `ValueError` |
| 4 | `api/vendor.py` `upload_file` | AI extraction ran synchronously inline | Request timeouts on large files | Handled via `workers/extract_offer.py` |
| 5 | `agents/executor.py` | `Message(thread_id=...)` could be null | Orphaned messages with null FK | Fixed - guarded thread creation |
| 6 | `services/rfx_service.py` `award_rfx` | No idempotency guard on award | Duplicate POs on double-award | Fixed - status guard rejects re-award |
| 7 | `agents/po.py` `run` | WeasyPrint fallback saves HTML but reuses `pdf_path` | HTML served as `application/pdf` | Fixed - download serves correct content type |

---

## Section 1: RFx Lifecycle - Highest Priority

**What this protects**: The RFx lifecycle is the core product. A buyer creates an
RFx, adds items, assigns vendors, dispatches, collects quotes, awards, and gets
a PO. Broken state transitions or missing validation here directly block
customers.

**File**: `tests/unit/test_rfx_service.py`

### 1a. State Machine Validation - targets Bug #3

Tests enforce valid status transitions. Invalid transitions must raise
`ValueError`. These tests define the contract; the service code must be patched
to add validation.

| Test | Asserts |
|------|---------|
| `test_dispatch_from_draft_succeeds` | drafting -> dispatched |
| `test_dispatch_from_dispatched_is_idempotent` | Already-dispatched returns without error |
| `test_cancel_from_draft_succeeds` | drafting -> cancelled |
| `test_cancel_from_dispatched_succeeds` | dispatched -> cancelled allowed |
| `test_cancel_from_awarded_raises` | awarded -> cancelled rejected |
| `test_cancel_from_cancelled_raises` | cancelled -> cancelled rejected |
| `test_award_from_dispatched_succeeds` | dispatched -> awarded |
| `test_award_from_draft_raises` | drafting -> awarded rejected |
| `test_award_from_cancelled_raises` | cancelled -> awarded rejected |
| `test_award_from_awarded_raises` | awarded -> awarded rejected (Bug #6) |

### 1b. RFx CRUD Edge Cases

| Test | Asserts |
|------|---------|
| `test_create_rfx_with_deadline` | Deadline persisted and returned |
| `test_create_rfx_with_delivery_window` | Window dates persisted |
| `test_add_line_items_to_nonexistent_rfx_raises` | ValueError on missing RFx |
| `test_add_line_items_empty_list` | Empty list returns empty |
| `test_add_line_items_with_target_price` | Target price persisted |
| `test_invite_vendor_duplicate_returns_existing` | Idempotent invite |
| `test_invite_vendor_creates_thread` | Thread auto-created |
| `test_get_rfx_with_details_nonexistent_returns_none` | None for missing RFx |
| `test_get_rfx_with_details_includes_dispatch_plan` | Dispatch plan shape |
| `test_list_rfx_for_buyer_empty` | New buyer sees empty list |
| `test_list_rfx_for_vendor_empty` | Vendor with no invites sees empty |
| `test_list_rfx_for_vendor_includes_buyer_name` | Buyer name resolved |

### 1c. Vendor Suggestions and Assignment

| Test | Asserts |
|------|---------|
| `test_get_vendor_suggestions_category_match` | Vendors matched by category |
| `test_get_vendor_suggestions_no_line_items` | Returns empty suggestions |
| `test_get_vendor_suggestions_scoring_order` | Sorted by composite score |
| `test_assign_vendors_to_items_valid` | Creates/updates RFxVendor |
| `test_assign_vendors_invalid_line_item_ids_raises` | Rejects bad IDs |
| `test_assign_vendors_creates_thread_for_new_vendor` | Thread auto-created |

**New tests**: ~28

---

## Section 2: Vendor Quote Submission

**What this protects**: Vendors submitting quotes is the second most critical
flow. Bug #1 means every structured quote total is wrong - directly affecting
procurement decisions and financial accuracy.

**File**: `tests/unit/test_vendor_api.py` (expand)

### 2a. Quote Total Calculation - targets Bug #1

| Test | Asserts |
|------|---------|
| `test_submit_quote_total_uses_quantity` | qty=100, price=50 -> total=5000, not 50 |
| `test_submit_quote_single_item_total` | qty=10, price=25 -> total=250 |
| `test_submit_quote_multiple_items_total` | Two items with different qty/price |
| `test_submit_quote_zero_quantity` | qty=0 -> total contribution is 0 |

### 2b. Quote Submission Workflow

| Test | Asserts |
|------|---------|
| `test_submit_quote_creates_offer` | Offer persisted with correct fields |
| `test_submit_quote_updates_vendor_status` | RFxVendor -> QUOTED |
| `test_submit_quote_creates_message` | Message in thread |
| `test_submit_quote_no_vendor_profile_returns_403` | Auth check |
| `test_submit_quote_no_thread_returns_404` | Thread must exist |
| `test_submit_quote_empty_line_items` | Empty items accepted |
| `test_submit_quote_revision_increments` | Second quote increments revision |

### 2c. Vendor Thread and Decline

| Test | Asserts |
|------|---------|
| `test_get_thread_returns_full_context` | Shape validation |
| `test_get_thread_marks_viewed` | INVITED -> VIEWED |
| `test_get_thread_no_vendor_profile_returns_403` | Auth check |
| `test_decline_sets_status_and_reason` | Status change |
| `test_decline_nonexistent_rfx_returns_404` | Error path |
| `test_reply_creates_message` | Message persisted |
| `test_upload_creates_attachment` | Attachment record |
| `test_upload_rejects_oversized_file` | 413 on large files |
| `test_vendor_inbox_returns_list` | Inbox shape |

**New tests**: ~20

---

## Section 3: Award and PO Generation

**What this protects**: Award is the money decision. PO generation is the
contractual output. Bugs #2, #6, #7 mean POs are silently never created,
duplicated, or delivered as HTML pretending to be PDF.

**File**: `tests/unit/test_po_agent.py` (new)

### 3a. PO Rendering - targets Bugs #2, #6, #7

| Test | Asserts |
|------|---------|
| `test_po_agent_generates_html_template` | HTML has vendor name, PO number, items |
| `test_po_agent_calculates_total` | total = sum(qty * price) |
| `test_po_agent_creates_purchase_order_record` | PurchaseOrder in DB |
| `test_po_agent_handles_missing_vendor` | Skips gracefully |
| `test_po_agent_weasyprint_fallback` | HTML saved when WeasyPrint fails (Bug #7) |
| `test_po_download_html_fallback_content_type` | text/html, not application/pdf |
| `test_po_generation_idempotency` | No duplicate POs (Bug #6) |
| `test_award_endpoint_logs_po_errors` | Not silently swallowed (Bug #2) |

### 3b. Award Service

| Test | Asserts |
|------|---------|
| `test_award_rfx_creates_award_record` | Award persisted |
| `test_award_rfx_sets_status` | RFx -> AWARDED |
| `test_award_rfx_logs_action` | Audit log created |
| `test_award_nonexistent_rfx_raises` | ValueError |
| `test_po_service_create_award` | po_service works |
| `test_po_service_create_po` | po_service works |
| `test_po_service_list_pos_for_rfx` | Lists POs |
| `test_po_service_get_po_by_award` | Lookup by award_id |

### 3c. PO API Endpoint

| Test | Asserts |
|------|---------|
| `test_get_po_details` | PO shape |
| `test_get_po_not_found_returns_404` | Missing PO |
| `test_download_po_returns_file` | FileResponse |
| `test_download_po_missing_file_returns_404` | File not on disk |
| `test_list_pos_for_rfx_endpoint` | Lists POs |
| `test_po_requires_buyer_role` | Vendor cannot access |

**New tests**: ~22

---

## Section 4: Agentic Chat Pipeline

**What this protects**: The chat agent is the primary user interface. Intent
detection errors mean wrong tools get called. Tool execution errors mean actions
silently fail. The agentic loop must respect limits and handle LLM failures.

### 4a. Intent Detection

**File**: `tests/unit/test_agent_intent.py` (new)

| Test | Asserts |
|------|---------|
| `test_create_rfx_english` | "I need 100kg rice" -> create_rfx |
| `test_create_rfx_hindi` | "mujhe 50kg atta chahiye" -> create_rfx |
| `test_dispatch` | "dispatch the RFx" -> dispatch_rfx |
| `test_cancel` | "cancel RFx #5" -> cancel_rfx |
| `test_evaluate` | "compare quotes" -> evaluate_offers |
| `test_award` | "award to vendor #2" -> award_rfx |
| `test_decline` | "can't supply" -> decline_rfx |
| `test_submit_quote` | "quote 78/kg" -> submit_quote |
| `test_list_rfx` | "show my rfx" -> list_rfx |
| `test_list_vendors` | "show vendors" -> list_vendors |
| `test_daily_summary` | "what happened today" -> daily_summary |
| `test_greeting` | "hello" -> ["__greeting__"] |
| `test_no_match` | "the weather is nice" -> [] |
| `test_empty_string` | "" -> [] |
| `test_mixed_multiple` | "I need rice, dispatch" -> [create_rfx, dispatch_rfx] |
| `test_case_insensitive` | "I NEED 100KG RICE" -> create_rfx |
| `test_deduplication` | Duplicate patterns -> one entry |
| `test_long_string_no_crash` | 1000+ chars -> no exception |

### 4b. Tool Selection Parsing

**File**: `tests/unit/test_agent_parsing.py` (new)

| Test | Asserts |
|------|---------|
| `test_valid_json_array` | Standard format parsed |
| `test_valid_single_dict` | Single tool parsed |
| `test_empty_object` | {} -> [] |
| `test_empty_array` | [] -> [] |
| `test_markdown_wrapped` | ```json [...] ``` parsed |
| `test_llm_preamble` | "Here are tools:\n[{...}]" parsed |
| `test_legacy_dict_format` | {"create_rfx": {...}} parsed |
| `test_invalid_json` | Random text -> [] |
| `test_deduplication` | Duplicates collapsed |
| `test_missing_tool_key` | Skipped |
| `test_non_dict_items` | Skipped |

### 4c. Tool Executor - targets Bug #5

**File**: `tests/unit/test_tool_executor.py` (new)

| Test | Asserts |
|------|---------|
| `test_happy_path` | ToolResult(success=True) |
| `test_unknown_tool_raises` | ValueError |
| `test_alias_resolution` | "search" -> "search_inventory" |
| `test_service_exception` | ToolResult(success=False) |
| `test_latency_positive` | latency_ms > 0 |
| `test_create_rfx_persists` | RFx in DB |
| `test_dispatch_rfx_status` | Status -> dispatched |
| `test_cancel_rfx_reason` | Reason persisted |
| `test_list_rfx_callers_only` | No cross-user leakage |
| `test_submit_quote_null_thread` | No orphaned message (Bug #5) |
| `test_evaluate_offers_with_quotes` | Returns quoted offers |
| `test_evaluate_offers_no_quotes` | Empty quoted list |
| `test_daily_summary_counts` | Counts correct |
| `test_clear_context` | Returns cleared flag |

### 4d. Agentic Pipeline

**File**: `tests/unit/test_agent_pipeline.py` (new)

| Test | Asserts |
|------|---------|
| `test_greeting_fast_path` | 1 LLM call, no tools |
| `test_tool_execution_flow` | LLM selects -> tool executes -> response |
| `test_multi_tool_execution` | 2 tools both execute |
| `test_continuation_after_create` | create_rfx triggers continuation |
| `test_continuation_stops_at_max` | Stops after max_iterations |
| `test_llm_call_budget` | Never exceeds max_llm_calls |
| `test_llm_selection_error` | Fallback message |
| `test_llm_response_error` | Tool-based fallback |
| `test_context_building_buyer` | Includes inventory/vendors/rfx |
| `test_context_building_vendor` | Includes RFx details |
| `test_context_building_empty` | "No data yet." |
| `test_sanitize_blocks_injection` | "ignore previous" -> "[redacted]" |
| `test_sanitize_preserves_normal` | Normal text unchanged |
| `test_sanitize_case_insensitive` | "IGNORE PREVIOUS" -> redacted |
| `test_history_truncation` | Respects limits |

### 4e. Tool Registry

**File**: `tests/unit/test_tool_registry.py` (new)

| Test | Asserts |
|------|---------|
| `test_buyer_excludes_vendor_only` | No vendor_only tools |
| `test_vendor_excludes_buyer_only` | No buyer_only tools |
| `test_admin_gets_all` | All tools |
| `test_all_tools_have_fields` | name, description, keywords non-empty |
| `test_no_duplicate_names` | Keys match .name |
| `test_tools_to_toon_valid` | Encodes without error |
| `test_filter_keywords_match` | Keyword matching works |
| `test_filter_no_match_fallback` | Returns first N |
| `test_filter_max_limit` | Respects max_tools |

**New tests**: ~68

---

## Section 5: Chat API Endpoints

**What this protects**: The chat API is the HTTP interface to the agent. It must
enforce auth, route to the correct agent, handle uploads, and return consistent
shapes.

**File**: `tests/unit/test_chat_api.py` (new)

| Test | Asserts |
|------|---------|
| `test_chat_requires_auth` | No session -> 401 |
| `test_chat_requires_buyer_or_vendor` | Admin -> 403 |
| `test_chat_buyer_uses_procurement_agent` | Correct agent |
| `test_chat_response_shape` | {message, data, success} |
| `test_chat_llm_error_returns_500` | LLM failure -> 500 |
| `test_chat_with_history` | History forwarded |
| `test_chat_with_rfx_id` | rfx_id forwarded |
| `test_create_rfx_requires_buyer` | Vendor -> 403 |
| `test_create_rfx_sku_exact_name` | Exact match |
| `test_create_rfx_sku_fuzzy` | ilike match |
| `test_create_rfx_sku_by_id` | Direct lookup |
| `test_create_rfx_missing_sku_skipped` | Unknown SKU skipped |
| `test_create_rfx_qty_convention` | qty/quantity/count |
| `test_create_rfx_unit_convention` | unit/unit_override |
| `test_create_rfx_suggested_vendors` | Vendors in response |
| `test_create_rfx_dispatch_plan` | Plan in response |
| `test_dispatch_uses_sourcing_agent` | SourcingAgent |
| `test_upload_rejects_oversized` | 413 |

**New tests**: ~18

---

## Section 6: Security and Access Control

**What this protects**: RBAC and IDOR are partially tested. This fills gaps
around cross-vendor isolation, prompt injection, and file validation.

### 6a. Cross-Vendor Isolation

| Test | Asserts |
|------|---------|
| `test_vendor_cannot_view_other_thread` | Vendor A != Vendor B |
| `test_vendor_cannot_quote_for_other` | Cross-vendor quote blocked |
| `test_vendor_cannot_decline_for_other` | Cross-vendor decline blocked |
| `test_vendor_inbox_own_only` | No data leakage |

### 6b. Prompt Injection

| Test | Asserts |
|------|---------|
| `test_ignore_previous_instructions` | Blocked |
| `test_you_are_now` | Blocked |
| `test_system_colon` | Blocked |
| `test_forget_everything` | Blocked |
| `test_normal_text_preserved` | Not over-redacted |
| `test_mixed_content` | Injection redacted, rest preserved |
| `test_multiple_injections` | All blocked |

### 6c. File Validation

| Test | Asserts |
|------|---------|
| `test_rejects_path_traversal` | `../../etc/passwd` sanitized |
| `test_rejects_null_bytes` | Null bytes stripped |
| `test_file_size_limit` | Configurable limit works |

**New tests**: ~14

---

## Section 7: Buyer API Endpoints

**File**: Expand integration tests

| Test | Asserts |
|------|---------|
| `test_list_rfx_shape` | Response shape |
| `test_get_rfx_detail_shape` | Includes vendor_offers, line_items |
| `test_get_rfx_not_found` | 404 |
| `test_cancel_rfx_success` | Cancel flow |
| `test_assign_vendors_success` | Assignment flow |
| `test_assign_vendors_invalid_ids` | 400 |
| `test_vendor_suggestions` | Endpoint works |
| `test_defaults_get_and_put` | CRUD |
| `test_activity_returns_logs` | Audit log shape |
| `test_award_po_failure_logged` | Not silent (Bug #2) |

**New tests**: ~10

---

## Section 8: Offer and Extraction Pipeline

**File**: Expand `tests/unit/test_offer_service.py`

| Test | Asserts |
|------|---------|
| `test_create_offer_basic` | Basic creation |
| `test_create_offer_revision_increments` | Revision number |
| `test_create_offer_supersedes_previous` | Previous superseded |
| `test_create_offer_fuzzy_sku_match` | Name matching |
| `test_create_offer_no_matching_sku` | Null line_item_id |
| `test_get_offers_for_rfx` | Non-superseded only |
| `test_get_offer_history` | All revisions |
| `test_override_offer_field` | Manual override |
| `test_override_nonexistent_raises` | ValueError |

**New tests**: ~9

---

## Section 9: Supporting Services

| Service | File | Tests | Purpose |
|---------|------|-------|---------|
| Inventory | test_inventory_service.py | 3 | Search edge cases, empty org |
| Auth | test_auth_service.py | 2 | Registration validation |
| Channels | test_channels_email_out.py | 2 | Email send mocking |
| Thread | test_thread_service.py | 2 | Message creation |
| Defaults | test_defaults_service.py | 1 | Default creation |
| Notification | test_notifications.py | 1 | Dispatch |

**New tests**: ~11

---

## Execution Order

### Phase 1: Bug-Catching Tests (Highest ROI)

Tests that expose the 7 known bugs were written first (failing against the
buggy code), then the bugs were fixed and the tests went green.

- Section 2a: Quote total calculation (Bug #1)
- Section 1a: State machine validation (Bug #3)
- Section 3a: PO rendering and fallback (Bugs #2, #6, #7)
- Section 4c: Null thread_id (Bug #5)

### Phase 2: Core Service Coverage

Broad coverage of `rfx_service.py` - the core state machine and CRUD paths.

- Section 1b: RFx CRUD edge cases
- Section 1c: Vendor suggestions and assignment
- Section 8: Offer service tests

### Phase 3: Agent Pipeline Tests

Agent pipeline covered using mocked LLMs and real DB sessions.

- Section 4a: Intent detection
- Section 4b: Tool selection parsing
- Section 4c: Tool executor
- Section 4d: Agentic pipeline
- Section 4e: Tool registry

### Phase 4: API and Integration Tests

- Section 5: Chat API
- Section 7: Buyer API
- Section 2b-2c: Vendor API
- Section 3b-3c: Award/PO API
- Section 6: Security

### Phase 5: Supporting Services and Polish

- Section 9: Supporting services
- Coverage verification
- PEP8/ruff pass

---

## Conventions

### PEP8 and Project Style

- **File naming**: `tests/unit/test_<module>.py` (snake_case, `test_` prefix)
- **Class naming**: `class TestFeatureName:` (CamelCase, `Test` prefix)
- **Method naming**: `def test_specific_behavior(self):` (descriptive, `test_` prefix)
- **Docstrings**: One-line docstring per test class and method
- **Line length**: 100 characters max
- **Imports**: Sorted by isort, first-party = `aeros`
- **Assertions**: Specific (`assert result.status == RFxStatus.DISPATCHED`)
  not generic (`assert result`)
- **Fixtures**: Shared from `conftest.py`; local fixtures at top of file
- **Mocking**: LLM calls ALWAYS via `AsyncMock`; use `_mock_chat_response()`
- **Independence**: No ordering dependencies between tests

### Ruff Rules (from pyproject.toml)

```
E, F, W, I, UP, B, SIM, S, A, C4, DTZ, T20, RUF
line-length = 100
```

---

## Verification

```bash
# Backend + Playwright E2E (sets WeasyPrint native lib path on macOS)
./app.sh test

# Backend only, with coverage report (enforces >=80%)
./app.sh test --pytest-only

# Lint
./app.sh lint

# A specific bug-catching test
uv run pytest tests/unit/test_po_agent.py -k "fallback" -v
```

### Success Criteria - Achieved

| Metric | Result |
|--------|--------|
| Overall coverage | 80.85% (≥80% enforced) |
| Total tests | 777 |
| Bug-catching tests | 7/7 pass |
| Ruff violations | 0 (`./app.sh lint`) |

---

## Critical Files (fixes applied)

| File | Change |
|------|--------|
| `src/aeros/services/rfx_service.py` | Status validation on `cancel_rfx`, `dispatch_rfx`, `award_rfx` |
| `src/aeros/api/vendor.py` | `submit_quote` total multiplies by line-item quantity |
| `src/aeros/api/buyer.py` | `award_rfx` logs PO errors instead of swallowing them |
| `src/aeros/agents/executor.py` | Guards against null `thread_id` |
| `src/aeros/agents/po.py` | HTML fallback served with correct content type |
