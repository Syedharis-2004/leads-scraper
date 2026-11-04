# Fixing Zero Leads Generation Issue

## Problem
Your lead generator is showing zero leads because of these issues:

### 1. **Playwright Browsers Not Installed** ⚠️
The web scraper needs Playwright browsers to scrape websites, but they're missing.

**Error you'll see:**
```
BrowserType.launch: Executable doesn't exist at C:\Users\...\chrome-headless-shell.exe
```

### 2. **Port 8765 Already in Use** (Sometimes)
Another application might be using port 8765.

### 3. **Scraping Failures**
Even when discovery works, scraping fails without Playwright browsers.

## Solutions

### Step 1: Install Playwright Browsers
Run **`continue_playwright_install.bat`** in the project folder.

**What it does:** Downloads ~100MB of browser files (Chrome, Firefox, WebKit).
**Time required:** 5-10 minutes depending on your internet speed.

### Step 2: Check Current Status
Run **`test_lead_generation.bat`** to check:
- Is backend running?
- Is API key configured?
- Which model is selected?

### Step 3: Restart Application
1. Close any running instances
2. Run **`Start Dashboard.bat`**
3. Go to the web interface (http://127.0.0.1:8765)
4. Try generating leads again

## How It Should Work After Fix

1. **Prompt Parsing** ✅ - Already working
   - Your prompts like "Find cafes in London" are correctly interpreted by Gemini

2. **Business Discovery** ✅ - Already working  
   - Searches DuckDuckGo for relevant business websites

3. **Web Scraping** ✅ - Will work after Playwright install
   - Extracts contact info (name, email, phone, etc.) from websites

4. **Data Storage** ✅ - Already working
   - Saves leads to `data\leads.csv`

## Quick Test
After fixing Playwright, try this prompt:
```
Find 3 cafes in London
```

You should see:
- ✅ Prompt parsed successfully
- ✅ Businesses discovered (URLs found)
- ✅ Websites scraped (contact info extracted)
- ✅ Leads saved to CSV

## Troubleshooting

### If Playwright Installation Fails:
1. Check internet connection
2. Try: `python -m playwright install --with-deps`
3. Manual install: Download from https://playwright.dev/docs/browsers

### If Port 8765 is Busy:
1. Check what's using it: `netstat -ano | findstr :8765`
2. Kill the process or run on different port
3. Modify `backend\config\settings.py` to use different port

### If Still Getting Zero Leads:
1. Check `logs\app.log` for detailed errors
2. Try simpler prompts first
3. Verify Gemini API key has sufficient quota

## Success Indicators
- In logs: `Appended X leads, skipped Y duplicates`
- In CSV file: Rows with actual data (not just headers)
- In web interface: Leads shown in table

---

**Note:** The first lead generation might take 1-2 minutes as it needs to:
1. Parse your prompt with Gemini
2. Search for business websites  
3. Scrape each website for contact info
4. Validate and save the data