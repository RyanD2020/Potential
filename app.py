"""Project Coach — a Streamlit app that takes any project or problem someone
describes, turns it into a step-by-step plan, and coaches them through each
step so they do the work themselves rather than having it done for them.

Works with Anthropic (Claude), OpenAI (GPT), or Google (Gemini) - whichever
the person has an API key for.

Flow:
  1. Intake  -> describe the project + upload supporting documents
  2. Plan    -> review the generated phases/steps
  3. Work    -> pick a step, see guidance, chat with a coach scoped to it
"""
from __future__ import annotations

import json
import os

import streamlit as st

from document_utils import build_supporting_docs_context
from providers import PROVIDERS

st.set_page_config(page_title="Project Coach", page_icon="🧭", layout="wide")


def inject_custom_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E3E6EA;
        }

        h1, h2, h3 {
            color: #1A2233 !important;
            font-weight: 700 !important;
        }

        /* Custom header banner */
        .pc-header {
            display: flex;
            align-items: center;
            gap: 14px;
            padding-bottom: 18px;
            margin-bottom: 22px;
            border-bottom: 1px solid #E3E6EA;
        }
        .pc-badge {
            width: 44px;
            height: 44px;
            flex-shrink: 0;
            border-radius: 10px;
            background: linear-gradient(135deg, #0B3B6F, #1E5FAE);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #FFFFFF;
            font-weight: 700;
            font-size: 18px;
        }
        .pc-header-text h1 {
            margin: 0 !important;
            font-size: 26px !important;
        }
        .pc-header-text p {
            margin: 2px 0 0 0;
            font-size: 14px;
            color: #5B6472;
        }

        /* Text inputs / textareas / selects */
        .stTextArea textarea, .stTextInput input {
            border-radius: 8px !important;
            border: 1px solid #D7DCE2 !important;
        }
        div[data-baseweb="select"] > div {
            border-radius: 8px !important;
            border: 1px solid #D7DCE2 !important;
        }

        /* File uploader */
        [data-testid="stFileUploaderDropzone"] {
            background: #FFFFFF;
            border: 1.5px dashed #C7CED6;
            border-radius: 10px;
        }

        /* Expander cards (phases) */
        [data-testid="stExpander"] {
            background: #FFFFFF;
            border: 1px solid #E3E6EA;
            border-radius: 10px;
        }

        /* Primary buttons - the one deliberate "shine" moment */
        button[kind="primary"] {
            position: relative;
            overflow: hidden;
            background: #1E5FAE !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            padding: 0.55rem 1.4rem !important;
            box-shadow: 0 1px 2px rgba(11, 59, 111, 0.15);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(11, 59, 111, 0.28);
        }
        button[kind="primary"]::after {
            content: "";
            position: absolute;
            top: 0; left: -75%;
            width: 50%; height: 100%;
            background: linear-gradient(120deg, transparent, rgba(255,255,255,0.45), transparent);
            transform: skewX(-20deg);
            transition: left 0.6s ease;
        }
        button[kind="primary"]:hover::after {
            left: 130%;
        }

        /* Secondary/default buttons - quiet hover */
        button[kind="secondary"] {
            border-radius: 8px !important;
            border: 1px solid #D7DCE2 !important;
            background: #FFFFFF !important;
            color: #1A2233 !important;
            transition: border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
        }
        button[kind="secondary"]:hover {
            border-color: #1E5FAE !important;
            background: #F0F5FB !important;
            color: #0B3B6F !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="pc-header">
            <div class="pc-badge">PC</div>
            <div class="pc-header-text">
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_custom_css()

PROVIDER_NAMES = list(PROVIDERS.keys())

DEFAULTS = {
    "stage": "intake",
    "intake_text": "",
    "docs_context": "",
    "doc_names": [],
    "plan": None,
    "progress": {},
    "chat_histories": {},
    "selected_step": None,
    "provider": PROVIDER_NAMES[0],
    "model": PROVIDERS[PROVIDER_NAMES[0]].MODELS[0],
    "api_keys": {
        name: os.environ.get(mod.KEY_ENV_VAR, "") for name, mod in PROVIDERS.items()
    },
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def step_key(phase_idx: int, step_idx: int) -> str:
    return f"{phase_idx}-{step_idx}"


def reset_all():
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


def current_provider_module():
    return PROVIDERS[st.session_state.provider]


def current_api_key() -> str:
    return st.session_state.api_keys.get(st.session_state.provider, "")


# ---------------------------------------------------------------- Sidebar --
with st.sidebar:
    st.header("Settings")

    st.session_state.provider = st.selectbox(
        "AI Provider",
        options=PROVIDER_NAMES,
        index=PROVIDER_NAMES.index(st.session_state.provider),
        help="Use whichever provider you have an API key for.",
    )
    provider_module = current_provider_module()

    if st.session_state.model not in provider_module.MODELS:
        st.session_state.model = provider_module.MODELS[0]
    st.session_state.model = st.selectbox("Model", options=provider_module.MODELS)

    st.session_state.api_keys[st.session_state.provider] = st.text_input(
        f"{st.session_state.provider} API key",
        value=st.session_state.api_keys.get(st.session_state.provider, ""),
        type="password",
        help=f"{provider_module.KEY_HELP}. Used only for this session; never stored or logged.",
    )

    st.divider()

    if st.session_state.plan:
        total_steps = sum(len(p["steps"]) for p in st.session_state.plan["phases"])
        done_steps = sum(1 for v in st.session_state.progress.values() if v)
        st.metric("Progress", f"{done_steps}/{total_steps} steps")
        if total_steps:
            st.progress(done_steps / total_steps)

        session_blob = json.dumps(
            {
                "intake_text": st.session_state.intake_text,
                "docs_context": st.session_state.docs_context,
                "doc_names": st.session_state.doc_names,
                "plan": st.session_state.plan,
                "progress": st.session_state.progress,
                "chat_histories": st.session_state.chat_histories,
            },
            indent=2,
        )
        st.download_button(
            "💾 Save progress (.json)",
            data=session_blob,
            file_name="project_coach_session.json",
            mime="application/json",
            use_container_width=True,
        )

    uploaded_session = st.file_uploader(
        "Load a saved session", type=["json"], key="session_loader"
    )
    if uploaded_session is not None and st.button("Load session", use_container_width=True):
        try:
            data = json.loads(uploaded_session.getvalue())
            st.session_state.intake_text = data.get("intake_text", "")
            st.session_state.docs_context = data.get("docs_context", "")
            st.session_state.doc_names = data.get("doc_names", [])
            st.session_state.plan = data.get("plan")
            st.session_state.progress = data.get("progress", {})
            st.session_state.chat_histories = data.get("chat_histories", {})
            st.session_state.stage = "work" if st.session_state.plan else "intake"
            st.success("Session loaded.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Couldn't load that file: {exc}")

    st.divider()
    if st.button("🔄 Start over", use_container_width=True):
        reset_all()
        st.rerun()


# ---------------------------------------------------------- Stage: Intake --
def render_intake():
    render_header("Project Coach", "Turn any project into a plan you'll actually work through")
    st.write(
        "Describe the project or problem you're working on. Upload any supporting "
        "documents for context — notes, briefs, requirements, anything relevant. "
        "I'll build you a step-by-step plan, then coach you through each step "
        "yourself rather than doing it for you."
    )

    st.session_state.intake_text = st.text_area(
        "What are you trying to get done?",
        value=st.session_state.intake_text,
        height=180,
        placeholder=(
            "e.g. I need to write a business plan for a small bakery, "
            "and get it ready to show a bank for a loan application..."
        ),
    )

    uploaded_files = st.file_uploader(
        "Supporting documents (optional)",
        type=["pdf", "docx", "txt", "md"],
        accept_multiple_files=True,
    )

    if st.button(
        "Generate My Plan",
        type="primary",
        disabled=not st.session_state.intake_text.strip(),
    ):
        if not current_api_key():
            st.error(f"Add your {st.session_state.provider} API key in the sidebar first.")
            return

        with st.spinner("Reading your documents and building your plan..."):
            docs_context = build_supporting_docs_context(uploaded_files or [])
            st.session_state.docs_context = docs_context
            st.session_state.doc_names = [f.name for f in (uploaded_files or [])]

            try:
                plan = current_provider_module().generate_plan(
                    api_key=current_api_key(),
                    model=st.session_state.model,
                    intake_text=st.session_state.intake_text,
                    docs_context=docs_context,
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Couldn't generate a plan: {exc}")
                return

            st.session_state.plan = plan
            st.session_state.progress = {}
            st.session_state.chat_histories = {}
            st.session_state.stage = "plan"
            st.rerun()


# ------------------------------------------------------- Stage: Plan review --
def render_plan():
    plan = st.session_state.plan
    render_header(plan.get("project_title", "Your Plan"), "Your step-by-step plan")
    st.write(plan.get("summary", ""))

    if st.session_state.doc_names:
        st.caption("Built using: " + ", ".join(st.session_state.doc_names))

    for p_idx, phase in enumerate(plan["phases"]):
        with st.expander(f"Phase {p_idx + 1}: {phase['title']}", expanded=True):
            st.write(f"**Goal:** {phase['goal']}")
            for step in phase["steps"]:
                st.markdown(f"- **{step['title']}** — {step['description']}")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Rewrite intake", type="secondary"):
            st.session_state.stage = "intake"
            st.rerun()
    with col2:
        if st.button("Start Working Through It", type="primary"):
            st.session_state.stage = "work"
            if plan["phases"] and plan["phases"][0]["steps"]:
                st.session_state.selected_step = (0, 0)
            st.rerun()


# ------------------------------------------------------ Stage: Work through --
def render_work():
    plan = st.session_state.plan
    nav_col, main_col = st.columns([1, 2.2])

    with nav_col:
        st.subheader(plan.get("project_title", "Your Plan"))
        for p_idx, phase in enumerate(plan["phases"]):
            st.markdown(f"**Phase {p_idx + 1}: {phase['title']}**")
            for s_idx, step in enumerate(phase["steps"]):
                key = step_key(p_idx, s_idx)
                done = st.session_state.progress.get(key, False)
                label = f"{'✅' if done else '⬜'} {step['title']}"
                if st.button(label, key=f"nav-{key}", use_container_width=True):
                    st.session_state.selected_step = (p_idx, s_idx)
                    st.rerun()
        st.divider()
        if st.button("Back to plan overview"):
            st.session_state.stage = "plan"
            st.rerun()

    with main_col:
        if not st.session_state.selected_step:
            st.info("Pick a step on the left to get started.")
            return

        p_idx, s_idx = st.session_state.selected_step
        phase = plan["phases"][p_idx]
        step = phase["steps"][s_idx]
        key = step_key(p_idx, s_idx)

        st.subheader(step["title"])
        st.write(step["description"])
        with st.expander("Why this step matters"):
            st.write(step.get("why_it_matters", ""))
        if step.get("self_check_questions"):
            with st.expander("How do I know I've done this well?"):
                for q in step["self_check_questions"]:
                    st.markdown(f"- {q}")

        done = st.checkbox(
            "Mark this step complete",
            value=st.session_state.progress.get(key, False),
            key=f"done-{key}",
        )
        st.session_state.progress[key] = done

        st.divider()
        st.markdown(f"**Work through it with your coach** ({st.session_state.provider})")

        history = st.session_state.chat_histories.get(key, [])
        for msg in history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        user_msg = st.chat_input(
            "Ask a question, share a draft, or say what you're stuck on..."
        )
        if user_msg:
            if not current_api_key():
                st.error(f"Add your {st.session_state.provider} API key in the sidebar first.")
                return

            history.append({"role": "user", "content": user_msg})
            with st.chat_message("user"):
                st.write(user_msg)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        reply = current_provider_module().coach_step(
                            api_key=current_api_key(),
                            model=st.session_state.model,
                            project_title=plan.get("project_title", ""),
                            project_summary=plan.get("summary", ""),
                            phase_title=phase["title"],
                            phase_goal=phase["goal"],
                            step_title=step["title"],
                            step_description=step["description"],
                            why_it_matters=step.get("why_it_matters", ""),
                            docs_context=st.session_state.docs_context,
                            chat_history=history,
                        )
                    except Exception as exc:  # noqa: BLE001
                        reply = f"Something went wrong calling the API: {exc}"
                st.write(reply)

            history.append({"role": "assistant", "content": reply})
            st.session_state.chat_histories[key] = history


# --------------------------------------------------------------- Router --
if st.session_state.stage == "intake" or st.session_state.plan is None:
    render_intake()
elif st.session_state.stage == "plan":
    render_plan()
else:
    render_work()
