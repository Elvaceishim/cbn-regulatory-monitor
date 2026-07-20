# Using Playwright's official image rather than python:3.12-slim +
# manual `playwright install` — Chromium needs a long list of system
# libraries to actually run headless, and getting that list right by
# hand is exactly the kind of thing that silently breaks (see: Project 1's
# Docker Hardened Image dead end). The official image ships with
# everything needed already correctly installed.
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scraper.py main.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
