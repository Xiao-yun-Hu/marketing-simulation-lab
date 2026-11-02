# GEO / Agent Search Test Plan — Marketing Simulation Lab

**Purpose:** Track whether Marketing Simulation Lab is retrieved, cited, mentioned or recommended by AI assistants (ChatGPT, Claude, Perplexity, Gemini/Google AI, Copilot, Muse) in response to realistic queries about synthetic consumers / consumer behavior simulation. This is a measurement plan, not a guarantee — no page structure, schema or llms.txt file guarantees ranking, citation or recommendation by any AI system. See [arXiv:2311.09735](https://arxiv.org/abs/2311.09735) for what "Generative Engine Optimization" techniques actually measured (visibility inside generated answers, not search-ranking position).

**Status:** This plan and the 12-prompt portfolio were prepared in this session. The actual cross-platform runs (5 runs × 12 prompts × 6 platforms = 360 runs) were **not** executed here — Marketing Simulation Lab has no API access configured in this environment for ChatGPT, Perplexity, Gemini, Copilot or Muse, and running real queries against each platform's consumer UI is outside what this session can do safely and repeatably. Rachel (or a follow-up session with the right accounts/API access) should run this plan and log results in the tracking table below.

## Methodology

- Run every prompt **5 times per platform**, on separate sessions/days where possible, to avoid judging a platform by one lucky or unlucky draw.
- For each run, record one of: **Retrieved** (the assistant appears to have fetched/read our site, inferred from specific accurate detail), **Cited** (our URL or domain appears as a source/link), **Mentioned** (Marketing Simulation Lab named without a link), **Recommended** (suggested as a solution to the user's stated problem), or **Not Found**.
- Don't judge a platform from a single run — report the 5-run rate per prompt per platform (e.g. "cited 2/5").
- Use incognito/fresh sessions where the platform allows it, so prior chat history doesn't bias retrieval.
- Note the date — these answers will drift as content gets indexed, re-crawled, or as competitors change their own content.

## The 12-prompt portfolio

Covers: definition, method/how-to, business/vendor-selection, limitations/skepticism, and direct comparison — the shapes of query a prospect or researcher would plausibly type.

### Definition
1. "What are synthetic consumers in market research?"
2. "What's the difference between a synthetic consumer, a persona, and a digital twin?"

### Method / how-to
3. "How does consumer behavior simulation work for e-commerce landing pages?"
4. "How can I use AI to simulate how shoppers react to a product page before I run an A/B test?"
5. "What's the process for diagnosing why an e-commerce product page isn't converting, using simulated customers?"

### Business / vendor selection
6. "What companies offer synthetic consumer research or AI-simulated focus groups?"
7. "Is there a tool that simulates consumer behavior to help prioritize A/B tests?"
8. "Who does consumer behavior simulation for e-commerce teams?"

### Limitations / skepticism
9. "Are LLM-simulated consumers actually reliable, or just plausible-sounding?"
10. "What are the risks of relying on synthetic consumer research instead of real user testing?"

### Comparison
11. "Synthetic consumer research vs. a real A/B test — which should I trust more, and when?"
12. "Compare synthetic consumer simulation tools for e-commerce."

## Competitive context (for interpreting results)

Real, currently-live adjacent products researched for this plan (not copied, for context only):
- **Synthetic Users** (syntheticusers.com) — AI-generated synthetic participants for product/UX research interviews. Independently reviewed (critically) by Nielsen Norman Group, which found some of its marketing claims overstated and recommended treating outputs as hypotheses, not evidence.
- Perspective AI (getperspective.ai) and Autentic AI appeared repeatedly in 2026 category coverage as synthetic-focus-group vendors — found only via their own content/secondary press, not independently verified by a third party; treat as real but lower-confidence.

If assistants cite these competitors but not Marketing Simulation Lab, that's a content-gap signal, not evidence our content is wrong — check whether they're simply older/more indexed, and consider it a reason to keep publishing dated, sourced research notes (see `/research/`) rather than copying their positioning.

## Tracking table (fill in per run)

| # | Prompt | Platform | Date | Retrieved | Cited | Mentioned | Recommended | Notes |
|---|--------|----------|------|-----------|-------|-----------|--------------|-------|
| 1 | | ChatGPT | | | | | | |
| 1 | | Claude | | | | | | |
| 1 | | Perplexity | | | | | | |
| 1 | | Gemini | | | | | | |
| 1 | | Copilot | | | | | | |
| 1 | | Muse | | | | | | |
| … | (repeat rows 2–12) | | | | | | | |

Copy this table (or import it into a spreadsheet) and fill in 5 rows per platform per prompt — this table shows the row shape, not all 360 rows, to keep the file manageable.

## After a round of testing

- Compute, per prompt, the cited/recommended rate across platforms — this tells you which query *shapes* are working and which aren't.
- Compute, per platform, the overall rate — this tells you which platform is hardest to reach (often the one with the least frequent re-crawl, or the one leaning most on already-indexed competitors).
- Re-check `/robots.txt`, `/sitemap.xml`, `/llms.txt` are still reachable (`curl -s -o /dev/null -w "%{http_code}\n" <url>`) before concluding a platform "isn't retrieving us" — a deploy regression is a more common cause than content quality.
- Treat zero citations after one round as inconclusive, not failure — re-crawl cycles for some of these platforms can take weeks. Re-run the full portfolio no sooner than 2-3 weeks after the first round.
