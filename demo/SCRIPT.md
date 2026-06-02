# AerOS - Live Demo Kit

Everything you need to run the live demo: a step-by-step script, the exact
co-pilot prompts to type, and a folder of sample vendor attachments in every
format the platform accepts.

- **Prompts & flow** → this file
- **Vendor attachments** → [`attachments/`](attachments/) (regenerate with
  `.venv/bin/python demo/generate_demo_files.py`)
- **Recorded walkthrough** → [`demo.mp4`](demo.mp4) - one
  continuous, captioned flow on a single RFx: Step 1 buyer signs in · Step 2
  buyer drafts the request in plain language (with an items table) · Step 3 the
  agent dispatches it and auto-invites matching vendors · Steps 4–5 two vendors
  reply (spreadsheet read by AI, then a scanned photo via vision) · Step 6 the
  buyer compares and awards. Each step has a title card naming the actor/account.

---

## 0. Pre-demo checklist (do this ~5 min before)

```bash
# 1. Fresh, clean demo data (RFx #1 offers map correctly for the comparison)
./app.sh stop
rm -f data/aeros.db data/aeros.db-shm data/aeros.db-wal
./app.sh upgrade && ./app.sh seed
./app.sh start          # backend :4040 · worker · frontend :5173

# 2. (Optional) regenerate the sample attachments
.venv/bin/python demo/generate_demo_files.py
```

Open <http://localhost:5173> in the browser you'll present from.

**Tips that avoid live surprises**
- In the co-pilot, **press `Enter` to send** (the Send button works too).
- The co-pilot reply takes ~5–15s (real LLM calls). Let it finish before the
  next prompt.
- Use one browser window for the buyer and a separate window/profile (or
  incognito) for the vendor so you can switch instantly without re-login.

### Demo accounts

| Role | Email | Password |
|---|---|---|
| Buyer | `buyer@aeros.demo` | `buyer123` |
| Vendor (Sabzi Mandi) | `sabzi@vendor.demo` | `vendor123` |
| Other vendors | `freshfarm@`, `metro@`, `kirana@`, `greenvalley@`, … `@vendor.demo` | `vendor123` |
| Admin | `admin@aeros.demo` | `admin123` |

The login page has one-click demo-credential buttons.

---

## 1. Buyer co-pilot (≈3 min)

Log in as **buyer**, open **Chat Co-pilot** (`/buyer/chat`). Type each prompt
and press Enter.

| # | Prompt | What the audience sees |
|---|--------|------------------------|
| 1 | `List the vendors that can supply dairy and produce.` | A live **Suggested vendors** table rendered by the agent |
| 2 | `Evaluate the offers for RFx #1 and show me the side-by-side comparison.` | A one-line takeaway **plus** a structured **Quote comparison** table (FreshFarm Dairy vs Kirana King) with lowest-price highlighting and a **Compare & award** action button |
| 3 | Click **Compare & award** on that block | Opens the full per-line-item comparison matrix for split award |

Optional extra prompts that also produce visual blocks:
- `I need 200kg tomatoes and 300 litres of milk by tomorrow` → drafts an RFx
- `Show my RFx` → lists all requests with status

> Talking point: *every* reply is a typed UI block (table / card / actions),
> not just text - and it's XSS-safe.

---

## 2. Vendor reply - format-agnostic intake (≈4 min)

This is the headline feature: a vendor can reply in **any** file format and
AerOS normalizes it into one structured offer.

Log in as **vendor** (`sabzi@vendor.demo`). Open the inbox → **Weekly Dairy &
Produce Replenishment - W23** (RFx #1, "Viewed", ~1 day left).

1. **Upload & Analyze** tab → drag in (or browse to) one of the sample files
   from [`attachments/`](attachments/). Good choices on stage:
   - `sabzimandi_quote.xlsx` (Excel) - matches this vendor
   - `greenvalley_pricelist.png` or `scanned_proforma.jpg` - show a
     **photo/scan** being read by the vision model (most impressive)
   - `metro_quote.pdf` (digital PDF) or `annapurna_quote.html` (email body)
2. Click **Ask AI about this document** → the vendor co-pilot replies with a
   card + a requested-items table extracted from the file.
3. Switch to **Quote Form**, confirm/adjust the prices, set payment/delivery,
   and click **Submit Quote**.

Then switch back to the **buyer** window and re-run prompt #2 - the new quote
now appears in the comparison.

> Talking point: PDF, Word, Excel, CSV, plain-text email, HTML email, and
> photographed/scanned price lists all collapse into the same `Offer` schema
> with per-field confidence scores.

---

## 3. Sample attachments (all quote RFx #1's four items)

Every file quotes the same line items so they line up in the comparison:
**Tomato 200 kg · Onion 150 kg · Full Cream Milk 300 ltr · Paneer 50 kg.**
Prices differ per vendor so "lowest price" highlighting is visible.

| File | Format / MIME | Plays the role of |
|---|---|---|
| `freshfarm_quote.csv` | CSV | Spreadsheet export |
| `sabzimandi_quote.xlsx` | Excel | Spreadsheet attachment |
| `kirana_quote.docx` | Word | Word document quote |
| `metro_quote.pdf` | PDF (text layer) | Digital PDF quotation |
| `dailyneeds_email.txt` | Plain text | Free-form email body |
| `annapurna_quote.html` | HTML | HTML email with a price table |
| `greenvalley_pricelist.png` | PNG image | Printed/screenshot price list |
| `scanned_proforma.jpg` | JPEG image | Scanned/photographed proforma |
| `vendor_pricelist.webp` | WebP image | Photo price list (WebP) |

All nine pass upload validation and extract through the real pipeline
(images/PDF via the vision LLM; the rest deterministically).

---

## 4. If something misbehaves

- **Co-pilot reply looks empty / "please share the offers"** - shouldn't happen
  after the latest fix; if it does, re-send prompt #2 (it now falls back to a
  deterministic tool call).
- **Comparison shows blank cells for a vendor** - the demo DB has stale data;
  re-run the reseed in section 0.
- **Upload rejected** - only the formats in section 3 are accepted; executables
  and unknown types are blocked by design (good security talking point).
