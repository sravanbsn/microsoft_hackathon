# 📒 PromiseLedger

> **AI-Powered FMCG Collections Assistant with Long-Term Memory (Hindsight + Groq)**

PromiseLedger is a smart debt-recovery and collections assistant built for FMCG distributors (modeled on Suresh Distributors in Hyderabad, India). It transforms stressful collection calls into personalized, respectful, and effective conversations by retaining each retail shop's unique payment history, behavioral personality, broken promises, preferred contact times, and successful past tactics.

---

## 🌟 Key Features

- **🧠 Continuous Memory (via Hindsight Cloud API)**
  - Stores and recalls interactions per shop: promises, broken promises, excuses, preferred channels (call vs. WhatsApp), and tactics that worked (e.g. split payments, delivery challans, cash discounts).
  - Automatically queries Hindsight's `reflect()` API to rank which shops to chase today based on debt risk and promise history.
- **⚡ Fast LLM Routing (via Groq)**
  - Generates context-aware follow-up scripts tailored to Telugu retail trade norms.
  - Primary model: `openai/gpt-oss-120b` with seamless fallback to `qwen/qwen3.8-27b`.
- **🖥️ Responsive 3-Column Streamlit Dashboard**
  - **Left Panel — Chase Today:** Prioritized list of retail shops with outstanding balances and Hindsight reasoning. Includes a live Memory ON/OFF toggle.
  - **Center Panel — Action Center:** Retail shop overview card, one-click script generation (call & WhatsApp scripts), and quick outcome logging (Paid, Partial, Promised Again, No Answer).
  - **Right Panel — "Why This Suggestion":** Visual memory feed color-coding recalled events (payment, broken promise, tactic, excuse, preference).

---

## 📁 Project Structure

```text
promiseledger/
├── app.py                # Main Streamlit dashboard (3-column UI)
├── agent.py              # LLM routing (Groq) & Hindsight chase ranking
├── memory.py             # Hindsight client wrapper (setup_bank, remember, history, think)
├── seed.py               # Seeds 12 Hyderabad retail shops & 60-day synthetic history
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore file (prevents secret leaks)
└── data/
    └── shops.json        # Master retail stores database (12 shops, ₹6,20,000 total dues)
```

---

## 🚀 Quickstart Guide

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/promiseledger.git
cd promiseledger
```

### 2. Set Up a Virtual Environment & Install Dependencies

```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp promiseledger/.env.example promiseledger/.env
```

Edit `.env` and supply your API keys:

```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
HINDSIGHT_API_KEY=hsk_your_hindsight_api_key_here
HINDSIGHT_API_URL=https://api.hindsight.vectorize.io
```

### 4. Seed the Memory Bank

Run the backdated seeding script to create the `distributor_suresh` memory bank and populate 12 Hyderabad shops with 60 days of realistic collections history:

```bash
python promiseledger/seed.py
```

### 5. Launch the Streamlit App

```bash
streamlit run promiseledger/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🛡️ License

MIT License. Designed for FMCG distributors and credit management workflows.
