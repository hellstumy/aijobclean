---
name: setup
description: >
  Runs the candidate profile onboarding and configuration for the AI Job Search framework.
  Collects professional information via documents folder, single CV import, or conversational
  interview, and populates candidate profile, templates, and search query files. Supports
  full onboarding or partial reconfiguration (e.g., --section search).
  Triggers on: /setup, setup, setup profile, configure profile, onboard, initialize profile,
  update search queries, setup search.
---

# Setup - Profile Onboarding

You are running the onboarding setup for the AI Job Search framework in Google Antigravity. Your goal is to collect the user's professional information and populate all profile files so the fit evaluation and application workflow work seamlessly out of the box.

There are three paths into setup. Step 0 selects the path; all three converge on Step 3 (file generation) and Step 4 (confirmation).

---

## Step 0: Welcome & Choose Path

1. **Check for partial run**: If the user's prompt or arguments contain `--section <name>`, skip directly to that section in Path C for an update-only flow. Do not run the path-selection prompt below.

2. **Check git remote visibility (Privacy Guard)**:
   - Run `git remote get-url origin` using `run_command`. If the command fails (no remote or not a git repo), continue silently.
   - If there is a GitHub `origin`, check its visibility with `gh repo view <owner/repo> --json visibility,isFork` if `gh` is available.
   - If the origin is a **public fork** of the upstream template (or visibility cannot be confirmed):
     > **Heads-up before we start:** your `origin` points at `<owner/repo>`, which is a public GitHub fork. This setup writes your personal data (name, contact details, employment history, salary expectations) into **tracked** files, and anything you commit *and push* to that fork is visible to anyone. Two safe options: keep your profile commits local and never push them, or push to a **private** repository instead — SETUP.md section 8 has the two-minute private-remote recipe. Want to continue with the setup?
     Wait for user confirmation before proceeding.

3. **Scan `documents/` folder**:
   - Inspect files under `documents/` across subfolders: `cv/`, `linkedin/`, `diplomas/`, `references/`, `projects/`, `applications/`.

4. **Welcome prompt**:
   - **If `documents/` contains files**:
     > **Welcome to the AI Job Search setup!**
     >
     > I'll help you build your professional profile so the agent can evaluate job postings, tailor CVs, write cover letters, and prepare you for interviews.
     >
     > I see files in your `documents/` folder: [list counts per subfolder, e.g. "1 in cv/, 1 in linkedin/, 2 in references/"]. Three ways to start:
     >
     > **Path A: Read my documents folder** (recommended for what you have) — I'll read everything in `documents/`, cross-reference for consistency, and build your profile from real source materials. Idempotent and safe to re-run as you add more documents.
     >
     > **Path B: Single CV import** — Paste or provide a single CV/resume here. I'll extract it and ask follow-up questions for what's missing.
     >
     > **Path C: Interview mode** — I'll walk you through structured questions section by section.
     >
     > Which would you like?

   - **If `documents/` is empty**:
     > **Welcome to the AI Job Search setup!**
     >
     > I'll help you build your professional profile so the agent can evaluate job postings, tailor CVs, write cover letters, and prepare you for interviews.
     >
     > Three ways to start:
     >
     > **Path A: Documents folder** (best signal if you have several materials) — Drop your CV, LinkedIn export, diplomas, reference letters, and project summaries in the `documents/` folder, then say "go". See `documents/README.md` for the folder layout.
     >
     > **Path B: Single CV import** — Paste or provide a single CV/resume here. I'll extract it and ask follow-up questions for what's missing.
     >
     > **Path C: Interview mode** — I'll walk you through structured questions section by section. Good if you're starting from scratch.
     >
     > Which would you like?

Wait for the user's choice. If they pick Path A but the folder is empty, explain what to add and pause.

---

## Path A: Documents Folder

Reads structured documents in `documents/`, cross-references them for consistency, and merges extracted data into the profile files. Read-before-write and idempotent: changes already present are not proposed again.

### Step A1: Inventory
Scan the `documents/` directory structure and report:
```
## Documents Found
- cv/: [list files or (empty)]
- linkedin/: [list files or (empty)]
- diplomas/: [list files or (empty)]
- references/: [list files or (empty)]
- projects/: [list files or (empty)]
- applications/: [list subfolders with files or (empty)]
```

### Step A2: Read Existing Profile & Methodology Files
Read existing state before extracting:
- `.claude/skills/job-application-assistant/01-candidate-profile.md` (Source of Truth)
- `.claude/skills/job-application-assistant/02-behavioral-profile.md` (Source of Truth)
- `.claude/skills/job-application-assistant/04-job-evaluation.md` (Source of Truth)
- `.claude/skills/job-application-assistant/07-interview-prep.md` (Source of Truth)
- `cv/main_example.tex` (Source of Truth)
- `.claude/skills/job-application-assistant/03-writing-style.md`
- `.claude/skills/job-application-assistant/05-cv-templates.md`
- `.claude/skills/job-application-assistant/06-cover-letter-templates.md`

