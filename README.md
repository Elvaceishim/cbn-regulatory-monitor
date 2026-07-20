# CBN Regulatory Monitor

## The Problem

The Central Bank of Nigeria publishes circulars and press releases that can materially affect banks, fintechs, payment companies, and compliance teams.

The challenge is that these updates are published on web pages rather than through a public API. Monitoring them manually means repeatedly checking multiple pages and hoping nothing important is missed.

I built an automated monitoring system that checks the CBN website daily, detects newly published documents, stores them in a database, and sends alerts only when genuinely new regulatory content appears.

## What This Project Does

- Scrapes CBN Circulars and Press Releases
- Detects newly published documents
- Stores documents in Postgres
- Prevents duplicate processing
- Sends Telegram alerts for new documents
- Maintains an audit trail of processed records
- Records failures in a dead-letter table for investigation

## Architecture

```text
Daily Trigger (n8n)
        │
        ▼
FastAPI Scraper Service
        │
        ▼
Playwright
        │
        ▼
CBN Website
        │
        ▼
Postgres
        │
        ├── Deduplication
        ├── Audit Trail
        └── Dead Letter Queue
        │
        ▼
Telegram Alerts

Tech Stack
n8n
Python
FastAPI
Playwright
PostgreSQL
Docker Compose
Telegram Bot API
Database Design
cbn_documents

Stores every processed document.

Column	Purpose
id	Primary key
url	Unique document URL
title	Document title
sources	Source metadata
first_seen_at	First discovery timestamp
notified_at	Alert timestamp

Deduplication is enforced with a database-level UNIQUE constraint on url.

cbn_dead_letter

Stores failed processing attempts for investigation and replay.

Testing Results
Test	Result
Live scraping	Passed
FastAPI integration	Passed
Postgres persistence	Passed
Telegram alerts	Passed
Telegram message chunking	Passed
Deduplication	Passed
End-to-end workflow	Passed
Idempotency test	Passed
Dataset
Documents discovered: 22
Documents inserted: 22
Duplicate URLs detected: 0
Idempotency Verification

The workflow was executed twice against the same live dataset.

Before rerun

22 documents

After rerun

22 documents

Results:

No new database records created
No duplicate alerts sent
No duplicate URLs detected

This confirms the workflow can safely run on a schedule without repeatedly processing existing documents.

What Broke During Development

This project turned out to be the most infrastructure-heavy automation project in the portfolio.

1. Docker Storage Corruption

Docker builds repeatedly failed despite sufficient host disk space.

Investigation showed Docker Desktop's internal storage state had become inconsistent.

Resolution:

Docker cleanup
Builder cache removal
Docker Desktop restart
Fresh image pulls
2. Playwright Timing Issues

The CBN pages load content asynchronously.

Initial scraper implementations occasionally returned incomplete results because extraction began before page content finished loading.

Resolution:

Added explicit waits
Improved page readiness checks
Re-tested against live pages
3. Telegram Message Length Limit

The first successful run attempted to send all discovered documents in a single Telegram message.

Telegram rejected the request because messages exceeded the 4096-character limit.

Resolution:

Implemented message chunking
Split large alert batches into multiple messages
4. n8n Type Coercion Bug

The workflow's "Is New?" decision node appeared correctly configured but did not route items as expected.

Root cause:

A data-type mismatch between values being evaluated

Resolution:

Normalized data types before evaluation
Verified branch behavior using real execution data
Project Structure
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
Future Improvements
Email alerts
Slack integration
Historical change tracking
Document classification
Regulatory topic tagging
Dashboard for monitoring trends
Key Takeaway

This project wasn't built to demonstrate web scraping.

It was built to demonstrate how to design and operate a production-shaped monitoring workflow: collecting data from a source with no API, handling failures, preventing duplicate processing, and delivering alerts only when action is required.
