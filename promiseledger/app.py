import json
import os
import re
import sys
from pathlib import Path

import streamlit as st

# Ensure the promiseledger package directory is importable
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import chase_list, draft_followup
from memory import remember

# Master shops catalog for resolving accurate dues & details
SHOPS_FILE = ROOT / "data" / "shops.json"
try:
    SHOPS_DATA = json.loads(SHOPS_FILE.read_text(encoding="utf-8"))
except Exception:
    SHOPS_DATA = []


def resolve_shop(item: dict | None) -> dict | None:
    """Ensure shop dictionary has canonical name, area, and accurate due amount."""
    if not item:
        return item
    raw_name = item.get("name", "")
    # Strip any trailing parenthetical area or details, e.g. 'Sri Lakshmi Kirana (Dilsukhnagar)'
    clean_name = re.sub(r"\s*\(.*?\)\s*$", "", raw_name).strip()

    matched = None
    for s in SHOPS_DATA:
        if s["name"].lower() == clean_name.lower():
            matched = s
            break
    if not matched:
        for s in SHOPS_DATA:
            if s["name"].lower() in raw_name.lower() or raw_name.lower() in s["name"].lower():
                matched = s
                break

    if matched:
        return {
            **item,
            "name": matched["name"],
            "area": matched.get("area") or item.get("area", ""),
            "due": matched.get("due") or item.get("due", 0),
            "reason": item.get("reason") or f"Rs {matched.get('due', 0):,} outstanding",
            "priority": item.get("priority", 99),
        }
    return item

# ──────────────────────────────────────────────────────────────────────────────
# Page config & global CSS
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PromiseLedger — FMCG Collections AI",
    page_icon="📒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── App background ── */
.stApp {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #0d1117 100%);
    min-height: 100vh;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.2rem 1.5rem 2rem 1.5rem !important; }

