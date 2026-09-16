Project Coach

A Streamlit app that takes any project or problem someone describes, breaks it into a step-by-step plan, and coaches them through each step — instead of doing the work for them.

What this is, based on what you asked for
Intake: free-text description of a project or problem, plus optional file uploads (PDF, DOCX, TXT, MD) as supporting context.
Plan generation: Claude reads the intake + documents and generates a custom, multi-phase, step-by-step plan live — not a fixed template.
Coaching, not solving: once the plan exists, the person works through it step by step, chatting with Claude at each step. Claude is instructed to guide with questions, frameworks, and checklists rather than hand over finished deliverables — the goal is for the person to do the work themselves, with Claude helping them think it through.
Supporting documents: whatever the person uploads at intake is parsed into text and kept as context for both the plan and every coaching conversation, so Claude can reference it by name.
General purpose: nothing in the prompts is domain-specific — it works for a business plan, a research paper, a job search, a home renovation, or whatever test project you throw at it.
How it works
Intake (describe project + upload docs)
        |
        v
Plan generation (one Claude call -> structured JSON: phases -> steps)
        |
        v
Work through it (pick any step -> read guidance -> chat with a coach
                  scoped to just that step -> mark complete -> next step)

Progress and every step's chat history are tracked in the session, and can be saved to a .json file from the sidebar and reloaded later to pick up where you left off (there's no database — it's a portable session file).

Files
File	Purpose
app.py	The Streamlit UI and page flow (intake → plan → work).
claude_engine.py	All Claude API calls: plan generation and per-step coaching. Prompts live here.
document_utils.py	Extracts text from uploaded PDF/DOCX/TXT/MD files.
requirements.txt	Python dependencies.
.env.example	Optional template if you want to pre-fill your API key via an env var.
Setup
Install dependencies (Python 3.9+ recommended):
bash
   pip install -r requirements.txt
Get an Anthropic API key if you don't have one already, from console.anthropic.com.
Run the app:
bash
   streamlit run app.py

This opens the app in your browser, usually at http://localhost:8501.

Add your API key in the sidebar (or set the ANTHROPIC_API_KEY environment variable before launching, and it'll pre-fill).
Testing it with your project
Paste in your project description on the intake screen.
Upload whatever supporting documents you have for it.
Click Generate My Plan and review the phases/steps it produces.
Click Start Working Through It, pick the first step, and try chatting with the coach as if you were actually doing the work — ask a question, share a rough draft, say where you're stuck — and see whether the responses feel like coaching or like it's just doing the task for you.
Mark steps complete as you go; check the progress bar in the sidebar.
Use Save progress to download a session file, and Load a saved session to confirm you can pick back up later.
Moving this to GitHub + Databricks
1. Push to GitHub
bash
cd project_coach
git init
git add .
git commit -m "Initial commit: Project Coach"
git branch -M main
git remote add origin https://github.com/<your-org>/<your-repo>.git
git push -u origin main
2. Deploy on Databricks Apps (simplest path)

Databricks Apps can host a Streamlit app directly and can pull its source straight from a GitHub repo — no CI/CD pipeline required to get started.

Create a secret scope and store your API key (one-time, from a terminal with the Databricks CLI configured):
bash
   databricks secrets create-scope project-coach-secrets
   databricks secrets put-secret project-coach-secrets ANTHROPIC_API_KEY --string-value "sk-ant-..."
In the Databricks UI: Compute → Apps → Create App.
For the source, choose Git repository, point it at your GitHub repo and branch. Databricks will use the app.yaml and requirements.txt already in this repo.
Under App resources, click + Add resource → Secret, pick the project-coach-secrets scope and ANTHROPIC_API_KEY key, and set the resource name to anthropic-api-key (this must match the valueFrom in app.yaml).
Click Deploy. Your app gets a URL like https://project-coach-<workspace-id>.<region>.databricksapps.com.

From then on, redeploying after a git push is a couple of clicks in the Apps UI (or databricks bundle run — see below) — Databricks doesn't automatically watch the repo unless you use CI/CD or its automatic Git deployment setting.

3. Optional: CI/CD so pushes deploy automatically

This repo also includes databricks.yml and .github/workflows/deploy.yml for a proper CI/CD path once the manual deploy above is working:

Fill in the placeholders in databricks.yml (<your-workspace>, <owner>, <your-org>/<your-repo>).
Set up workload identity federation so GitHub Actions can authenticate to Databricks without stored credentials, and grant that service principal CAN MANAGE on the app.
In your GitHub repo, go to Settings → Environments, create an environment named prod, and add environment variables DATABRICKS_HOST and DATABRICKS_CLIENT_ID (from step 2 — neither is a secret value).
Run the workflow manually from the Actions tab first (workflow_dispatch). Once it succeeds, uncomment the push trigger in deploy.yml so every push to main redeploys automatically.
Things worth tuning once you've tested it

These are the levers most likely to need adjusting once you see it against a real project, in rough order of likely impact:

Coaching tone/strictness — STEP_COACH_SYSTEM_TEMPLATE in claude_engine.py controls how much Claude pushes back before helping directly. Tighten or loosen this based on what you observe.
Plan granularity — PLAN_SYSTEM_PROMPT currently asks for 2–5 phases of 2–5 steps each. Adjust if your test project wants more/fewer, larger/ smaller steps.
Document truncation — MAX_CHARS_PER_DOC in document_utils.py caps how much of each upload gets used. Raise it if your documents are large and the plan is missing important details from them.
Model choice — the sidebar lets you switch models per session; there's no need to hardcode one while you're testing quality vs. cost/speed.
Known limitations (v1)
No user accounts or server-side storage — state lives in the browser session and the optional exported .json file.
Plan editing isn't supported yet (you can regenerate from a rewritten intake, but can't hand-edit individual steps).
Only PDF, DOCX, TXT, and MD uploads are parsed; images/scans aren't OCR'd.
