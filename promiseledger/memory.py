import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from hindsight_client import Hindsight

# Load environment variables
load_dotenv()

# Initialize Hindsight client
BASE_URL = os.getenv("HINDSIGHT_API_URL") or os.getenv("HINDSIGHT_BASE_URL") or "http://localhost:8888"
API_KEY = os.getenv("HINDSIGHT_API_KEY")

hs = Hindsight(base_url=BASE_URL, api_key=API_KEY)
BANK_ID = "distributor_suresh"


def setup_bank():
    """
    Creates or updates the memory bank for distributor_suresh with the FMCG collections mission
    and a disposition of skepticism 4, literalism 3, and empathy 3.
    """
    mission = (
        "Collections assistant for an FMCG distributor. Track each shop's promises, "
        "payments, excuses, preferred channel and time, and which follow up tactics led to payment."
    )
    return hs.create_bank(
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
    return hs.retain(
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
    return hs.recall(
        bank_id=BANK_ID,
        query=query,
        budget="mid",
        max_tokens=2000,
    )


def think(question: str):
    """
    Reflects on the bank's stored memories and answers a question using hs.reflect().
    """
    return hs.reflect(
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