### Step A3: Parse Documents
Process subfolders in order: `cv/`, `linkedin/`, `diplomas/`, `references/`, `projects/`, `applications/`.
- **`cv/`**: Name, contact (email, phone, LinkedIn, GitHub), education (degree, institution, dates, thesis), work experience (title, company, dates, bullets), skills, languages with proficiency levels, publications, awards.
- **`linkedin/`**: Summary/About (used for behavioral inference), work experience, education, endorsements, **Languages section** (name + proficiency level, e.g. "Native", "Professional working proficiency" — feeds the Language Gate in `04-job-evaluation.md`), certifications, recommendations received.
- **`diplomas/`**: Official degree titles, institution official names, graduation dates, honors/GPA.
- **`references/`**: Referee names, titles, organizations, direct quotes, competency language.
- **`projects/`**: Project names, domains, tech stack, key technical challenges, architectural decisions, measurable metrics.
- **`applications/<company>_<role>/`**:
  - `job_posting.md`: role, company, required skills, sector.
  - `cover_letter.tex`: opening structure, body structure, recurring phrases.
  - `cv_draft.tex`: profile statement, section ordering.
  - `outcome.md`: status, interview stages, feedback notes.

### Step A4: Cross-Reference Check
Identify any inconsistencies across sources:
- Date mismatches between CV, LinkedIn, and diplomas.
- Role title mismatches across documents for the same company.
- Education mismatches.
- Employer naming variations.

If inconsistencies are found, present them as a numbered list and ask the user to resolve each before continuing.

### Step A5: Build Change Sets
Categorize extracted content into:
1. **Additive changes**: Entirely new content not in the profile files (e.g., new certification, new project, new referee, new skill).
2. **Conflicting changes**: Content touching an existing entry with differing values (e.g., different date span or title).

**Inference Rules**:
- `01-candidate-profile.md` (`## Independent Projects`): Ground strictly in `projects/` text.
- `02-behavioral-profile.md`: Inferred from LinkedIn About + recommendations. Label additions: *[Inferred from LinkedIn About / Reference letter — review before relying on this]*.
- `03-writing-style.md`: Extract recurring patterns from 2+ cover letters under "## Patterns Observed in Past Applications".
- `04-job-evaluation.md`: Successful role types and sectors noted under "## Calibration from Past Applications".
- `05-cv-templates.md`: Profile statements from past drafts labeled *[Used for: <company>_<role>]*. All factual claims inside must be validated against `01-candidate-profile.md`.
- `06-cover-letter-templates.md`: Opening patterns and bullet structures that are structurally distinct.
- `07-interview-prep.md`: Add stubs under "## STAR Candidates (Complete Manually)" for achievements not yet covered by a full STAR story.

### Step A6: Present and Confirm Changes
- Present proposed **Additive changes** grouped by file and ask for confirmation ("yes" to apply all, or specify exclusions).
- Present **Conflicting changes** one by one with options: `[keep]`, `[replace]`, or `[manual]`.
- Wait for user response before modifying files.

### Step A7: Write Confirmed Changes and Fill Gaps
- Write confirmed updates to the target skill files.
- Prompt user for remaining missing essentials:
  - Career goals and target role types.
  - What excites the user in their next role.
  - Hard deal-breakers.
  - Languages and proficiency levels (if not already extracted).
  - Commute / location constraints.
  - Job search configuration (Section 9 below).
- Proceed to Step 3.

---

## Path B: Single CV Import

1. Read the provided CV document (text or file).
2. Extract all structured details: identity, contact, education, experience, technical skills, languages, publications, awards.
3. Present a clear summary of extracted facts.
4. Ask follow-up questions for gaps: behavioral profile, career goals, deal-breakers, languages/levels, salary expectations, references, job search configuration.
5. Proceed to Step 3.

---

## Path C: Interview Mode

Walk through structured sections conversationally. Let the user answer naturally; synthesize their responses into clean structured records.

### Section 1: Identity & Contact
- Full name.
- Location (city, country, commute limits).
- Phone, email, LinkedIn, GitHub.
- Working languages and proficiency level in each (Native, C1, B2, fluent, conversational). Explain why: feeds the Language Gate in `04-job-evaluation.md` (undeclared language = hard stop; declared but lower bar = flagged for judgment).
- Current employment status.
- CV language preference: English (default) or target market language.

### Section 2: Education & Certifications
- Degree level, field, institution, graduation year (or expected date).
- Thesis topic, key coursework.
- Professional certifications, online specializations.

### Section 3: Professional Experience & Projects
- For each role (most recent first): Title, company, dates, location, key responsibilities (3–5 bullets), key achievements with numbers, tech stack used.
- Independent technical projects, freelance engagements, open-source work.

### Section 4: Technical Skills
- Primary skills (core daily tools).
- Secondary skills (familiar / adjacent).
- Domain expertise (industry / scientific area).
- Software, frameworks, platforms, databases.

### Section 5: Publications & Awards (Optional)
- Papers, patents, conference talks, hackathon awards, honors.

