---
name: outcome
description: >
  Records progress updates (interview stages, offers) and final resolutions (hired, rejected,
  no response, withdrawn) for tracked job applications. Maintains job_search_tracker.csv,
  archives submitted materials and outcome logs in documents/applications/<company>_<role>/,
  handles polite follow-up drafting, and sweeps stale quiet applications.
  Triggers on: /outcome, outcome, record outcome, application status, followup, stale applications.
---

# /outcome — Record the Result of an Application

You are recording what happened to a job application in Google Antigravity: progress updates (interview invitations, stages completed, offers) and final resolutions (hired, rejected, no response, withdrawn).

The data lands in two places the framework reads:
- `job_search_tracker.csv` — the status column that `/scrape` and `/rank` use for dedup and exclusion.
- `documents/applications/<company>_<role>/` — the per-application archive (posting, submitted drafts, `outcome.md`) that `/setup` Path A mines to calibrate evaluation criteria and surface STAR candidates.

`/outcome` writes the data; `/setup` interprets it. This skill never edits the evaluation framework (`04-job-evaluation.md`) or candidate profile files directly.
The skill also manages follow-ups for open applications that have gone quiet, drafts brief follow-up notes in the user's voice, and sweeps stale open applications.

Follow these steps **in order**.

---

## Step 0: Parse Input

Command arguments may specify:
- **Nothing**: List open applications and prompt user to select which one to update.
- **`<company>` or `<company> <role>`** (e.g. `outcome acme` or `outcome acme ml engineer`): Target that application.
- **`followup`**: Enter the follow-up branch (Step 2b) for quiet open applications using the default threshold of **10 days**.
- **`followup <N>`** (e.g. `outcome followup 14`): Follow-up branch with an N-day threshold.
- **`followup <company>`**: Draft a follow-up for that company's application immediately, regardless of threshold.
- **`stale` or `sweep`**: Enter the stale application sweep branch (Step 2c) for applications quiet for **60+ days**.
- **`stale <N>` or `sweep <N>`** (e.g. `outcome stale 90`): Stale sweep branch with an N-day threshold.

---

## Step 1: Load State and Identify the Application

1. **Check Tracker CSV**: Read `job_search_tracker.csv` using `view_file`. If it does not exist, create it via `write_to_file` with the standard header:
   ```csv
   date,company,sector,role,role_type,channel,status,contact_person,fit_rating,notes,cv_file,cover_letter_file,source,deadline
   ```
   **If the file exists and its header does not end in `,deadline`, append `,deadline` to the header line only** — leave all existing data rows intact (legacy rows read with empty deadline).
2. **With Company / Role Argument**: Match rows case-insensitively on company (and role, if specified).
   - One match: proceed with this application.
   - Multiple matches: list matching rows and ask user to choose.
   - Zero matches: the application was submitted outside the workflow; prompt the user for company, role, date applied, channel, contact person, and posting URL, and append a tracker row.
3. **Without Argument (Interactive List)**: List all rows whose status is not final (see **Tracker Status Vocabulary** below) as a numbered table:
   - Columns: `#`, `Company`, `Role`, `Date Applied`, `Current Status`, `Deadline`, `Days Quiet`, `Follow-ups Sent`.
   - **Days quiet**: counts elapsed days from `date` or the most recent dated note in `notes`.
   - **Follow-ups sent**: counts `followed up YYYY-MM-DD` markers in `notes`.
   - **`drafted` rows**: list under a separate heading ("Drafted, not yet submitted"); leave days quiet and follow-ups sent blank.
   - **Deadline alerts**: display deadline when present. Flag deadlines within 7 days with 🔥, and passed deadlines with ⚠.
   - If any open submitted row is 10+ days quiet with fewer than 2 follow-ups, suggest: *"Some of these have gone quiet — want a follow-up draft? (Step 2b)"*.
   - If any open rows are 60+ days quiet, offer: *"You have applications quiet for 60+ days — run `outcome stale` to batch-resolve them (Step 2c)."*.
   - If all applications are resolved, report that the tracker is completely resolved and stop.
4. **Derive Archive Subfolder**: `documents/applications/<company>_<role>/` following the naming rule:
   - Lowercase, spaces converted to underscores, keep only alphanumeric characters and underscores, collapse consecutive underscores, trim leading/trailing underscores.
   - Check if the subfolder and `outcome.md` exist (updating vs creating).

---

## Tracker Status Vocabulary

Canonical spellings for `job_search_tracker.csv` `status` column (lowercase, underscores, never spaces):

