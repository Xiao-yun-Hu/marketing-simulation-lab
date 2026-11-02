"""
Independent verification of the 50/50 A/B entry point at
https://xiao-yun-hu.github.io/marketing-simulation-lab/

Does NOT read or trust the deployed JS source for its conclusions — it only
observes real browser behavior through Playwright, using genuinely isolated
browser contexts (fresh profile, no shared storage) per visitor, the same way
Playwright is normally used for this kind of testing.
"""
import json
import time
from playwright.sync_api import sync_playwright

BASE = "https://xiao-yun-hu.github.io/marketing-simulation-lab/"
N_VISITORS = 20

results = {
    "fresh_assignment": [],       # (visitor_id, landed_path)
    "console_errors": [],
    "failed_requests": [],
    "stickiness_failures": [],
    "v_override_failures": [],
    "direct_visit_not_rerouted": True,
    "experiment_exposure_counts": [],  # per visitor: how many times experiment_exposure fired across refresh+reopen
}

def landed_variant(url: str) -> str:
    if "/a/" in url:
        return "a"
    if "/scanner/" in url:
        return "b"
    return "unknown:" + url

def attach_diagnostics(page, bucket_errors, bucket_failed):
    page.on("console", lambda msg: bucket_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: bucket_errors.append(f"pageerror: {exc}"))
    page.on("requestfailed", lambda req: bucket_failed.append(f"{req.method} {req.url} -> {req.failure}"))
    page.on("response", lambda resp: bucket_failed.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None)

def get_datalayer_events(page, name):
    try:
        return page.evaluate(
            """(name) => (window.dataLayer||[]).filter(e => Array.isArray(e) && e[0]==='event' && e[1]===name).length""",
            name,
        )
    except Exception as e:
        return f"eval_error: {e}"

with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---- Part 1: 20 fresh, isolated visitors through the unified entry point ----
    for i in range(N_VISITORS):
        ctx = browser.new_context()  # brand-new context = empty localStorage/cookies, no sharing with any other iteration
        page = ctx.new_page()
        errs, fails = [], []
        attach_diagnostics(page, errs, fails)
        page.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed = landed_variant(page.url)
        exposure_count = get_datalayer_events(page, "experiment_exposure")
        results["fresh_assignment"].append({"visitor": i, "landed": landed, "exposure_events_after_first_visit": exposure_count})

        # Stickiness: reload the ROOT again in the SAME context (same visitor) — must land on the same variant,
        # and must NOT fire a second experiment_exposure (same visitor, not a new assignment).
        page.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed2 = landed_variant(page.url)
        exposure_count2 = get_datalayer_events(page, "experiment_exposure")
        if landed2 != landed:
            results["stickiness_failures"].append({"visitor": i, "first": landed, "second_after_reload": landed2})
        results["experiment_exposure_counts"].append({"visitor": i, "after_visit1": exposure_count, "after_visit2_reload": exposure_count2})

        # Stickiness across "close and reopen": new page/tab in the SAME context (persisted localStorage), not a new context.
        page2 = ctx.new_page()
        errs2, fails2 = [], []
        attach_diagnostics(page2, errs2, fails2)
        page2.goto(BASE, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed3 = landed_variant(page2.url)
        if landed3 != landed:
            results["stickiness_failures"].append({"visitor": i, "first": landed, "third_new_tab_same_context": landed3})
        exposure_count3 = get_datalayer_events(page2, "experiment_exposure")
        if isinstance(exposure_count3, int) and exposure_count3 > 0:
            # a second real page view in the SAME context (same localStorage) should NOT log a fresh exposure
            results["experiment_exposure_counts"][-1]["new_tab_same_context_exposure_events"] = exposure_count3

        results["console_errors"].extend([f"visitor {i}: {e}" for e in errs + errs2])
        results["failed_requests"].extend([f"visitor {i}: {f}" for f in fails + fails2])
        page2.close()
        ctx.close()

    # ---- Part 2: ?v=a / ?v=b override accuracy, in a fresh isolated context each ----
    for forced in ["a", "b"]:
        ctx = browser.new_context()
        page = ctx.new_page()
        errs, fails = [], []
        attach_diagnostics(page, errs, fails)
        page.goto(BASE + f"?v={forced}", wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        landed = landed_variant(page.url)
        if landed != forced:
            results["v_override_failures"].append({"forced": forced, "landed": landed})
        # Overrides must NOT write localStorage / must NOT count as a real exposure
        ls = page.evaluate("() => { try { return localStorage.getItem('msl_experiment_variant') } catch(e){ return 'ERR:'+e } }")
        exposure_count = get_datalayer_events(page, "experiment_exposure")
        results["v_override_failures"].append({"forced": forced, "landed": landed, "localStorage_after_override": ls, "exposure_count": exposure_count, "note": "localStorage should be null and exposure_count 0 for a clean override"})
        results["console_errors"].extend([f"v={forced}: {e}" for e in errs])
        results["failed_requests"].extend([f"v={forced}: {f}" for f in fails])
        ctx.close()

    # ---- Part 3: direct visits to /a/ and /scanner/ must NOT be rerouted ----
    for path in ["a/", "scanner/"]:
        ctx = browser.new_context()
        page = ctx.new_page()
        errs, fails = [], []
        attach_diagnostics(page, errs, fails)
        page.goto(BASE + path, wait_until="networkidle", timeout=20000)
        time.sleep(0.3)
        if BASE + path != page.url.split("?")[0]:
            results["direct_visit_not_rerouted"] = False
            results["stickiness_failures"].append({"direct_visit": path, "ended_up_at": page.url})
        results["console_errors"].extend([f"direct {path}: {e}" for e in errs])
        results["failed_requests"].extend([f"direct {path}: {f}" for f in fails])
        ctx.close()

    browser.close()

# ---- Summarize ----
a_count = sum(1 for r in results["fresh_assignment"] if r["landed"] == "a")
b_count = sum(1 for r in results["fresh_assignment"] if r["landed"] == "b")
unknown = [r for r in results["fresh_assignment"] if r["landed"] not in ("a", "b")]

summary = {
    "n_visitors": N_VISITORS,
    "a_count": a_count,
    "b_count": b_count,
    "unknown_landings": unknown,
    "stickiness_failures": results["stickiness_failures"],
    "v_override_results": results["v_override_failures"],
    "direct_visit_not_rerouted": results["direct_visit_not_rerouted"],
    "console_errors": results["console_errors"],
    "failed_http_requests": results["failed_requests"],
    "exposure_event_detail": results["experiment_exposure_counts"],
}

print(json.dumps(summary, indent=2))
with open("ab_verification_result.json", "w") as f:
    json.dump({"raw": results, "summary": summary}, f, indent=2)
