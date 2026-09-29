import os
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from memory import history, think

load_dotenv()

# ---------------------------------------------------------------------------
# Groq client — lazily initialized so missing keys don't crash at import time
# ---------------------------------------------------------------------------
_groq: Groq | None = None
_current_groq_key: str | None = None

_PRIMARY_MODEL = "openai/gpt-oss-120b"
_FALLBACK_MODEL = "qwen/qwen3.8-27b"

SHOPS_FILE = Path(__file__).resolve().parent / "data" / "shops.json"


def _load_shops() -> list[dict]:
    with open(SHOPS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _get_api_key() -> str:
    """Retrieve and sanitize Groq API key from Streamlit secrets, session state, or environment."""
    key = None
    try:
        import streamlit as st
        # 1. UI session state override
        if hasattr(st, "session_state") and st.session_state.get("groq_api_key"):
            key = st.session_state["groq_api_key"]
        # 2. Streamlit Cloud secrets
        elif hasattr(st, "secrets"):
            if "GROQ_API_KEY" in st.secrets:
                key = st.secrets["GROQ_API_KEY"]
            elif "groq" in st.secrets and isinstance(st.secrets["groq"], dict):
                key = st.secrets["groq"].get("api_key")
    except Exception:
        pass

    # 3. Environment variable fallback
    if not key:
        key = os.getenv("GROQ_API_KEY")

    if key:
        # Strip whitespace, newlines, and accidental quotes (single/double)
        key = str(key).strip().strip('"').strip("'")

    return key or ""


def _get_groq() -> Groq:
    """Return the shared Groq client, creating or updating it when the key changes."""
    global _groq, _current_groq_key
    api_key = _get_api_key()
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set or is empty. "
            "Add it to your Streamlit Cloud Secrets (Settings > Secrets) or provide it in the sidebar."
        )
    if _groq is None or _current_groq_key != api_key:
        _groq = Groq(api_key=api_key)
        _current_groq_key = api_key
    return _groq


def _chat(messages: list[dict], model: str) -> str:
    """Call Groq chat completion and return the assistant text."""
    response = _get_groq().chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()