/* ── App title bar ── */
.app-header {
    background: linear-gradient(90deg, #6c63ff 0%, #f50057 100%);
    border-radius: 14px;
    padding: 14px 24px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 4px 24px rgba(108,99,255,0.35);
}
.app-header h1 { color: #fff; font-size: 1.55rem; font-weight: 700; margin: 0; }
.app-header p  { color: rgba(255,255,255,0.8); font-size: 0.82rem; margin: 0; }

/* ── Panel cards ── */
.panel {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    padding: 16px;
    height: 100%;
    backdrop-filter: blur(8px);
}
.panel-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #a78bfa;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(167,139,250,0.2);
}

/* ── Chase list items ── */
.chase-item {
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    padding: 11px 13px;
    margin-bottom: 8px;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.2s ease;
}
.chase-item:hover {
    border-color: #6c63ff;
    background: rgba(108,99,255,0.12);
}
.chase-item.active {
    border-color: #6c63ff;
    background: rgba(108,99,255,0.18);
    box-shadow: 0 0 0 2px rgba(108,99,255,0.25);
}
.chase-name   { font-weight: 600; font-size: 0.9rem; color: #f1f5f9; }
.chase-area   { font-size: 0.73rem; color: #94a3b8; }
.chase-due    { font-size: 0.8rem; font-weight: 600; color: #f59e0b; margin-top: 2px; }
.chase-reason { font-size: 0.72rem; color: #94a3b8; margin-top: 4px; line-height: 1.4; }

/* ── Badge (priority) ── */
.badge {
    display: inline-block;
    background: linear-gradient(90deg,#6c63ff,#f50057);
    color: #fff;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 0.65rem;
    font-weight: 700;
    margin-right: 6px;
    vertical-align: middle;
}

/* ── Shop card (center) ── */
.shop-card {
    background: rgba(255,255,255,0.05);
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,0.10);
    padding: 20px;
    margin-bottom: 16px;
}
.shop-card-name {
    font-size: 1.35rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 2px;
}
.shop-card-area { font-size: 0.8rem; color: #94a3b8; }
.due-tag {
    display: inline-block;
    background: linear-gradient(90deg,#f59e0b,#ef4444);
    color: #fff;
    padding: 5px 14px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 1rem;
    margin-top: 8px;
}

/* ── Draft area ── */
.draft-box {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(108,99,255,0.35);
    border-radius: 10px;
    padding: 16px;
    color: #e2e8f0;
    font-size: 0.88rem;
    line-height: 1.7;
    white-space: pre-wrap;
    max-height: 280px;
    overflow-y: auto;
}
.model-badge {
    font-size: 0.68rem;
    color: #6c63ff;
    font-weight: 600;
    margin-top: 6px;
}

/* ── Outcome buttons ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    padding: 7px 14px !important;
    transition: all 0.18s ease !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
}

/* ── Memory memory panel (right) ── */
.memory-panel {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 14px;
    padding: 16px;
    font-family: 'Inter', monospace;
}
.memory-panel-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #58a6ff;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}
.memory-entry {
    background: #161b22;
    border-left: 3px solid #6c63ff;
    border-radius: 0 8px 8px 0;
    padding: 9px 12px;
    margin-bottom: 8px;
    font-size: 0.78rem;
    color: #c9d1d9;
    line-height: 1.55;
}
.memory-entry.payment  { border-color: #3fb950; }
.memory-entry.broken   { border-color: #f85149; }
.memory-entry.tactic   { border-color: #f0883e; }
.memory-entry.promise  { border-color: #d2a8ff; }
.memory-entry.excuse   { border-color: #e3b341; }
.memory-entry.preference { border-color: #58a6ff; }
.memory-label {
    display: inline-block;
    font-size: 0.62rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 4px;
    background: rgba(108,99,255,0.2);
    color: #a78bfa;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

/* ── Toggle styling ── */
.stToggle label, div[data-testid="stToggle"] label { color: #f1f5f9 !important; }
div[data-testid="stToggle"] { margin-top: 8px; }

/* ── Spinner ── */
div[data-testid="stSpinner"] p { color: #a78bfa !important; }

/* ── Outcome log notice ── */
.outcome-notice {
    background: rgba(63,185,80,0.12);
    border: 1px solid rgba(63,185,80,0.35);
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.8rem;
    color: #3fb950;
    margin-top: 8px;
}

/* ── Empty states ── */
.empty-state {
    text-align: center;
    padding: 30px 10px;
    color: #4b5563;
    font-size: 0.85rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ──────────────────────────────────────────────────────────────────────────────
if "chase" not in st.session_state:
    st.session_state.chase = []
if "selected_shop" not in st.session_state:
    st.session_state.selected_shop = None
if "draft_result" not in st.session_state:
    st.session_state.draft_result = None
if "use_memory" not in st.session_state:
    st.session_state.use_memory = True
if "outcome_log" not in st.session_state:
    st.session_state.outcome_log = {}
if "chase_loaded" not in st.session_state:
    st.session_state.chase_loaded = False

# ──────────────────────────────────────────────────────────────────────────────
# App header
# ──────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="app-header">
    <div>📒</div>
    <div>
        <h1>PromiseLedger</h1>
        <p>AI-powered FMCG collections assistant — Suresh Distributors, Hyderabad</p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# Helper: load chase list (cached in session state)
# ──────────────────────────────────────────────────────────────────────────────
def load_chase():
    with st.spinner("Ranking shops to chase today…"):
        raw_chase = chase_list()
        st.session_state.chase = [resolve_shop(s) for s in raw_chase]
        st.session_state.chase_loaded = True
        # Default selection = first shop
        if st.session_state.chase and st.session_state.selected_shop is None:
            st.session_state.selected_shop = st.session_state.chase[0]
            st.session_state.draft_result = None


if not st.session_state.chase_loaded:
    load_chase()

# ──────────────────────────────────────────────────────────────────────────────
# Helper: generate draft
# ──────────────────────────────────────────────────────────────────────────────
def generate_draft():
    shop = resolve_shop(st.session_state.selected_shop)
    if not shop:
        return
    with st.spinner(f"Drafting follow-up for {shop['name']}…"):
        st.session_state.draft_result = draft_followup(
            shop=shop["name"],
            due=shop["due"],
            area=shop.get("area", ""),
            use_memory=st.session_state.use_memory,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Helper: parse memories into structured entries for the right panel
# ──────────────────────────────────────────────────────────────────────────────
def _parse_memory_entries(memories_text: str) -> list[dict]:
    """Split raw memory text into labelled chunks for rendering."""
    if not memories_text or memories_text.startswith("[Memory unavailable"):
        return []

    entries = []
    # Each block is separated by blank lines or leading dash/bullet
    import re
    blocks = re.split(r"\n{2,}|(?=\n[-•])", memories_text.strip())
    kind_keywords = {
        "payment": "payment",
        "paid": "payment",
        "broken": "broken",
        "ignored": "broken",
        "no answer": "broken",
        "tactic": "tactic",
        "split": "tactic",
        "offered": "tactic",
        "promise": "promise",
        "committed": "promise",
        "excuse": "excuse",
        "reason": "excuse",
        "delay": "excuse",
        "preference": "preference",
        "preferred": "preference",
        "channel": "preference",
    }
    for block in blocks:
        block = block.strip().lstrip("-•").strip()
        if not block:
            continue
        # Detect kind from content
        lower = block.lower()
        kind = "info"
        for kw, k in kind_keywords.items():
            if kw in lower:
                kind = k
                break
        entries.append({"kind": kind, "text": block})
    return entries


# ──────────────────────────────────────────────────────────────────────────────
# Layout: 3 columns
# ──────────────────────────────────────────────────────────────────────────────
col_left, col_center, col_right = st.columns([1.1, 2.2, 1.5], gap="medium")

# ══════════════════════════════════════════════════════════════════════════════
# LEFT COLUMN — Chase Today list + Memory toggle
# ══════════════════════════════════════════════════════════════════════════════
with col_left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">🎯 Chase Today</div>', unsafe_allow_html=True)

    # Memory toggle
    mem_on = st.toggle(
        "Memory: ON" if st.session_state.use_memory else "Memory: OFF",
        value=st.session_state.use_memory,
        key="mem_toggle",
        help="When ON, past interactions from Hindsight are injected into every draft.",
    )
    if mem_on != st.session_state.use_memory:
        st.session_state.use_memory = mem_on
        st.session_state.draft_result = None   # invalidate cached draft

    st.markdown("<div style='margin-bottom:10px'></div>", unsafe_allow_html=True)

    # Refresh button
    if st.button("🔄 Refresh list", use_container_width=True, key="btn_refresh"):
        st.session_state.chase_loaded = False
        st.session_state.selected_shop = None
        st.session_state.draft_result = None
        load_chase()
        st.rerun()

    st.markdown("<div style='margin:8px 0'></div>", unsafe_allow_html=True)

    # Chase list items
    for idx, raw_shop in enumerate(st.session_state.chase):
        shop = resolve_shop(raw_shop)
        current_sel = resolve_shop(st.session_state.selected_shop)
        is_active = (
            current_sel is not None
            and current_sel.get("name") == shop["name"]
        )
        active_cls = "active" if is_active else ""
        priority_badge = f'<span class="badge">#{shop.get("priority", idx+1)}</span>'

        st.markdown(
            f"""
<div class="chase-item {active_cls}" id="shop-{idx}">
    <div class="chase-name">{priority_badge}{shop['name']}</div>
    <div class="chase-area">📍 {shop.get('area','')}</div>
    <div class="chase-due">Rs {shop['due']:,}</div>
    <div class="chase-reason">{shop.get('reason','')[:90]}{'…' if len(shop.get('reason',''))>90 else ''}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        if st.button(f"Select", key=f"sel_{idx}", use_container_width=True):
            st.session_state.selected_shop = shop
            st.session_state.draft_result = None
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# CENTER COLUMN — Shop card + draft + outcome buttons
# ══════════════════════════════════════════════════════════════════════════════
with col_center:
    shop = resolve_shop(st.session_state.selected_shop)

    if not shop:
        st.markdown(
            '<div class="panel"><div class="empty-state">Select a shop from the list →</div></div>',
            unsafe_allow_html=True,
        )
    else:
        # ── Shop card ──────────────────────────────────────────────────────
        last_outcome = st.session_state.outcome_log.get(shop["name"], "")
        outcome_pill = (
            f" &nbsp;·&nbsp; <span style='color:#3fb950;font-size:0.78rem'>Last: {last_outcome}</span>"
            if last_outcome
            else ""
        )
        st.markdown(
            f"""
<div class="shop-card">
    <div class="shop-card-name">{shop['name']}{outcome_pill}</div>
    <div class="shop-card-area">📍 {shop.get('area','')}</div>
    <div class="due-tag">Outstanding: Rs {shop['due']:,}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        # ── Draft / regenerate ─────────────────────────────────────────────
        mem_indicator = (
            "🧠 Memory-powered draft" if st.session_state.use_memory else "⚡ Generic draft (memory OFF)"
        )
        st.markdown(
            f'<div class="panel-title" style="color:#6c63ff;font-size:0.75rem">'
            f'📝 Follow-up Script &nbsp;·&nbsp; {mem_indicator}</div>',
            unsafe_allow_html=True,
        )

        # Auto-generate on first selection
        if st.session_state.draft_result is None:
            generate_draft()

        draft_res = st.session_state.draft_result
        if draft_res:
            st.markdown(
                f'<div class="draft-box">{draft_res["draft"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="model-badge">🤖 Generated by: {draft_res["model"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="draft-box" style="color:#4b5563;font-style:italic">'
                "Click Draft again to generate…</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin:12px 0'></div>", unsafe_allow_html=True)

        # ── Action row ─────────────────────────────────────────────────────
        btn_col1, btn_col2 = st.columns([1, 1], gap="small")
        with btn_col1:
            if st.button("✍️ Draft again", key="btn_redraft", use_container_width=True):
                st.session_state.draft_result = None
                generate_draft()
                st.rerun()

        st.markdown("<div style='margin:6px 0'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="panel-title" style="margin-top:4px">📋 Log Outcome</div>',
            unsafe_allow_html=True,
        )

        out_cols = st.columns(4, gap="small")
        outcomes = [
            ("✅ Paid",           "payment",   "Paid"),
            ("💰 Partial",        "payment",   "Partial payment"),
            ("🤝 Promised again", "promise",   "Promised again"),
            ("📵 No answer",      "broken_promise", "No answer"),
        ]
        for (label, kind, logged_label), col in zip(outcomes, out_cols):
            with col:
                if st.button(label, key=f"out_{kind}_{logged_label}", use_container_width=True):
                    st.session_state.outcome_log[shop["name"]] = logged_label
                    try:
                        remember(
                            shop=shop["name"],
                            area=shop.get("area", ""),
                            kind=kind,
                            text=f"Outcome logged via PromiseLedger app: {logged_label}",
                        )
                        st.markdown(
                            f'<div class="outcome-notice">✓ Logged "{logged_label}" to memory bank</div>',
                            unsafe_allow_html=True,
                        )
                    except Exception as exc:
                        st.warning(f"Outcome recorded locally (memory sync failed: {exc})")
                    st.rerun()

        # Show last logged outcome
        if last_outcome:
            st.markdown(
                f'<div class="outcome-notice">Last outcome for {shop["name"]}: <b>{last_outcome}</b></div>',
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════════════════════
# RIGHT COLUMN — Why this suggestion (dark memory panel)
# ══════════════════════════════════════════════════════════════════════════════
with col_right:
    st.markdown('<div class="memory-panel">', unsafe_allow_html=True)
    st.markdown(
        '<div class="memory-panel-title">🔍 Why This Suggestion</div>',
        unsafe_allow_html=True,
    )

    draft_res = st.session_state.draft_result
    selected = st.session_state.selected_shop

    if not selected:
        st.markdown(
            '<div class="empty-state">Select a shop to see recalled memories.</div>',
            unsafe_allow_html=True,
        )
    elif not st.session_state.use_memory:
        st.markdown(
            '<div class="empty-state" style="color:#4b5563">Memory is <b style="color:#f85149">OFF</b>.<br>'
            "Enable memory to see past interactions and recalled tactics here.</div>",
            unsafe_allow_html=True,
        )
    elif draft_res and draft_res.get("memories"):
        entries = _parse_memory_entries(draft_res["memories"])
        if entries:
            # Legend
            st.markdown(
                """
<div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;font-size:0.67rem">
    <span style="color:#3fb950">■ payment</span>
    <span style="color:#f85149">■ broken</span>
    <span style="color:#f0883e">■ tactic</span>
    <span style="color:#d2a8ff">■ promise</span>
    <span style="color:#e3b341">■ excuse</span>
    <span style="color:#58a6ff">■ preference</span>
</div>""",
                unsafe_allow_html=True,
            )
            for entry in entries:
                kind = entry["kind"]
                label_map = {
                    "payment": "Payment",
                    "broken": "Broken Promise",
                    "tactic": "Tactic Used",
                    "promise": "Promise",
                    "excuse": "Excuse",
                    "preference": "Preference",
                    "info": "Note",
                }
                label = label_map.get(kind, "Note")
                css_class = kind if kind in ("payment","broken","tactic","promise","excuse","preference") else ""
                text = entry["text"][:320] + ("…" if len(entry["text"]) > 320 else "")
                st.markdown(
                    f"""
<div class="memory-entry {css_class}">
    <div class="memory-label">{label}</div><br>
    {text}
</div>""",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                f'<div class="memory-entry">{draft_res["memories"][:600]}</div>',
                unsafe_allow_html=True,
            )

        # Model attribution
        if draft_res.get("model"):
            st.markdown(
                f'<div style="font-size:0.68rem;color:#58a6ff;margin-top:8px">'
                f'🤖 Draft via <b>{draft_res["model"]}</b></div>',
                unsafe_allow_html=True,
            )
    elif draft_res and not draft_res.get("memories"):
        st.markdown(
            '<div class="memory-entry" style="border-color:#e3b341;color:#94a3b8">'
            "No past interactions found in memory for this shop.<br>"
            "Run <code>seed.py</code> to seed synthetic history.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="empty-state">Generate a draft to see the recalled memories.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)
