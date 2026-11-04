# AI Lead Generator

A local-first AI Lead Generation Dashboard that uses **ScrapeGraphAI** for web scraping, **Google Gemini** for natural-language prompt understanding, and stores all leads in a persistent **CSV file**. Runs entirely on your Windows machine with no cloud hosting required.

## Features

- **Natural-language lead generation** — describe what businesses you want in plain English
- **Gemini-powered prompt understanding** — converts your prompt into a structured search configuration
- **Business discovery** — finds relevant websites using DuckDuckGo search
- **ScrapeGraphAI extraction** — uses AI to extract structured data from each website
- **Persistent CSV storage** — all leads saved to `data/leads.csv`, survives restarts
- **Duplicate detection** — prevents the same business from being added twice
- **Dark theme dashboard** — modern SaaS-style UI with teal accents
- **BYOK (Bring Your Own Key)** — your Google AI Studio API key, stored securely
- **Progress tracking** — real-time updates while scraping, with cancellation support
- **Lead management** — search, filter, sort, paginate, export (CSV/JSON), delete
- **Activity logs** — view application and API error logs with level filtering
- **Windows batch launchers** — double-click to set up, start, and stop

## Prerequisites

Install these before running Setup.bat:

| Requirement | Minimum Version | Download |
|---|---|---|
| Python | 3.12 | [python.org](https://www.python.org/downloads/) |
| Node.js | 18+ (LTS recommended) | [nodejs.org](https://nodejs.org/) |

When installing Python, check **"Add Python to PATH"** during installation.

## Installation

### Step 1: Run Setup

Double-click **`Setup.bat`** in the project folder. The script will:

1. Verify Python 3.12 and Node.js are installed
2. Create a Python virtual environment (`venv/`)
3. Install all Python dependencies (ScrapeGraphAI, FastAPI, etc.)
4. Install the Playwright Chromium browser (for web scraping)
5. Install Angular frontend dependencies
6. Build the Angular frontend
7. Create the `data/` and `logs/` directories
8. Initialize the CSV storage file

This takes several minutes on first run. Wait for the "Setup Complete" message.

### Step 2: Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with a Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIza...`)

The free tier provides generous usage for testing.

### Step 3: Start the Dashboard

Double-click **`Start Dashboard.bat`**. The script will:

1. Verify setup is complete
2. Start the FastAPI backend (serves both API and frontend)
3. Wait for the backend to be ready
4. Open your browser to `http://127.0.0.1:8765`

### Step 4: Configure Your API Key

1. In the dashboard, go to **API Settings** in the sidebar
2. Paste your Gemini API key
3. Click **Save Key**
4. Click **Test Connection** to verify it works
5. Select your preferred Gemini model (Flash models are faster and cheaper)

### Step 5: Generate Leads

1. Go to **Find Leads** in the sidebar
2. Enter a natural-language prompt, for example:

   ```
   Find 25 digital marketing agencies in Karachi, Pakistan.
   Extract: company name, owner name, website, public business email,
   phone number, city, business description.
   Only collect publicly available business information.
   ```

3. Click **Generate Leads**
4. Watch the progress bar as the pipeline runs:
   - Interpreting your prompt with Gemini
   - Discovering business websites via DuckDuckGo
   - Scraping each website with ScrapeGraphAI
   - Validating and deduplicating leads
   - Saving to CSV

5. View your leads in **All Leads** or check `data/leads.csv`

### Step 6: Stop the Dashboard

- Press any key in the Start Dashboard window, **or**
- Double-click **`Stop Dashboard.bat`**

Your leads and API key are preserved between sessions.

## Usage Guide

### Dashboard Page

Shows summary statistics: total leads, leads generated today, total/successful/failed searches, and the 10 most recent leads.

### Find Leads Page

Enter a natural-language prompt describing the businesses you want to find. The system uses Gemini to interpret your prompt and extract:
- Business type
- Location
- Number of leads requested
- Data fields to extract

Progress is displayed in real-time with stage indicators, website counts, and lead extraction stats. You can cancel a running job at any time.

### All Leads Page

View, search, filter, and manage all generated leads:

- **Search** by company name
- **Filter** by city or business type
- **Sort** by generated date, company name, city, or business type
- **Copy** email addresses with one click
- **Open** website links in a new tab
- **Delete** individual leads
- **Export** all or filtered leads as CSV or JSON
- **Paginate** through large datasets

### API Settings Page

Manage your Gemini API key and model selection:
- Enter, update, or remove your API key
- Show/hide the key while typing
- Test the connection with a real API call
- Select from available Gemini models

### Activity Logs Page

View application logs with filtering:
- Filter by log level (INFO, WARNING, ERROR)
- Adjust the number of lines displayed
- Refresh to get the latest logs

All secrets are automatically redacted from log entries.

### Application Settings Page

View system information, backend status, technology stack details, and security/privacy notes.

## Architecture

```
User Prompt
    |
    v
Gemini Prompt Understanding (google-genai SDK)
    |
    v
Structured Search Configuration
    |
    v
Business Discovery (DuckDuckGo via ddgs)
    |
    v
URL Validation & Deduplication
    |
    v
ScrapeGraphAI SmartScraperGraph (per URL)
    |
    v
Data Validation & Normalisation
    |
    v
Duplicate Detection (website + email)
    |
    v
CSV Storage (atomic writes + file locking)
    |
    v
Dashboard Display (real-time polling)
```

### How It Works

1. **Prompt Parsing**: Your natural-language prompt is sent to Gemini, which returns a structured JSON configuration (business type, location, limit, fields).

2. **Business Discovery**: DuckDuckGo search (via the `ddgs` package) finds websites matching your query. URLs are validated and deduplicated.

3. **Scraping**: For each discovered URL, ScrapeGraphAI's `SmartScraperGraph` loads the page with Playwright (headless Chromium), extracts the content, and uses Gemini to pull out the requested business fields.

4. **Data Validation**: Extracted data is normalised (field name mapping, email format validation, URL protocol fixing). Leads with no useful data are discarded.

5. **Deduplication**: New leads are checked against existing CSV records using website and email as the dedup key. Duplicates are skipped.

6. **CSV Storage**: New leads are appended to `data/leads.csv` using atomic writes (write to temp file, then rename) with file locking for concurrent-safe access.

7. **Progress Tracking**: The pipeline runs in a background thread. The frontend polls the status endpoint every 2 seconds for real-time updates.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Angular 20, TypeScript, Tailwind CSS |
| Scraping Engine | ScrapeGraphAI 2.3+ |
| AI Model | Google Gemini (via google-genai SDK) |
| Browser Automation | Playwright (Chromium) |
| Search | DuckDuckGo (ddgs) |
| Storage | CSV file with file locking |
| API Key Security | Windows Credential Manager (keyring) + DPAPI fallback |
| Testing | pytest, pytest-mock, pytest-asyncio |

## API Key Security

- Your API key is stored using **Windows Credential Manager** (via the `keyring` package)
- If Credential Manager is unavailable, falls back to **DPAPI-encrypted** local file storage
- The API key is **never** returned in any API response
- The API key is **never** stored in browser localStorage
- The API key is **automatically redacted** from all log entries
- API calls are restricted to the **local backend only** (127.0.0.1)
- The backend binds to **localhost only** — not accessible from the network

## Data Storage

All generated leads are stored in a single CSV file at `data/leads.csv` with these columns:

| Column | Description |
|---|---|
| lead_id | Unique identifier (auto-generated) |
| company_name | Business/company name |
| owner_name | Owner or founder name |
| website | Website URL |
| email | Public business email |
| phone | Phone number |
| city | City |
| country | Country |
| business_type | Type of business |
| description | Business description |
| source_url | URL the data was scraped from |
| search_query | The original prompt |
| generated_at | Timestamp of generation |

The CSV is the primary source of truth. The dashboard reads directly from this file — there is no separate in-memory database.

## Project Structure

```
AI-Lead-Generator/
├── Setup.bat                    # One-time setup script
├── Start Dashboard.bat          # Starts the application
├── Stop Dashboard.bat           # Stops the application
├── README.md                    # This file
├── .gitignore
├── .env.example
├── pytest.ini
│
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt         # Python dependencies
│   ├── api/
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── settings.py       # API key & model management
│   │       ├── leads.py         # Lead CRUD, search, export
│   │       ├── generation.py    # Lead generation pipeline
│   │       ├── dashboard.py     # Dashboard statistics
│   │       └── logs.py          # Activity logs
│   ├── services/
│   │   ├── gemini_service.py    # Gemini API key validation & prompt parsing
│   │   ├── discovery_service.py # DuckDuckGo business discovery
│   │   ├── scraping_service.py  # ScrapeGraphAI wrapper
│   │   ├── lead_service.py      # Pipeline orchestration
│   │   └── csv_service.py       # CSV storage with dedup & locking
│   ├── config/
│   │   └── settings.py          # App configuration
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   └── utils/
│       ├── logging_config.py    # Centralised logging with redaction
│       ├── security.py          # Input sanitisation, redaction
│       └── secure_storage.py    # API key storage (Credential Manager)
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.ts            # Root component with sidebar
│   │   │   ├── app.html          # Sidebar layout
│   │   │   ├── app.config.ts     # App providers
│   │   │   ├── app.routes.ts     # Route definitions
│   │   │   ├── core/
│   │   │   │   ├── models/       # TypeScript interfaces
│   │   │   │   └── services/     # Angular API services
│   │   │   └── pages/
│   │   │       ├── dashboard/
│   │   │       ├── find-leads/
│   │   │       ├── all-leads/
│   │   │       ├── api-settings/
│   │   │       ├── activity-logs/
│   │   │       └── app-settings/
│   │   ├── styles.css           # Global dark theme + Tailwind
│   │   └── main.ts
│   ├── angular.json
│   ├── tailwind.config.js
│   └── package.json
│
├── data/
│   ├── leads.csv                # All generated leads (primary storage)
│   └── app_config.json          # Non-secret app configuration
│
├── logs/
│   └── app.log                  # Application logs (rotating)
│
└── tests/
    ├── conftest.py              # Test fixtures
    ├── test_csv_service.py      # CSV operations tests
    ├── test_gemini_service.py   # Gemini validation & parsing tests
    ├── test_discovery_service.py # Discovery service tests
    ├── test_lead_service.py     # Pipeline orchestration tests
    └── test_api_endpoints.py   # API endpoint tests
```

## Running Tests

Tests use mocked APIs and do not consume real Gemini quota:

```bash
# Activate the virtual environment
venv\Scripts\activate

# Set the Python path
set PYTHONPATH=backend

# Run all tests
python -m pytest tests/ -v
```

Expected output: **79 passed**.

## Troubleshooting

### "Python 3.12 is not installed"

Install Python 3.12 from [python.org](https://www.python.org/downloads/). Make sure to check "Add Python to PATH" during installation. If you have multiple Python versions, the `py -3.12` launcher is used automatically.

### "Node.js is not installed"

Install Node.js LTS from [nodejs.org](https://nodejs.org/).

### "Port 8765 is already in use"

Another instance is already running. Either use the existing instance (it will open automatically) or run `Stop Dashboard.bat` first to free the port.

### "Backend failed to start"

Check `logs/app.log` for error details. Common causes:
- Missing dependencies (re-run `Setup.bat`)
- Playwright browser not installed (run `venv\Scripts\playwright install chromium`)
- Corrupted virtual environment (delete `venv/` and re-run `Setup.bat`)

### "API key test failed"

- Verify your key starts with `AIza...`
- Make sure you copied the entire key
- Check that the Gemini API is available in your region
- Verify you haven't exceeded the free tier quota
- Try selecting a different model in API Settings

### "No businesses found"

- Try a more specific prompt with a clear business type and location
- DuckDuckGo search may be rate-limited; wait a few minutes and try again
- Some locations may have fewer indexed businesses

### "Scraping failed for some websites"

This is expected — not all websites are scrapable. Websites may:
- Block automated access
- Require JavaScript rendering that fails
- Have anti-bot protection
- Be temporarily unavailable

Failed websites are logged and the pipeline continues with the remaining URLs.

### Frontend changes not reflected

If you modified Angular code, rebuild the frontend:
```bash
cd frontend
npm run build
```
Then restart the dashboard.

## Limitations

- **DuckDuckGo rate limits**: The discovery search may be rate-limited. The pipeline includes delays between requests.
- **Website accessibility**: Not all websites can be scraped. CAPTCHAs and anti-bot measures will cause individual failures, which are handled gracefully.
- **Data accuracy**: The system extracts publicly available information using AI. Results depend on website content quality. Missing fields remain empty — the system never fabricates data.
- **Local only**: The application runs on localhost. It is not designed for remote or multi-user access.
- **CSV storage**: CSV is efficient for moderate datasets. For very large datasets (100,000+ leads), consider migrating to a database.

## Privacy

- All data stays on your machine
- API calls go only to Google Gemini (for AI processing) and DuckDuckGo (for search)
- Your API key is stored in Windows Credential Manager
- No analytics, no telemetry (ScrapeGraphAI telemetry is disabled)
- Logs redact all secrets automatically

## License

This project uses ScrapeGraphAI (MIT License), Angular (MIT License), and other open-source libraries. See each library's license for details.
