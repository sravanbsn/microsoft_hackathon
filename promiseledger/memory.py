import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from hindsight_client import Hindsight

# Load environment variables
load_dotenv()

def _get_hindsight_config() -> tuple[str, str | None]:
    """Retrieve and sanitize Hindsight URL and API key from Streamlit secrets or env."""
    base_url = None
    api_key = None
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "HINDSIGHT_API_KEY" in st.secrets:
                api_key = st.secrets["HINDSIGHT_API_KEY"]
            if "HINDSIGHT_API_URL" in st.secrets:
                base_url = st.secrets["HINDSIGHT_API_URL"]
            elif "HINDSIGHT_BASE_URL" in st.secrets:
                base_url = st.secrets["HINDSIGHT_BASE_URL"]
    except Exception:
        pass

    if not api_key:
        api_key = os.getenv("HINDSIGHT_API_KEY")
    if not base_url:
        base_url = os.getenv("HINDSIGHT_API_URL") or os.getenv("HINDSIGHT_BASE_URL") or "http://localhost:8888"

    if api_key:
        api_key = str(api_key).strip().strip('"').strip("'")
    if base_url:
        base_url = str(base_url).strip().strip('"').strip("'")

    return base_url, api_key


BASE_URL, API_KEY = _get_hindsight_config()
hs = Hindsight(base_url=BASE_URL, api_key=API_KEY)
BANK_ID = "distributor_suresh"


def _get_hs() -> Hindsight:
    """Return active Hindsight client, re-initializing if config changed."""
    global hs, BASE_URL, API_KEY
    curr_url, curr_key = _get_hindsight_config()
    if hs is None or API_KEY != curr_key or BASE_URL != curr_url:
        BASE_URL, API_KEY = curr_url, curr_key
        hs = Hindsight(base_url=BASE_URL, api_key=API_KEY)
    return hs


def setup_bank():
    """
    Creates or updates the memory bank for distributor_suresh with the FMCG collections mission
    and a disposition of skepticism 4, literalism 3, and empathy 3.
    """
    mission = (
        "Collections assistant for an FMCG distributor. Track each shop's promises, "
        "payments, excuses, preferred channel and time, and which follow up tactics led to payment."
    )
    return _get_hs().create_bank(
        bank_id=BANK_ID,
        mission=mission,
        reflect_mission=mission,
        disposition_skepticism=4,
        disposition_literalism=3,
        disposition_empathy=3,
    )


def remember(shop: str, area: str, kind: str, text: str, when=None):
    """
    Stores an interaction with a shop using hs.retain() with a timestamp and metadata.
    """
    timestamp = when if when is not None else datetime.now(timezone.utc).isoformat()
    content = f"Shop: {shop} | Area: {area} | Kind: {kind}\n{text}"
    metadata = {
        "shop": str(shop),
        "area": str(area),
        "kind": str(kind),
    }
    return _get_hs().retain(
        bank_id=BANK_ID,
        content=content,
        timestamp=timestamp,
        metadata=metadata,
    )


def history(shop: str):
    """
    Fetches all past promises and tactics for a shop using hs.recall() with a 'mid' budget and 2000 max tokens.
    """
    query = f"All past promises, payments, excuses, and follow up tactics for {shop}"
    return _get_hs().recall(
        bank_id=BANK_ID,
        query=query,
        budget="mid",
        max_tokens=2000,
    )


def think(question: str):
    """
    Reflects on the bank's stored memories and answers a question using hs.reflect().
    """
    return _get_hs().reflect(
        bank_id=BANK_ID,
        query=question,
    )


if __name__ == "__main__":
    print(f"Connecting to Hindsight at {BASE_URL}...")
    try:
        bank_info = setup_bank()
        print(f"Bank '{BANK_ID}' successfully configured: {bank_info}")
    except Exception as e:
        print(f"Error setting up bank: {e}")
