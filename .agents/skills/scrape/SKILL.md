---
name: scrape
description: >
  Finds new job postings matching the candidate profile using installed portal-search CLIs
  in .agents/skills/ (LinkedIn, Freehire, and local boards) with fallback to web search.
  Deduplicates across runs, performs quick fit assessments, generates networking search links,
  and records seen postings.
  Triggers on: /scrape, scrape, job scrape, find jobs, search jobs, new jobs, job search,
  scrape jobs, check new positions.
---

# Job Scraper

You are searching for job postings matching the candidate's profile using the installed portal-search CLIs in `.agents/skills/` (with web search fallback). You deduplicate against previously seen jobs and the application tracker, and present new matches with a quick fit assessment.

---

## Execution Steps

### Step 0: Load State

1. Read `job_scraper/seen_jobs.json` using `view_file` (create via `write_to_file` if missing: `{"seen": {}}`).
2. Read `job_search_tracker.csv` using `view_file` to extract already-applied companies and roles (match case-insensitively).
3. Read `.claude/skills/job-scraper/search-queries.md` using `view_file` for the configured search strategy, role priorities, and geographic tiers.
4. Read the Languages table in `.claude/skills/job-application-assistant/01-candidate-profile.md` and the Language Gate in `.claude/skills/job-application-assistant/04-job-evaluation.md` to know the candidate's working languages.

### Step 1: Search Strategy & Execution

By default, run the top 3 priority query categories from `search-queries.md`.
- If the user specified a focus area (e.g. `/scrape data science`), prioritize queries from that category.
- If the user said `broad`, run all priority categories.
- If the user said `health` (e.g. `/scrape health` or `/scrape health jobnet`), jump directly to Step 4.75 (Portal Health Check) and exit after diagnosis.

#### 1a. Check Bun availability
Run `bun --version` using `run_command`.
- If `bun` is available, proceed to **1b (CLI Search)** as primary.
- If `bun` is not available, proceed to **1c (Web Search Fallback)** and note in the summary that search ran via web fallback.

#### 1b. Run CLI tools (Primary)
Inspect all installed portal skills in `.agents/skills/*/SKILL.md` using `view_file`.
Only execute portals where `enabled: true` (or where `enabled` is omitted, which defaults to true).
Skip portals with `enabled: false` (such as default disabled demo portals).

For each enabled portal skill:
1. Check its `SKILL.md` for exact CLI syntax and flags.
2. Translate query terms from `search-queries.md` into that portal's CLI flags (`--query`, `--location`, `--region`, etc.).
3. Scope to the last 14 days where supported (`--jobage 14`, `--since`, etc.) or filter client-side by the `date` field.
4. Cap results to ~20 per query using `--limit 20`.
5. Specify `--format json` for structured machine-readable output.
6. Execute CLI commands via `run_command`:
   ```bash
   bun run .agents/skills/<portal>/cli/src/cli.ts search [flags]
   ```
   Run independent searches where appropriate. If a CLI returns a non-zero exit code, log the error and continue with remaining searches.

#### 1c. Web Search Fallback
Use `search_web` for:
- Portals listed in `search-queries.md` that do not have a CLI skill.
- Any portal whose CLI failed at runtime.
- When `bun` is unavailable.
Use `site:` queries defined in `search-queries.md`.

---

### Step 2: Fetch & Parse Detail

For each promising search result:
- **CLI results**: Search output already includes title, company, location, date, and URL. For strong candidates, fetch full details with the portal's `detail` command:
  ```bash
  bun run .agents/skills/<portal>/cli/src/cli.ts detail <id|url> --format json
  ```
  **Closed-at-source detection**: If `detail` returns `isActive: false` (e.g. on LinkedIn), the posting is closed. Record it in `seen_jobs.json` with `"status": "expired"` and exclude it from presentation.
- **Web search results**: Retrieve the posting page with `read_url_content`. If HTTP 403 occurs, retry with browser headers via `run_command` and `curl` per `.claude/skills/job-application-assistant/09-web-research.md`.

