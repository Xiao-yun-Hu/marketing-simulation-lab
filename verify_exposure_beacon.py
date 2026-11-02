"""
Targeted check: does the experiment_exposure GA4 beacon actually get SENT (not
necessarily "complete before redirect", but at minimum dispatched) from the
root entry page before it redirects to /a/ or /scanner/?

We capture every network request made while the ROOT page is loading (before
and during the redirect), and look for a Google Analytics "collect" request
whose query string names the event ('en=experiment_exposure' or
'en=page_view'). Whether that specific request shows as completed or
ERR_ABORTED in Playwright does not by itself tell us whether gtag used
sendBeacon (which survives navigation) — so we report both the request having
been *initiated* and, separately, its completion status, rather than
conflating the two.
"""
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright

BASE = "https://xiao-yun-hu.github.io/marketing-simulation-lab/go/"
N = 6

results = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    for i in range(N):
        ctx = browser.new_context()
        page = ctx.new_page()
        seen = []

        def on_request(req):
            if "google-analytics.com/g/collect" in req.url or "analytics.google.com" in req.url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                seen.append({"event": qs.get("en", ["?"])[0], "dl": qs.get("dl", ["?"])[0], "status": "initiated"})

        def on_requestfinished(req):
            if "google-analytics.com/g/collect" in req.url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                for s in seen:
                    if s["event"] == qs.get("en", ["?"])[0] and s["status"] == "initiated":
                        s["status"] = "completed"
                        break

        def on_requestfailed(req):
            if "google-analytics.com/g/collect" in req.url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                for s in seen:
                    if s["event"] == qs.get("en", ["?"])[0] and s["status"] == "initiated":
                        s["status"] = f"failed:{req.failure}"
                        break

        page.on("request", on_request)
        page.on("requestfinished", on_requestfinished)
        page.on("requestfailed", on_requestfailed)

        page.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.5)
        results.append({"visitor": i, "landed": page.url, "ga_requests_seen": seen})
        ctx.close()
    browser.close()

print(json.dumps(results, indent=2))
