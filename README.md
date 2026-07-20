# CBN Regulatory Monitor

## Overview

The Central Bank of Nigeria publishes circulars, regulatory guidance, and 
press releases that can materially affect banks, fintechs, payment 
companies, and compliance teams.

The problem is that these updates are published on web pages rather than 
through a public API. Monitoring them manually means repeatedly checking 
multiple pages and hoping nothing important is missed.

This project automates that process.

A scheduled n8n workflow calls a FastAPI scraper service, collects newly 
published CBN documents, stores them in PostgreSQL, prevents duplicate 
processing, and sends Telegram alerts only when genuinely new regulatory 
content appears.

---

## Features

- Automated monitoring of CBN Circulars
- Automated monitoring of CBN Press Releases
- Playwright-powered scraping
- PostgreSQL-backed deduplication
- Audit trail for all discovered documents
- Dead-letter table for failed processing
- Telegram alert delivery
- Idempotent workflow execution

---

## Architecture

```text
n8n Schedule Trigger
        │
        ▼
FastAPI Scraper Service
        │
        ▼
Playwright Scraper
        │
        ▼
CBN Website
        │
        ▼
PostgreSQL
   ├─ Deduplication
   ├─ Audit Trail
   └─ Dead Letter Queue
        │
        ▼
Telegram Alerts
```

---

## Tech Stack

| Component | Technology |
|------------|------------|
| Workflow Orchestration | n8n |
| API Service | FastAPI |
| Scraping | Playwright |
| Database | PostgreSQL |
| Containerization | Docker Compose |
| Notifications | Telegram Bot API |

---

## Database Design

### `cbn_documents`

Stores all processed regulatory documents.

| Column | Description |
|----------|----------|
| id | Primary key |
| url | Unique document URL |
| title | Document title |
| sources | Source metadata |
| first_seen_at | Discovery timestamp |
| notified_at | Alert timestamp |

Deduplication is enforced through a database-level UNIQUE constraint on 
document URLs.

### `cbn_dead_letter`

Stores failed processing attempts for later investigation and replay.

---

## Testing Results

| Test | Status |
|--------|--------|
| Live Scraping | ✅ Passed |
| FastAPI Integration | ✅ Passed |
| PostgreSQL Persistence | ✅ Passed |
| Telegram Alerts | ✅ Passed |
| Message Chunking | ✅ Passed |
| Deduplication | ✅ Passed |
| End-to-End Workflow | ✅ Passed |
| Idempotency Verification | ✅ Passed |

### Dataset

- Documents discovered: **22**
- Documents inserted: **22**
- Duplicate URLs detected: **0**

### Idempotency Verification

The workflow was executed twice against the same live dataset.

**Before rerun**

```
22 documents
```

**After rerun**

```
22 documents
```

Results:

- No new database records created
- No duplicate alerts sent
- No duplicate URLs detected

This confirms the workflow can safely run on a schedule without repeatedly 
processing existing records.

---

## What Broke During Development

This project had more infrastructure debugging than either of my previous 
automation projects.

### Docker Storage Corruption

Docker builds repeatedly failed despite sufficient available disk space.

Root cause: Docker Desktop's internal storage state became inconsistent.

Resolution:

- Cleared builder cache
- Pruned Docker resources
- Restarted Docker Desktop
- Pulled fresh images

### Playwright Timing Issues

The CBN pages load content asynchronously.

Initial scraper runs occasionally returned incomplete results because 
extraction started before page content had fully loaded.

Resolution:

- Added explicit waits
- Added page readiness checks
- Re-tested against live pages

### Telegram Message Limit

The first successful run attempted to send all discovered documents in a 
single Telegram message.

Telegram rejected the request because the message exceeded its 
4096-character limit.

Resolution:

- Implemented message chunking
- Split alerts across multiple Telegram messages

### n8n Type Coercion Bug

The workflow's "Is New?" decision node appeared correctly configured but 
refused to route items as expected.

Root cause:

A data type mismatch between values being compared.

Resolution:

- Normalized data types before evaluation
- Verified routing behavior using real execution data

---

## Project Structure

```text
cbn-regulatory-monitor/
├── db/
│   └── init.sql
├── scraper/
│   ├── main.py
│   ├── scraper.py
│   ├── Dockerfile
│   └── requirements.txt
├── workflows/
│   └── cbn-monitor-pipeline.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Future Improvements

- Email notifications
- Slack integration
- Historical change tracking
- Document classification
- Regulatory topic tagging
- Monitoring dashboard

---

## Key Takeaway

This project was not built to demonstrate web scraping.

It was built to demonstrate how to design and operate a production-style 
monitoring workflow: collecting data from a source with no public API, 
handling failures, preventing duplicate processing, and delivering alerts 
only when action is required.
