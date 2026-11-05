# MSL GA4 daily sync — recovery implementation

This restores the **upstream GA4 → Google Sheets sync**. It does not modify or reschedule the existing ChatGPT 18:30 daily report.

- GA4 property ID: **561684830**
- Target Sheet: https://docs.google.com/spreadsheets/d/13gd6ja4npcqHLu5mtPNJMy9u-HJwGPuC50qhRemM8c8/edit
- Script timezone: **America/Los_Angeles**
- Upstream refresh: **about 17:00 Pacific daily** (Apps Script clock triggers may be ±15 minutes).
- Query window: last **28 completed local dates** (through yesterday).
- A/B canonical page map: \`/marketing-simulation-lab/a/\` => A; \`/marketing-simulation-lab/scanner/\` => B.
- GA4 Data API is the authoritative source; zero traffic is *never* invented for unreturned dates.
- Upstream rows are only replaced **after all three API requests succeed**, leaving previous data if GA4 refuses access.
- \`Dashboard\` gains sync timestamp, data freshness, and dates GA4 didn't return; \`Sync_Log\` records successes/failures.

## Activation — one-time Google account consent required

The ChatGPT Google Drive connector cannot install Apps Script triggers or grant the Analytics OAuth scope. The spreadsheet owner must authorize the Apps Script project once; after that the refresh is unattended.

1. Open the Google Sheet → **Extensions → Apps Script** (use the Google account that can read GA4 property 561684830).
2. Replace the bound script code with [Code.gs](./Code.gs), and show the manifest in **Project Settings** → **Show "appsscript.json" manifest file in editor**. Replace its contents with [appsscript.json](./appsscript.json).
3. Run **installDailyMSLSync** in the Apps Script editor and approve its requested Google permissions. It immediately tests the GA4 API, refreshes \`Daily_Total\`, \`Daily_by_Page\`, \`Summary_by_Page\`, and only then installs a recurring trigger.
4. Verify that \`Dashboard!B2\` shows a recent timestamp and \`Sync_Log\` contains a **SUCCESS** row. Check **Triggers** for \`refreshMSLGA4\` and **Executions** for any errors.
5. If the run returns **403 / SERVICE_DISABLED**, enable **Google Analytics Data API** for the Apps Script linked Google Cloud project, then run again. If **403 / PERMISSION_DENIED**, verify the signed-in account can view GA4 property 561684830. If an OAuth consent warning appears, review the script source and required scopes.

The 17:00 upstream refresh is deliberately before the existing ChatGPT 18:30 Pacific reporting time. No private OAuth secrets or tokens are committed to the public repository.

**Important:** The old "MSL GA4 Daily Report" OAuth authorization record is NOT proof that a recurring script was installed; neither the old script nor its trigger is visible through the connected Drive interface.