`drafted` | `applied` | `interview` | `offer` | `hired` | `rejected` | `no_response` | `offer_declined` | `withdrawn`

- **Final (Closed)**: `hired`, `rejected`, `no_response`, `offer_declined`, `withdrawn`
- **Open (Active)**: `drafted`, `applied`, `interview`, `offer`
- **Legacy Readers**: Read both `no_response` and legacy `no response`, `offer_declined` and `offer declined`. Never write spaces when updating.

*(Note: Distinct from the archive `outcome.md` `Status:` enum in `documents/README.md`: `in_progress` | `hired` | `offer_declined` | `rejected` | `no_response` | `interview_only`).*

---

## Step 2: Collect What Happened

Ask the user what happened, then classify:

**Progress Updates (Application remains Open):**
- Interview invitation / round scheduled or completed (phone screen, technical, case, hiring manager, final round)
- Offer received (under consideration)

**Resolutions (Application Closed):**
- `hired`: Accepted an offer.
- `offer_declined`: Received an offer, turned it down.
- `rejected`: Explicit rejection at any stage.
- `no_response`: No reply received; let the user decide whether to close it.
- `interview_only`: Completed interview rounds but process stalled or abandoned without explicit rejection.
- `withdrawn`: Candidate withdrew application.

Collect brief details without interrogation:
- Dates for the stages reached.
- Feedback received (quote verbatim where remembered).
- Reflections: what candidate would do differently, what the company valued.

---

## Step 2b: Follow-Up Branch (Chase Quiet Applications)

Enter via `outcome followup` or when triggered from Step 1.3.

1. **Identify Candidates**: Applications with status `applied` or `interview`, elapsed days quiet >= threshold (default 10 days), and fewer than 2 follow-ups logged. Skip rows with unparseable dates with a warning.
2. **Drafting Principles (Zero Fabrication / No New Claims)**:
   - View `documents/applications/<company>_<role>/`: `job_posting.md`, `cv_draft.tex`, `cover_letter.tex`.
   - All claims must be grounded in the submitted materials — do not introduce new experience or skills.
   - Follow writing guidelines from `.claude/skills/job-application-assistant/03-writing-style.md` (warm, direct, concise, no cliches).
   - Match language and register from the submitted cover letter.
   - Length: **60 to 120 words**.
   - Structure: address `contact_person` (or team); 1 sentence restating enthusiasm for specific role; 1 concrete value reminder grounded in submitted documents; 1 polite question regarding hiring timeline.
   - Format tailored to channel: email (with subject line), LinkedIn message (concise, no subject), portal message.
3. **Review & Iterate**: Present the draft to the user and iterate upon request.
4. **Logging**: When user confirms sending:
   - Append `followed up YYYY-MM-DD` to the row's `notes` in `job_search_tracker.csv`.
   - Save the note to `documents/applications/<company>_<role>/followup_YYYY-MM-DD.md`.
5. **Termination**: If an application already has 2 logged follow-ups, do not offer a third. Suggest closing as `no_response`.

---

## Step 2c: Stale Sweep Branch (Batch-Resolve Quiet Applications)

Enter via `outcome stale [N]` or `outcome sweep [N]`.

1. **Filter Candidates**: Open submitted applications (`applied` or `interview`), days quiet >= threshold (default 60 days, or user-provided N). Exclude `drafted`.
2. **Review Table**: Present candidate applications:
   ```markdown
   ## Stale Applications ([K] quiet for [N]+ days)

   | # | Company | Role | Date Applied | Days Quiet | Follow-ups Sent | Current Status | Proposed Status |
   |---|---------|------|--------------|------------|-----------------|----------------|-----------------|
   | 1 | Acme    | SWE  | 2026-05-10   | 118        | 2               | applied        | no_response     |
   ```
3. **User Confirmation Required**:
   Prompt user for action:
   - `all`: mark all listed applications as `no_response`.
   - `select`: resolve specific numbers (e.g. `1, 3` or `1-4`).
   - `skip`: abort without making changes.
   *Do not write changes until the user gives explicit confirmation.*
4. **Execution**:
   - Update `job_search_tracker.csv`: set `status` to `no_response`, append `stale resolved no_response (YYYY-MM-DD)` to `notes`.
   - Update `documents/applications/<company>_<role>/outcome.md` with `Status: no_response`, `Date resolved: YYYY-MM-DD`, and note the stale resolution.
