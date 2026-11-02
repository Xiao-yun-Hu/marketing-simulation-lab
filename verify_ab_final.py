"""
Final independent A/B verification against the LIVE deployed site.
20 genuinely isolated Playwright browser contexts (fresh profile each —
no shared localStorage/cookies). Observes real browser behavior only.
"""
import json
import time
import urllib.parse
from playwright.sync_api import sync_playwright

BASE = "https://xiao-yun-hu.github.io/marketing-simulation-lab/"
N_VISITORS = 20

def landed_variant(url: str) -> str:
    if "/a/" in url:
        return "a"
    if "/scanner/" in url:
        return "b"
    return "unknown:" + url

def ga_events(bucket):
    return [b["event"] for b in bucket]

results = {
    "fresh_assignment": [],
    "stickiness_failures": [],
    "v_override": [],
    "direct_visit_failures": [],
    "console_errors": [],
    "non_ga_failed_requests": [],
    "exposure_beacon_per_visitor": [],
}

with sync_playwright() as p:
    browser = p.chromium.launch()

    # Part 1: 20 fresh isolated visitors
    for i in range(N_VISITORS):
        ctx = browser.new_context()
        page = ctx.new_page()
        errs = []
        non_ga_fails = []
        ga_seen = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errs.append(f"pageerror:{e}"))

        def on_req(req, ga_seen=ga_seen):
            if "google-analytics.com/g/collect" in req.url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                ga_seen.append({"event": qs.get("en", ["?"])[0], "status": "initiated"})

        def on_fail(req, non_ga_fails=non_ga_fails, ga_seen=ga_seen):
            if "google-analytics.com" in req.url or "googletagmanager.com" in req.url:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(req.url).query)
                for s in ga_seen:
                    if s["event"] == qs.get("en", ["?"])[0] and s["status"] == "initiated":
                        s["status"] = f"failed:{req.failure}"
                        return
            else:
                non_ga_fails.append(f"{req.method} {req.url} -> {req.failure}")

        page.on("request", on_req)
        page.on("requestfailed", on_fail)

        page.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.6)  # let event_callback / timeout window fully resolve
        landed = landed_variant(page.url)
        results["fresh_assignment"].append({"visitor": i, "landed": landed})
        results["exposure_beacon_per_visitor"].append({"visitor": i, "ga_events_seen": ga_events(ga_seen), "detail": ga_seen})

        # Reload root in same context: must stay on same variant, no 404/loop/console error
        page.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed2 = landed_variant(page.url)
        if landed2 != landed:
            results["stickiness_failures"].append({"visitor": i, "case": "reload", "first": landed, "second": landed2})

        # New tab, same context (simulates close-and-reopen): must still be sticky
        page2 = ctx.new_page()
        page2.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page2.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed3 = landed_variant(page2.url)
        if landed3 != landed:
            results["stickiness_failures"].append({"visitor": i, "case": "new_tab_same_context", "first": landed, "third": landed3})
        page2.close()

        results["console_errors"].extend([f"visitor {i}: {e}" for e in errs])
        results["non_ga_failed_requests"].extend([f"visitor {i}: {f}" for f in non_ga_fails])
        ctx.close()

    # Part 2: ?v= overrides
    for forced in ["a", "b"]:
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(BASE + f"?v={forced}", wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed = landed_variant(page.url)
        ls = page.evaluate("()=>{try{return localStorage.getItem('msl_experiment_variant')}catch(e){return 'ERR'}}")
        results["v_override"].append({"forced": forced, "landed": landed, "localStorage_should_be_null": ls})
        ctx.close()

    # Part 3: direct /a/ and /scanner/ visits must not be rerouted, no console errors, no 404
    for path in ["a/", "scanner/"]:
        ctx = browser.new_context()
        page = ctx.new_page()
        errs = []
        statuses = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        resp = page.goto(BASE + path, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        final_url = page.url.split("?")[0]
        expected = BASE + path
        if final_url != expected:
            results["direct_visit_failures"].append({"path": path, "expected": expected, "got": final_url})
        if resp and resp.status >= 400:
            results["direct_visit_failures"].append({"path": path, "http_status": resp.status})
        if errs:
            results["console_errors"].extend([f"direct {path}: {e}" for e in errs])
        ctx.close()

    browser.close()

a_count = sum(1 for r in results["fresh_assignment"] if r["landed"] == "a")
b_count = sum(1 for r in results["fresh_assignment"] if r["landed"] == "b")
exposure_fired_count = sum(1 for v in results["exposure_beacon_per_visitor"] if "experiment_exposure" in v["ga_events_seen"])
exposure_missing = [v for v in results["exposure_beacon_per_visitor"] if "experiment_exposure" not in v["ga_events_seen"]]

summary = {
    "n_visitors": N_VISITORS,
    "a_count": a_count,
    "b_count": b_count,
    "exposure_beacon_fired_for_n_of_20": exposure_fired_count,
    "exposure_missing_detail": exposure_missing,
    "stickiness_failures": results["stickiness_failures"],
    "v_override_results": results["v_override"],
    "direct_visit_failures": results["direct_visit_failures"],
    "console_errors": results["console_errors"],
    "non_ga_failed_requests": results["non_ga_failed_requests"],
}
print(json.dumps(summary, indent=2))
with open("ab_verification_final.json", "w") as f:
    json.dump({"raw": results, "summary": summary}, f, indent=2)