**Filter candidates**:
- Skip if the URL already exists in `job_scraper/seen_jobs.json`.
- Skip if the company + title combination already exists in `job_scraper/seen_jobs.json`.
- Skip if the company + role already appears in `job_search_tracker.csv`.

---

### Step 2.5: Mass-Posting Detection
If multiple results from this run share substantially identical job descriptions across different cities/regions or share the same requisition ID, consolidate them into a single row with an explicit notation: e.g. "Frontend Engineer (posted across 6 cities)". Do not auto-reject, but flag for the user's attention.

---

### Step 3: Quick Fit Assessment

For each new posting, perform a rapid fit check:
- **High match**: Directly involves core skills from `01-candidate-profile.md`.
- **Medium match**: Adjacent to candidate experience and transferable skills.
- **Low match**: Requires substantial skills candidate lacks.

**Language Gate Override**:
Apply the Language Gate from `04-job-evaluation.md`:
- If a posting requires a working language NOT declared in the candidate's Languages table in `01-candidate-profile.md`: mark as **Low match** regardless of skills, and highlight the language requirement.
- If a posting requires a declared language at a higher level than candidate's level: score fit normally, but add a ⚠ warning note.

---

### Step 4: Deduplicate & Store

1. Derive the canonical key for each posting using `run_command`:
   ```bash
   python3 tools/job_key.py --company "<company>" --title "<title>" --url "<url>"
   ```
2. Save newly fetched and skipped postings to `job_scraper/seen_jobs.json`:
   ```json
   {
     "seen": {
       "<canonical_key>": {
         "title": "...",
         "company": "...",
         "url": "...",
         "first_seen": "YYYY-MM-DD",
         "posted_date": "YYYY-MM-DD",
         "deadline": "YYYY-MM-DD",
         "fit": "high/medium/low",
         "status": "new",
         "portal": "<portal_name>",
         "source": "cli"
       }
     }
   }
   ```
   Preserve existing entries and any ranked fields (`rank_score`, `strengths`, `gaps`, etc.).

---

### Step 4.5: Generate Networking Links (High & Medium Fit)

For each new **High** and **Medium** match, construct two LinkedIn search links for the user:
1. **Recruiter / Talent Acquisition link**:
   `https://www.linkedin.com/search/results/people/?keywords=<url-encoded "<Company Name> recruiter">&origin=GLOBAL_SEARCH_HEADER`
2. **Team Peer link**:
   `https://www.linkedin.com/search/results/people/?keywords=<url-encoded "<Company Name> <role keyword>">&origin=GLOBAL_SEARCH_HEADER`

*Note: Never programmatically scrape LinkedIn people search pages; these links are strictly for the user to open.*

---

### Step 4.75: Portal Health Check

If inspecting results reveals parsing degradation (empty company names, undecoded HTML entities, zero results where historical runs produced results):
- Probe the portal CLI once with its SKILL.md test query capped at 3 results.
- If broken, flag in the summary: `health: <portal> - degraded / broken`.
- If `scrape health` was called directly, test all installed portals, report diagnostic verdicts, and stop.

---

### Step 5: Present Results

Output a markdown table sorted by fit (High first):

```markdown
## New Job Matches — YYYY-MM-DD

Found X new positions (Y high, Z medium, W low match).

| # | Fit | Title | Company | Location | Deadline | URL |
|---|-----|-------|---------|----------|----------|-----|
| 1 | High | ... | ... | ... | ... | [Link](...) |

### High-Match Highlights
- **[Title] at [Company]**:
  - Why it matches: ...
  - Key requirements to note: ...
  - Networking links: [Recruiter Search](...) | [Peer Search](...)
```

After presenting:
- Offer: *"Want me to evaluate any of these in detail or prepare an application? Specify the number or URL."*
- If 8+ new jobs were found, suggest running `/rank` to batch-score and prioritize a ranked shortlist.

