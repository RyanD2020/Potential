# Project Coach

A Streamlit app that takes any project or problem someone describes, breaks it
into a step-by-step plan, and coaches them through each step — instead of
doing the work for them. Works with **Anthropic (Claude), OpenAI (GPT), or
Google (Gemini)** — whichever the person has access to.

## Adding this to your existing GitHub repo

If your repo currently only has a README in it, here's how to get everything
else in:

1. **Download and unzip this project** (or copy the files below) into a local
   folder.
2. **Clone your existing repo** next to it, or `cd` into it if you already
   have it cloned:
   ```bash
   git clone https://github.com/<your-org>/<your-repo>.git
   cd <your-repo>
   ```
3. **Copy every file from this project into that folder**, including the
   hidden `.github/` and dotfiles (`.gitignore`, `.env.example`):
   ```bash
   cp -r /path/to/project_coach/. .
   ```
4. **Add, commit, and push:**
   ```bash
   git add -A
   git commit -m "Add Project Coach app, multi-provider support, and Databricks config"
   git push
   ```

That's it — your repo now has the full app, not just the README.

## What this is, based on what you asked for

- **Intake:** free-text description of a project or problem, plus optional
  file uploads (PDF, DOCX, TXT, MD) as supporting context.
- **Plan generation:** the model reads the intake + documents and generates a
  custom, multi-phase, step-by-step plan live — not a fixed template.
- **Coaching, not solving:** once the plan exists, the person works through it
  step by step, chatting with the model at each step. It's instructed to
  guide with questions, frameworks, and checklists rather than hand over
  finished deliverables — the goal is for the person to do the work
  themselves, with AI help along the way.
- **Provider-agnostic:** the sidebar lets each person pick **Anthropic
  (Claude), OpenAI (GPT), or Google (Gemini)** and use their own API key. No
  one is locked out just because they don't have access to one particular
  vendor.
- **Supporting documents:** whatever the person uploads at intake is parsed
  into text and kept as context for both the plan and every coaching
  conversation, regardless of which provider is answering.
- **General purpose:** nothing in the prompts is domain-specific — it works
  for a business plan, a research paper, a job search, a home renovation, or
  whatever test project you throw at it.

## How it works

```
Intake (describe project + upload docs)
        |
        v
Plan generation (one model call -> structured JSON: phases -> steps)
        |
        v
Work through it (pick any step -> read guidance -> chat with a coach
                  scoped to just that step -> mark complete -> next step)
```

Progress and every step's chat history are tracked in the session, and can be
saved to a `.json` file from the sidebar and reloaded later to pick up where
you left off (there's no database — it's a portable session file).

## Files

| File | Purpose |
|---|---|
| `app.py` | The Streamlit UI and page flow (intake → plan → work). Provider-agnostic. |
| `providers/prompts.py` | The shared "coach, don't solve" system prompts and plan JSON schema, used by every provider. |
| `providers/anthropic_provider.py` | Calls Claude via the Anthropic SDK. |
| `providers/openai_provider.py` | Calls GPT via the OpenAI Responses API. |
| `providers/google_provider.py` | Calls Gemini via the Google Gen AI SDK. |
| `providers/__init__.py` | Registry mapping each provider's display name to its module — add a new vendor here. |
| `document_utils.py` | Extracts text from uploaded PDF/DOCX/TXT/MD files. |
| `requirements.txt` | Python dependencies for all three providers. |
| `.env.example` | Optional template if you want to pre-fill API keys via env vars. |
| `app.yaml` | Databricks Apps runtime config (see below). |
| `databricks.yml` | Optional Databricks Asset Bundle config for CLI/CI-CD deploys. |
| `.github/workflows/deploy.yml` | Optional GitHub Actions workflow for automated redeploys. |

## Setup

1. **Install dependencies** (Python 3.9+ recommended):
   ```bash
   pip install -r requirements.txt
   ```