5. **Calibration Trigger**: If 3 or more applications were resolved in this sweep, proceed to Step 5.

---

## Step 3: Archive Application Materials

Create or update `documents/applications/<company>_<role>/`:

1. **Archive Submitted CV & Cover Letter**:
   - Copy (never move) submitted files referenced by `cv_file` and `cover_letter_file` from tracker row, or matching `cv/main_<company>_<role>.*` and `cover_letters/cover_<company>_<role>.*`.
   - Save as `cv_draft.tex` and `cover_letter.tex`.
   - If files already exist in archive, preserve them (the archived file represents what was actually submitted).
2. **Archive Job Posting**:
   - If `job_posting.md` exists, leave untouched.
   - If absent and a source URL is in the tracker, fetch using `read_url_content` or `search_web`.
   - If the URL is unavailable or bot-protected, prompt the user to provide the posting text or write a stub noting posting unavailable. Never fabricate posting text.
3. **Write / Update `outcome.md`**:
   Follow the canonical schema:
   ```markdown
   # Outcome: <Company> — <Role>

   **Status:** in_progress | hired | offer_declined | rejected | no_response | interview_only

   **Date resolved:** YYYY-MM-DD

   ## Interview stages reached
   - [x] Phone screen (YYYY-MM-DD)
   - [ ] Technical interview
   - [ ] Case interview
   - [ ] Final round
   - [ ] Offer received

   ## Notes
   - YYYY-MM-DD: <Notes, feedback, reflections>
   ```
   *Tick checkboxes as stages are completed, appending the date. Append new entries to `## Notes` with dates.*
4. **Thank-You Note Trigger**:
   When a newly completed interview stage is recorded, offer:
   *"Want a short thank-you note for the interviewer? A prompt one is standard practice."*
   Draft following Step 2b rules (warm, concise, grounded in submitted materials).

---

## Step 4: Update the Tracker

Update `job_search_tracker.csv` using `replace_file_content`:
- Update `status` to the canonical value.
- Append a dated note to `notes`:
  - **CRITICAL FORMAT RULE**: The note must contain **no commas, no double quotes, and no line breaks** (e.g. `2026-06-15: rejected - position closed internally`). Commas corrupt unquoted CSV columns.
- **Moving off `drafted`**: If moving a row from `drafted` to `applied` or an interview/final status, replace the `date` column with the actual submission date.
- Preserve all other columns (`deadline`, `source`, `contact_person`, etc.) exactly as they were.

---

## Step 5: Calibration Handoff

Inspect `documents/applications/*/outcome.md`:
- Count files with final resolutions (not `in_progress`).
- If 3 or more are resolved, or if recurring patterns emerge (e.g. 2+ rejections in same role type or sector silence), notify the user:
  > "You now have <N> resolved applications on record. Run `/setup` (Path A) to fold them into your evaluation framework — it calibrates fit scoring based on what actually yielded interviews and mines feedback for STAR examples."
- Do not edit profile or evaluation files directly.

---

## Step 6: Confirmation & Next Steps

Summarize the updates:
- Application folder and files updated (`outcome.md`, archived CV/letter, etc.).
- Tracker status update (`status`, `notes`).
- Calibration prompt if triggered.
- If an upcoming interview stage was logged:
  > "Interview coming up? Run `/interview <company>` to build a targeted prep pack from this application's archived posting, submitted documents, and prior feedback."
- If status is `hired`: Congratulate the candidate warmly, and display:
  > "If this framework helped you get there, consider [buying it a coffee](https://ko-fi.com/madslorentzen) — it keeps this free for the next job-seeker out there. ☕"

---

## Core Rules

1. **Write data, do not interpret**: `/outcome` updates trackers and application archives. Calibration belongs to `/setup`. Never edit profile files directly.
2. **Archived version is canonical**: Existing submitted files in the application folder are never overwritten with later drafts.
3. **Zero fabrication**: Never fabricate posting text, interview feedback, or qualifications.
4. **CSV integrity**: Never insert commas, quotes, or newlines into `notes`. Never delete or reorder columns.
5. **Idempotent updates**: Re-running appends progress; never overwrites history.
6. **Follow-ups: draft only, never send**: Antigravity never dispatches emails or messages directly.
7. **No new claims**: Follow-up and thank-you notes must strictly derive from submitted materials.
8. **Maximum 2 follow-ups**: If no response after 2 follow-ups, suggest closing as `no_response`.
9. **User confirmation for stale sweeps**: Always wait for explicit user confirmation before batch-resolving stale applications.