def _chat_with_fallback(messages: list[dict]) -> tuple[str, str]:
    """
    Try PRIMARY_MODEL first; on any error fall back to FALLBACK_MODEL.
    Returns (text, model_used).
    """
    last_exc = None
    for model in (_PRIMARY_MODEL, _FALLBACK_MODEL):
        try:
            text = _chat(messages, model)
            return text, model
        except Exception as exc:
            last_exc = exc
            # If the API key is unauthorized or invalid, do not retry on fallback model
            if "AuthenticationError" in type(exc).__name__:
                raise exc
            if model == _FALLBACK_MODEL:
                raise
            print(f"[agent] Primary model failed ({exc}); falling back to {_FALLBACK_MODEL}")
    if last_exc:
        raise last_exc
    raise RuntimeError("Both models failed")



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def draft_followup(
    shop: str,
    due: int,
    area: str = "",
    use_memory: bool = True,
) -> dict:
    """
    Draft a personalised follow-up script for a shop.

    Returns a dict with keys:
        draft       – the follow-up message text
        model       – which model was actually used
        memories    – the recalled history text (empty string if use_memory=False)
        recall_raw  – the raw RecallResponse object (or None)
    """
    memories_text = ""
    recall_raw = None

    if use_memory:
        try:
            recall_raw = history(shop)
            # RecallResponse.to_prompt_string() renders a clean text block
            if recall_raw and hasattr(recall_raw, "to_prompt_string"):
                memories_text = recall_raw.to_prompt_string()
            elif recall_raw and recall_raw.results:
                memories_text = "\n".join(
                    getattr(r, "content", str(r)) for r in recall_raw.results
                )
        except Exception as exc:
            memories_text = f"[Memory unavailable: {exc}]"

    memory_section = (
        f"\n\n--- Interaction History ---\n{memories_text}\n--- End of History ---"
        if memories_text
        else "\n\n[No past interaction history available — compose a general follow-up.]"
    )

    system_prompt = (
        "You are a professional collections assistant for Suresh Distributors, "
        "an FMCG distributor in Hyderabad. Your job is to help Suresh recover "
        "outstanding payments from retail kirana and general stores. "
        "You write follow-up messages that are polite, firm, and culturally "
        "appropriate for the Telugu-speaking retail trade context. "
        "Based on past interaction history, always recommend the best channel "
        "(call / WhatsApp), the optimal time of day, and the tactic most likely "
        "to succeed (e.g., split payment, ledger statement, cash discount, "
        "personal visit). Never be aggressive or threatening."
    )

    user_prompt = (
        f"Shop: {shop}"
        + (f" ({area})" if area else "")
        + f"\nOutstanding amount: Rs {due:,}"
        + memory_section
        + "\n\nBased on this history, write a concise, personalised follow-up script "
        "for today. Include:\n"
        "1. The best channel to use and exactly when to contact them.\n"
        "2. The specific tactic to suggest (split, discount, visit, etc.).\n"
        "3. The actual follow-up message text (WhatsApp or call script).\n"
        "Keep the tone warm but professional."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    draft, model_used = _chat_with_fallback(messages)

    return {
        "draft": draft,
        "model": model_used,
        "memories": memories_text,
        "recall_raw": recall_raw,
    }


def chase_list() -> list[dict]:
    """
    Use Hindsight reflect to rank which shops to chase today.

    Returns a list of dicts sorted by priority (highest first):
        [{"name": ..., "area": ..., "due": ..., "reason": ..., "priority": int}, ...]

    Falls back to a due-amount ranking if Hindsight is unavailable.
    """
    shops = _load_shops()

    # Build shop summary for the reflect query
    shop_summary = "\n".join(
        f"- {s['name']} ({s['area']}): Rs {s['due']:,} outstanding"
        for s in shops
    )

    reflect_query = (
        "Given the following shops with outstanding dues, and considering any "
        "recorded broken promises, long overdue amounts, and past payment "
        "patterns in memory, rank which shops should be chased today. "
        "Prioritise shops with broken promises or very large dues first. "
        "Reply as a JSON array of objects with keys: name, reason, priority "
        "(1=highest). Only include shops from this list:\n" + shop_summary
    )

    try:
        reflect_res = think(reflect_query)
        text = reflect_res.text if hasattr(reflect_res, "text") else str(reflect_res)

        # Try to parse the JSON array from the reflect response
        import re
        json_match = re.search(r"\[.*?\]", text, re.DOTALL)
        if json_match:
            ranked = json.loads(json_match.group())
            # Enrich with area and due from shops data
            enriched = []
            for item in ranked:
                raw_name = item.get("name", "")
                clean_name = re.sub(r"\s*\(.*?\)\s*$", "", raw_name).strip()

                # Match against shops.json
                matched = None
                for s in shops:
                    if s["name"].lower() == clean_name.lower():
                        matched = s
                        break
                if not matched:
                    for s in shops:
                        if s["name"].lower() in raw_name.lower() or raw_name.lower() in s["name"].lower():
                            matched = s
                            break

                if matched:
                    enriched.append({
                        "name": matched["name"],
                        "area": matched.get("area", ""),
                        "due": matched.get("due", 0),
                        "reason": item.get("reason", ""),
                        "priority": item.get("priority", 99),
                    })
                else:
                    enriched.append({
                        "name": clean_name or raw_name,
                        "area": item.get("area", ""),
                        "due": item.get("due", 0),
                        "reason": item.get("reason", ""),
                        "priority": item.get("priority", 99),
                    })
            # Sort by priority ascending (1 = chase first)
            enriched.sort(key=lambda x: x["priority"])
            return enriched
    except Exception as exc:
        print(f"[agent] chase_list reflect failed ({exc}); falling back to due-amount ranking")

    # -----------------------------------------------------------------------
    # Fallback: rank purely by outstanding amount
    # -----------------------------------------------------------------------
    fallback = sorted(shops, key=lambda s: s["due"], reverse=True)
    return [
        {
            "name": s["name"],
            "area": s["area"],
            "due": s["due"],
            "reason": f"Rs {s['due']:,} outstanding — prioritised by amount",
            "priority": idx + 1,
        }
        for idx, s in enumerate(fallback)
    ]