### Section 6: Behavioral Profile (Optional)
- Formal assessment results if available (PI, DISC, Myers-Briggs, CliftonStrengths).
- If no formal test:
  - "What work environments do you thrive in?"
  - "What drains your energy at work?"
  - "How do you prefer to collaborate in teams?"
  - "What is your decision-making and communication style?"

### Section 7: Career Goals & Preferences
- Target roles and target industries.
- Tasks that energize vs. tasks that drain.
- Deal-breakers (e.g. required relocation, heavy travel, toxic management).
- Salary expectations / baseline (optional).

### Section 8: References (Optional)
- Names, titles, organizations, contact information, relationship.

### Section 9: Job Search Configuration
Configures the query generation for job searching:
- **Target Role Titles**: Ask about day-to-day functions, then collect 3–8 concrete search titles (e.g. "Data Scientist", "Machine Learning Engineer").
- **Key Skills as Search Terms**: 3–5 distinctive keywords likely to appear in job descriptions.
- **Target Companies (Optional)**: Specific employers to monitor.
- **Geographic Scope**: Cities, regions, commute radius; define tiers (ideal, acceptable, borderline, too far).
- **Job Portals**: Shipped country-agnostic tools include `linkedin-search` and `freehire-search` (enabled by default). Shipped Danish demos (`jobindex`, `jobbank`, `jobdanmark`, `jobnet`) are disabled by default. If the user's market is Denmark, enable them in frontmatter (`enabled: true`); otherwise keep disabled. If a custom board is needed, point to `/add-portal`.
- **Proactive Suggestions**: Suggest adjacent role types based on skills (e.g., Python + domain $\to$ "Solutions Engineer", ML + data engineering $\to$ "MLOps Engineer").

---

## Step 3: Generate Profile Files

Setup populates and updates ONLY the Source of Truth files and derived operational files.
`GEMINI.md`, `AGENTS.md`, and `CLAUDE.md` serve as thin-pointer guidelines and compatibility layers; they are NOT modified during normal setup.

Files updated by setup:

### Source of Truth (Canonical Data)
1. **Populate `.claude/skills/job-application-assistant/01-candidate-profile.md`**:
   - Structured sections: Identity, Languages table, Education, Experience, Independent Projects, Technical Skills, Publications, Awards, References.
2. **Populate `.claude/skills/job-application-assistant/02-behavioral-profile.md`**:
   - Behavioral profile, thrive/drain factors, team dynamics.
3. **Update `.claude/skills/job-application-assistant/04-job-evaluation.md`**:
   - Insert user's strong, moderate, and weak match areas; career goals; personal constraints.
4. **Update `.claude/skills/job-application-assistant/07-interview-prep.md`**:
   - Add ready-made STAR examples from candidate experience (or STAR candidate stubs).
5. **Update `cv/main_example.tex`**:
   - Replace placeholders with actual contact info, latest education, and experience.

### Derived Operational Files & Configuration
6. **Update `.claude/skills/job-application-assistant/05-cv-templates.md`**:
   - Personalize contact block (`\name`, `\email`, `\phone`, `\address`, `\extrainfo`) and insert role-specific profile statements.
7. **Update `.claude/skills/job-application-assistant/06-cover-letter-templates.md`**:
   - Personalize `\namesection` and `\signature` with user details.
8. **Update `.claude/skills/job-scraper/search-queries.md`**:
   - Populate priority categories (Priority 1: Core roles, Priority 2: Domain, Priority 3: Adjacent, Priority 4: Broad), location filter tiers, and language scopes.
9. **Update `.agents/skills/*/SKILL.md` (Portal configuration)**:
   - Toggle `enabled: true/false` in frontmatter for portals matching the candidate's target market (e.g. enable Danish portals if market is Denmark).

---

## Step 4: Confirmation & Next Steps

Present a clear summary of configured files:

> **Setup complete!** Your candidate profile is ready:
>
> **Source of Truth (Canonical Profile):**
> - `.claude/skills/job-application-assistant/01-candidate-profile.md` — Structured career facts
> - `.claude/skills/job-application-assistant/02-behavioral-profile.md` — Behavioral profile
> - `.claude/skills/job-application-assistant/04-job-evaluation.md` — Personalized fit evaluation framework & goals
> - `.claude/skills/job-application-assistant/07-interview-prep.md` — STAR interview stories
> - `cv/main_example.tex` — Master LaTeX CV
>
> **Derived Files & Configuration:**
> - `.claude/skills/job-application-assistant/05-cv-templates.md` — CV contact block
> - `.claude/skills/job-application-assistant/06-cover-letter-templates.md` — Cover letter signature block
> - `.claude/skills/job-scraper/search-queries.md` — Job search queries
> - `.agents/skills/*/SKILL.md` — Enabled portal search skills
>
> *(Note: `GEMINI.md` and `AGENTS.md` act as static Thin-Pointer guidelines referencing the Source of Truth files above.)*
>
> **Privacy note:** The files above now contain your personal data. Keep profile commits local or push only to a **private** GitHub repository.
>
> **What's next:**
> - Run search: "Find new jobs" or `/scrape`
> - Evaluate & apply: Provide a job posting URL to start the application workflow
> - Reconfigure search anytime: Run `setup --section search`

