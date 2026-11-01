---
name: rank
description: >
  Batch-scores and triages scraped job postings against the candidate fit framework.
  Evaluates postings on technical, experience, behavioral, and career dimensions,
  applies location and language gates, performs deadline expiry sweeps, and produces
  a prioritized shortlist.
  Triggers on: /rank, rank, rank jobs, rank postings, score jobs, shortlist jobs, triage jobs,
  batch score.
---

# /rank — Triage Scraped Jobs into a Ranked Shortlist

You are batch-scoring jobs collected by the scraper so the user can decide where to direct application efforts.
`/scrape` finds postings; `/apply` executes in-depth evaluation and document generation for a single role. `/rank` bridges them: it rapidly scores new postings against the candidate profile and produces a prioritized shortlist.

`/rank` produces **triage scores**, not final applications. It evaluates the posting text against candidate profile criteria without deep company research or the two-agent review loop (which are reserved for `/apply`).

---

## Execution Steps

### Step 0: Parse Input Arguments

Arguments may include:
- (empty): Rank up to 10 jobs with status `new` in `job_scraper/seen_jobs.json`.
- A focus term (e.g. `/rank data science`): Score only jobs matching the focus.
- `--all`: Re-rank all jobs not yet applied to (useful when the profile changes).
- `--limit <N>`: Maximum postings to score this run (default 10).
- `--top <N>`: Number of top matches to display in the shortlist (default 5).

---

### Step 1: Load Candidate Jobs via State Helper

Do not load all of `job_scraper/seen_jobs.json` directly into context. Query candidate jobs using `run_command`:

```bash
python3 tools/rank_state.py candidates --limit 10
# Append --all or --focus "<text>" if specified
```

This command automatically applies status filters, excludes positions already recorded in `job_search_tracker.csv`, and outputs compact JSON objects (`key`, `title`, `company`, `url`, `portal`, `deadline`, `posted_date`).

- **If no candidates exist**: Run the expiry sweep over existing ranked entries:
  ```bash
  python3 tools/rank_state.py sweep --write
  ```
  Present a sweep summary (closing soon, expired entries), suggest running `/scrape` for new jobs, and stop.

- **If candidates exist**: Read the evaluation rubric and candidate profile using `view_file`:
  - `.claude/skills/job-application-assistant/04-job-evaluation.md` (Weights: Technical 30%, Experience 25%, Behavioral 15%, Career 30%; Bands: Strong 75+, Good 60–74, Moderate 45–59, Weak 30–44, Poor <30).
  - `.claude/skills/job-application-assistant/01-candidate-profile.md` (Skills, experience domains, languages table).

---

### Step 2: Fetch and Score Postings

For each candidate job:
1. Fetch the posting content using `read_url_content`.
   - If HTTP 403 occurs, retry with browser headers via `run_command` and `curl` per `.claude/skills/job-application-assistant/09-web-research.md`.
   - If the URL is permanently dead or closed, mark the job as `expired`.
2. Score the posting strictly from verified content against the dimensions in `04-job-evaluation.md`:
   - **Technical Skills Match (0–100)**: Compare required/preferred stack against primary and secondary skills.
   - **Experience Match (0–100)**: Compare functional responsibilities against candidate work history.
   - **Behavioral & Culture Fit (0–100)**: Compare team setup and work style against `02-behavioral-profile.md`.
   - **Career Alignment & Motivation (0–100)**: Compare growth path against candidate career goals.
   - **Location Verdict**: `PASS`, `FAIL` (requires relocation), or `FLAG` (heavy travel).
   - **Language Gate**: `PASS`, `FAIL` (requires undeclared language), or `FLAG` (higher level than declared).
   - **Strengths & Gaps**: 1–3 grounded bullet points each.

Assemble the scored jobs into structured JSON format:
```json
{
  "key": "<job_key>",
  "status": "scored",
  "scores": { "technical": 85, "experience": 80, "behavioral": 75, "career": 80 },
  "location_verdict": "PASS",
  "language_gate": "PASS",
  "language_note": null,
  "deadline": "YYYY-MM-DD",
  "strengths": ["Direct match in PyTorch and MLOps"],
  "gaps": ["Kubernetes experience preferred but not daily"],
  "language": "English"
}
```

*Note: For batches >5 jobs, parallel scoring can also be delegated to subagents via `invoke_subagent`.*

---

### Step 3: Aggregate and Rank

Back in the main agent context:
1. Calculate the overall weighted score:
   $$\text{Score} = 0.30 \times \text{Tech} + 0.25 \times \text{Exp} + 0.15 \times \text{Behav} + 0.30 \times \text{Career}$$
2. Map to fit bands:
   - Strong Fit: 75–100
   - Good Fit: 60–74
   - Moderate Fit: 45–59
   - Weak Fit: 30–44
   - Poor Fit: <30
3. **Apply Vetoes**:
   - `location_verdict: FAIL` $\to$ Exclude from shortlist, list under Excluded.
   - `language_gate: FAIL` $\to$ Exclude from shortlist, list under Excluded with quoted requirement.
   - `FLAG` for location or language $\to$ Keep in ranking with a visible ⚠ marker.
4. **Urgency & Expiry**:
   - Deadline within 7 days $\to$ Mark with 🔥 and prioritize on score ties.
   - Past deadline $\to$ Mark `status: expired`.
   - Run background sweep over un-scored ranked entries:
     ```bash
     python3 tools/rank_state.py sweep --write --exclude "<comma_separated_keys_scored_now>"
     ```
   - If `posted_date` is >30 days old $\to$ Add staleness indicator ⚠.
5. Sort shortlisted postings descending by overall score.

---

### Step 4: Persist Results Atomically

1. Write the JSON results array to a temporary file (e.g. `scratch/rank_results.json` or `/tmp/rank_results.json`) using `write_to_file`.
2. Apply the updates to `job_scraper/seen_jobs.json` via `run_command`:
   ```bash
   python3 tools/rank_state.py apply --results "<path_to_temporary_file>"
   ```
   This updates `seen_jobs.json` atomically with `rank_score`, `rank_verdict`, `strengths`, `gaps`, and deadline updates.
3. Clean up the temporary file.

---

### Step 5: Present the Shortlist

Display the ranked results table:

```markdown
## Job Ranking — YYYY-MM-DD

Ranked X new postings (Y shortlisted, Z below threshold, W expired/vetoed).

| # | Score | Band | Title | Company | Location | Deadline | URL |
|---|-------|------|-------|---------|----------|----------|-----|
| 1 | 84/100 | Strong Fit | Machine Learning Engineer | Acme Corp | Remote | 2026-10-20 🔥 | [Link](...) |

### Top Matches Detail
- **#1 Machine Learning Engineer at Acme Corp (84/100)**:
  - **Strengths**: Direct PyTorch match; production pipeline track record.
  - **Gaps**: Kubernetes orchestration mentioned as preferred.
  - **Notes**: Remote-first team.
```

If postings were vetoed (relocation or undeclared language), list them briefly in an **Excluded** section.

Prompt the user:
> *"Which role would you like to apply to? Run `apply <number or URL>` to launch the tailored application workflow."*

