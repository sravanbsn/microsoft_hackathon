import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure promiseledger directory is in Python path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from memory import setup_bank, remember


def run_seed():
    print("=" * 70)
    print("PromiseLedger - Seeding Hindsight Memory Bank")
    print("=" * 70)

    # 1. Setup Hindsight Bank
    print("\n[1/4] Setting up memory bank 'distributor_suresh'...")
    try:
        bank_res = setup_bank()
        print(f"      Bank setup successful: {bank_res}")
    except Exception as e:
        print(f"      Warning: Bank setup encountered an error: {e}")
        print("      (Make sure the Hindsight API server is running if attempting live sync)")

    # 2. Load the 12 shops from data/shops.json
    shops_file = CURRENT_DIR / "data" / "shops.json"
    print(f"\n[2/4] Loading shops from {shops_file}...")
    if not shops_file.exists():
        raise FileNotFoundError(f"Shops data file not found: {shops_file}")

    with open(shops_file, "r", encoding="utf-8") as f:
        shops = json.load(f)

    print(f"      Loaded {len(shops)} retail shops successfully:")
    for idx, shop in enumerate(shops, 1):
        print(f"      {idx:2d}. {shop['name']:<30} | {shop['area']:<15} | Rs {shop['due']:,}")

    # Retain baseline shop profiles
    print("\n[3/4] Retaining initial profile context for all 12 shops...")
    for shop in shops:
        try:
            remember(
                shop=shop["name"],
                area=shop["area"],
                kind="profile",
                text=f"Initial registration: Current due is Rs {shop['due']:,}. Payment behavior profile: {shop['personality']}",
                when=(datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            )
            print(f"      -> Baseline retained for: {shop['name']}")
        except Exception as e:
            print(f"      -> Note: Could not retain baseline for {shop['name']}: {e}")

    # 3. Generate backdated learning timeline for 'Sri Lakshmi Kirana'
    target_shop = "Sri Lakshmi Kirana"
    target_area = "Dilsukhnagar"
    now = datetime.now(timezone.utc)

    # Synthetic backdated events over the last 60 days showing the core learning pattern:
    # 1. Early promise made
    # 2. Broken promise (ignored WhatsApp)
    # 3. 2-part split offered
    # 4. Same-day payment following split offer
    # 5. Subsequent promise
    # 6. Recent partial payment
    events = [
        {
            "days_ago": 54,
            "kind": "promise",
            "label": "Early Promise Made",
            "text": "Suresh called owner Srinivas at 7:30 PM. Srinivas acknowledged pending invoice of Rs 40,000 for confectionery items and made an early promise: 'Will clear the full Rs 40,000 payment by coming Monday via UPI.'",
        },
        {
            "days_ago": 46,
            "kind": "broken_promise",
            "label": "Broken Promise (Ignored WhatsApp)",
            "text": "Sent follow-up WhatsApp message at 2:15 PM asking for the promised Rs 40,000. Message delivered and read with blue ticks, but Srinivas ignored the WhatsApp completely without replying or paying.",
        },
        {
            "days_ago": 42,
            "kind": "broken_promise",
            "label": "Broken Promise (Daytime Call Cut)",
            "text": "Followed up with a voice call at 11:30 AM during morning peak rush. Call was abruptly cut by Srinivas who texted: 'Busy with customers, don't call during shop hours.' Promise remained broken.",
        },
        {
            "days_ago": 35,
            "kind": "tactic",
            "label": "2-Part Split Offered",
            "text": "Called Srinivas at 7:15 PM after evening rush. Offered a 2-part split tactic: pay Rs 20,000 today and remaining Rs 20,000 in two weeks. Srinivas agreed immediately: 'Two-part split is feasible for my cash flow, I will pay first half right now.'",
        },
        {
            "days_ago": 35,
            "kind": "payment",
            "label": "Same-Day Payment (Split Result)",
            "text": "Same-day payment received! Srinivas transferred Part 1 payment of Rs 20,000 via PhonePe UPI at 8:05 PM, exactly 50 minutes after accepting the 2-part split offer.",
        },
        {
            "days_ago": 21,
            "kind": "promise",
            "label": "Subsequent Promise",
            "text": "Evening follow-up call at 7:45 PM for Part 2 plus new stock dispatch (total balance Rs 80,000). Srinivas made a subsequent promise: 'Will pay Rs 15,000 by 10th and balance within 10 days.'",
        },
        {
            "days_ago": 14,
            "kind": "excuse",
            "label": "Excuse / Daytime Delay",
            "text": "WhatsApp reminder sent at 1:00 PM for the promised installment. Srinivas gave excuse: 'Local customer payments are stuck, cannot pay during daytime. Contact me only at night.'",
        },
        {
            "days_ago": 7,
            "kind": "payment",
            "label": "Recent Partial Payment",
            "text": "Called at 7:30 PM with an empathetic reminder and another split option. Srinivas made a recent partial payment of Rs 15,000 via Google Pay at 8:15 PM, bringing remaining balance to current due of Rs 65,000.",
        },
        {
            "days_ago": 2,
            "kind": "preference",
            "label": "Preferred Channel & Timing Confirmed",
            "text": "Sent WhatsApp check-in at 7:20 PM regarding current due of Rs 65,000. Srinivas responded: 'Acknowledged. Please strictly call only after 7:00 PM when counter sales slow down, and send split payment terms on WhatsApp.'",
        },
    ]

    print(f"\n[4/4] Retaining {len(events)} backdated learning events for '{target_shop}'...")
    print("-" * 70)

    for idx, event in enumerate(events, 1):
        event_time = (now - timedelta(days=event["days_ago"])).isoformat()
        days_str = f"{event['days_ago']} days ago"
        print(f"      [{idx}/{len(events)}] ({days_str:<12}) {event['label']}")
        print(f"          Kind: {event['kind']}")
        print(f"          Content: {event['text'][:90]}...")
        try:
            remember(
                shop=target_shop,
                area=target_area,
                kind=event["kind"],
                text=event["text"],
                when=event_time,
            )
            print("          Status: Retained in memory bank.")
        except Exception as e:
            print(f"          Status: Handled ({e})")

    print("-" * 70)
    print("Seeding script execution completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    run_seed()