2. **Get an API key for at least one provider** — you only need one to use
   the app:
   - Anthropic (Claude): [console.anthropic.com](https://console.anthropic.com)
   - OpenAI (GPT): [platform.openai.com](https://platform.openai.com)
   - Google (Gemini): [aistudio.google.com](https://aistudio.google.com)

3. **Run the app:**
   ```bash
   streamlit run app.py
   ```
   This opens the app in your browser, usually at `http://localhost:8501`.

4. **Pick a provider and add your API key** in the sidebar (or set the
   matching environment variable — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or
   `GOOGLE_API_KEY` — before launching, and it'll pre-fill).

## Testing it with your project

1. Pick a provider in the sidebar and paste in your API key.
2. Paste in your project description on the intake screen.
3. Upload whatever supporting documents you have for it.
4. Click **Generate My Plan** and review the phases/steps it produces.
5. Click **Start Working Through It**, pick the first step, and try chatting
   with the coach as if you were actually doing the work — ask a question,
   share a rough draft, say where you're stuck — and see whether the
   responses feel like coaching or like it's just doing the task for you.
6. Try switching providers in the sidebar mid-project and confirm the plan
   and chat history stay put — only the model answering changes.
7. Mark steps complete as you go; check the progress bar in the sidebar.
8. Use **Save progress** to download a session file, and **Load a saved
   session** to confirm you can pick back up later.

## Moving this to GitHub + Databricks

### 1. Push to GitHub

See "Adding this to your existing GitHub repo" at the top of this file.

### 2. Deploy on Databricks Apps (simplest path)

Databricks Apps can host a Streamlit app directly and can pull its source
straight from a GitHub repo — no CI/CD pipeline required to get started.

1. **Create a secret scope and store whichever key(s) you want to offer**
   (one-time, from a terminal with the Databricks CLI configured):
   ```bash
   databricks secrets create-scope project-coach-secrets
   databricks secrets put-secret --json '{
     "scope": "project-coach-secrets",
     "key": "ANTHROPIC_API_KEY",
     "string_value": "sk-ant-..."
   }'
   # Repeat for OPENAI_API_KEY and/or GOOGLE_API_KEY if you want those too
   ```
2. In the Databricks UI: **Compute → Apps → Create App**.
3. For the source, choose **Git repository**, point it at your GitHub repo
   and branch. Databricks will use the `app.yaml` and `requirements.txt`
   already in this repo.
4. Under **App resources**, click **+ Add resource → Secret** for each key
   you created — scope `project-coach-secrets`, matching key, permission
   **Can read** — and set the resource name to match `app.yaml`
   (`anthropic-api-key`, `openai-api-key`, or `google-api-key`).
5. **Important:** `app.yaml` references all three secrets by default. If you
   only set up one or two providers, delete the unused `env` entries in
   `app.yaml` first — an env var pointing at a resource that doesn't exist
   will fail deployment.
6. Click **Deploy**. Your app gets a URL like
   `https://project-coach-<workspace-id>.<region>.databricksapps.com`.

From then on, redeploying after a `git push` is a couple of clicks in the
Apps UI (or `databricks bundle run` — see below) — Databricks doesn't
automatically watch the repo unless you use CI/CD or its automatic Git
deployment setting.

### 3. Optional: CI/CD so pushes deploy automatically

This repo also includes `databricks.yml` and `.github/workflows/deploy.yml`
for a proper CI/CD path once the manual deploy above is working:

1. Fill in the placeholders in `databricks.yml` (`<your-workspace>`,
   `<owner>`, `<your-org>/<your-repo>`), and remove any secret resources for
   providers you're not using.
2. Set up [workload identity federation](https://docs.databricks.com/aws/en/dev-tools/auth/provider-github)
   so GitHub Actions can authenticate to Databricks without stored
   credentials, and grant that service principal `CAN MANAGE` on the app.
3. In your GitHub repo, go to **Settings → Environments**, create an
   environment named `prod`, and add environment variables
   `DATABRICKS_HOST` and `DATABRICKS_CLIENT_ID` (from step 2 — neither is a
   secret value).
4. Run the workflow manually from the **Actions** tab first
   (`workflow_dispatch`). Once it succeeds, uncomment the `push` trigger in
   `deploy.yml` so every push to `main` redeploys automatically.

## Things worth tuning once you've tested it

These are the levers most likely to need adjusting once you see it against a
real project, in rough order of likely impact:

- **Coaching tone/strictness** — `STEP_COACH_SYSTEM_TEMPLATE` in
  `providers/prompts.py` controls how much the model pushes back before
  helping directly, across every provider at once. Tighten or loosen this
  based on what you observe.
- **Plan granularity** — `PLAN_SYSTEM_PROMPT` (also in `providers/prompts.py`)
  currently asks for 2–5 phases of 2–5 steps each. Adjust if your test
  project wants more/fewer, larger/smaller steps.
- **Document truncation** — `MAX_CHARS_PER_DOC` in `document_utils.py` caps
  how much of each upload gets used. Raise it if your documents are large and
  the plan is missing important details from them.
- **Model choice within a provider** — the sidebar lets you switch models per
  session; there's no need to hardcode one while you're testing quality vs.
  cost/speed.
- **Adding another provider** — write a new module with the same
  `generate_plan` / `coach_step` interface (see any file in `providers/` as a
  template) and add it to the registry in `providers/__init__.py`.

## Known limitations (v1)

- No user accounts or server-side storage — state lives in the browser
  session and the optional exported `.json` file.
- Plan editing isn't supported yet (you can regenerate from a rewritten
  intake, but can't hand-edit individual steps).
- Only PDF, DOCX, TXT, and MD uploads are parsed; images/scans aren't OCR'd.
- Switching providers mid-conversation changes who's answering, but the new
  provider only sees what's in the chat history — it wasn't part of earlier
  turns and may respond slightly differently in style than its predecessor.
