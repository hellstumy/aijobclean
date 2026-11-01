---
name: interview
description: >
  Prepares the candidate for an interview on a tracked job application.
  Builds a stage-specific prep pack (likely questions, STAR stories, consistency brief,
  tough questions, questions to ask), researches interviewers and company hooks,
  and offers an interactive mock interview.
  Triggers on: /interview, interview, prepare interview, interview prep, mock interview,
  practice interview, interview coaching.
---

# /interview — Interview Preparation & Mock Interview

You are preparing the candidate for an interview on a tracked job application in Google Antigravity.
`/apply` optimizes what the company reads; `/interview` optimizes what the company hears. The bridge between them is consistency: every talking point must strictly align with what was submitted in the CV and cover letter.

---

## Execution Steps

### Step 0: Identify the Application

- **If argument provided (e.g. `interview acme`)**: Match against rows in `job_search_tracker.csv` (case-insensitively on company and role).
- **If no argument provided**: Read `job_search_tracker.csv` using `view_file` and list open applications (status `interview`, `applied`, or `offer`). Prompt user to select which one to prepare for.

---

### Step 1: Load Application Context & Source Documents

1. **Locate the Application Archive**:
   Derive `<company>_<role>` and check `documents/applications/<company>_<role>/`:
   - `job_posting.md` — The exact job posting applied to.
   - `cv_draft.tex` and `cover_letter.tex` — The exact documents the interviewers received.
   - `outcome.md` — Stage history and recorded feedback from previous rounds.
   *(Fallback if archive is missing: read `cv/main_<company>_<role>.tex` and `cover_letters/cover_<company>_<role>.tex`)*.

2. **Inquire about Stage Details**:
   Ask the user (if not already recorded in `outcome.md`):
   - Interview stage: phone screen, technical round, case study, or final/culture round.
   - Format: phone, video, or on-site.
   - Interviewers: names, titles, and roles (if known).

3. **Read Canonical Reference Files**:
   Using `view_file`, read:
   - `.claude/skills/job-application-assistant/07-interview-prep.md` (STAR examples & tough questions)
   - `.claude/skills/job-application-assistant/01-candidate-profile.md` (Career facts)
   - `.claude/skills/job-application-assistant/02-behavioral-profile.md` (Natural communication register)
   - `.claude/skills/job-application-assistant/04-job-evaluation.md` (Gaps and motivation criteria)

---

### Step 2: Interview-Focused Company Research

1. **Check Cache**:
   Read `company_research/<normalized_company>.json` using `view_file`. If it exists and is within the 30-day TTL, use it as baseline.
2. **Fresh Research**:
   If missing or stale, research via `search_web` and `read_url_content`:
   - Company strategic priorities, recent press releases, and culture.
   - Public background of named interviewers (role focus, technical background).
   - 2–3 concrete conversation hooks the candidate can reference naturally.
   Save or update `company_research/<normalized_company>.json`.
3. **Verify Claims**:
   All company facts must be independently verified. Never invent facts about the employer.

---

### Step 3: Build the Stage-Specific Prep Pack

Assemble a structured markdown document with the following sections:

1. **Likely Questions & Focus Areas**:
   - Probes based on feedback recorded from earlier rounds in `outcome.md`.
   - Probes targeting identified profile gaps (prepared with honest bridge answers).
   - Competency questions tied directly to job posting requirements.
   - Stage-specific themes (e.g., motivation for phone screen, deep architecture for technical round).
2. **STAR Story Mapping**:
   - Map existing STAR examples from `07-interview-prep.md` to likely questions.
   - For uncovered questions, formulate new STAR answers grounded strictly in `01-candidate-profile.md`.
3. **Consistency Brief**:
   - Bullet points summarizing the exact claims and metrics submitted on paper:
     *Rule: No claim in the room that isn't on the paper, and every claim on paper must be defensible in depth.*
4. **Customized Tough Questions**:
   - Stage-appropriate tough questions (e.g. "Why this company?", "Why did you leave your last role?", "How do you handle X gap?").
5. **Questions for the Interviewer**:
   - 4–6 high-value questions tailored to the stage, company, and interviewer profile.
6. **Logistics & Tips**:
   - Interview setup checklist and communication reminders matching candidate's behavioral style.

**Save the Prep Pack**:
Write to `documents/applications/<company>_<role>/interview_prep_<stage>.md` using `write_to_file`. Also display the summary in chat.

---

### Step 4: Offer Mock Interview

Ask the user:
> *"Would you like to run a mock interview session right now? We can roleplay the interview step by step."*

If the user accepts:
- Conduct conversational roleplay in the chat following the guidelines in `07-interview-prep.md`.
- Ask one question at a time (warm-up $\to$ technical/role competencies $\to$ behavioral scenario $\to$ curveball).
- After each response, provide concise constructive coaching: what landed well, what to sharpen, and which STAR example best fits.
- Coach toward the candidate's natural register (`02-behavioral-profile.md`), avoiding robotic corporate jargon.

---

### Step 5: Close the Loop

Conclude with advice for post-interview steps:
- Run `/outcome <company>` after the interview to log the outcome, round feedback, or offer details.

