# ReviewMind AI

> A persistent, memory-powered code review agent for engineering teams.

ReviewMind AI eliminates the repetitive cycle of enforcing the same conventions on every pull request. It builds a living memory of your team's coding standards, past review feedback, architectural decisions, and recurring mistakes — and applies that knowledge automatically on every new review.

**Built for the CascadeFlow Hackathon — AI Agents That Learn Using Hindsight**

---

## The Core Insight

Without memory, a code review agent is just a smarter linter.  
With memory, it becomes a senior engineer that knows your codebase, your team's preferences, and your most common pitfalls — and gets better with every PR it reviews.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Memory | [Hindsight by Vectorize](https://hindsight.vectorize.io/) |
| Agent Orchestration | CascadeFlow (7-stage pipeline) |
| LLM | [Groq](https://groq.com/) — `openai/gpt-oss-120b` / `qwen/qwen3-32b` |
| Backend | Python 3.11 + FastAPI |
| Frontend | React 18 + Tailwind CSS + Vite |

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Hindsight Cloud account](https://ui.hindsight.vectorize.io) — use promo code `MEMHACK409` for $50 free credits
- [Groq API key](https://groq.com/) — free tier available

---

## Setup

### 1. Clone and configure environment

```bash
git clone <repo-url>
cd reviewmind-ai
cp .env.example .env
```

Edit `.env` and fill in your API keys:

```env
HINDSIGHT_API_KEY=your_hindsight_api_key_here
GROQ_API_KEY=your_groq_api_key_here
HINDSIGHT_INSTANCE_URL=https://ui.hindsight.vectorize.io
GROQ_MODEL=openai/gpt-oss-120b
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Demo Walkthrough (5 Steps)

The UI guides you through a structured narrative. Here's what each step demonstrates:

### Step 1 — Setup
Meet the team: Crestline Software, Sprint 14, Orion API backend.  
Arjun Mehta has just opened PR #5. The code input is pre-loaded with the sample submission.

### Step 2 — Review Without Memory
Click **"Review Without Memory"**.  
The agent reviews the code with no Hindsight context. You'll see correct but generic feedback — null checks, style issues, obvious bugs. Labeled **WITHOUT MEMORY** (grey badge).

### Step 3 — Inject Memory
Click **"Inject Memory (PR #1–4)"**.  
Watch the memory panel populate in real time with:
- Team Convention: mutable default args banned (PR #1)
- Recurring Mistake: Arjun's async try/except gap (PRs #2 & #4, escalated)
- Architectural Decision: repository layer required for DB calls (PR #3)
- Approved Exception: legacy auth module direct ORM allowed (PR #3)

### Step 4 — Review With Memory
Click **"Review With Memory"**.  
The identical code is reviewed again — now with full team context. The agent references Arjun's recurring pattern, cites the team's mutable default arg decision, and notes the approved exception. Labeled **WITH MEMORY** (green badge).

### Step 5 — The Delta
Side-by-side comparison of both reviews.  
The quality difference is unmistakable.

---

## API Reference

### `POST /review`
Run a memory-powered code review.

```json
{
  "code": "async def get_user_orders(user_id: int, filters=[]):\n    ...",
  "contributor": "Arjun Mehta",
  "file_path": "routes/orders.py"
}
```

### `POST /inject-memory`
Bulk-write memory entries to Hindsight.

```json
{
  "entries": [
    {
      "category": "Team Convention",
      "contributor": "Arjun Mehta",
      "pattern_tag": "mutable-default-arg",
      "description": "Mutable default arguments are banned project-wide."
    }
  ]
}
```

---

## How Hindsight Memory Is Integrated

Hindsight is the sole persistence layer — no local database or file cache is used.

**On every review request:**
1. The agent queries Hindsight (`GET /memory/query`) with the contributor name and file path
2. Retrieved memory entries are injected into the LLM system prompt as structured context
3. After generating the review, new findings are written back to Hindsight (`POST /memory`)

**Memory categories stored:**
- `Team Convention` — project-wide coding rules
- `Recurring Mistake` — per-contributor patterns that appear repeatedly  
- `Architectural Decision` — design patterns and module boundaries
- `Approved Exception` — cases where the standard rule was explicitly waived
- `Positive Pattern` — good practices to reinforce

This accounts for 25% of the judging criteria and is the core differentiator of ReviewMind AI.

---

## Project Structure

```
reviewmind-ai/
├── backend/
│   ├── main.py              # FastAPI app + routes
│   ├── agent/
│   │   ├── workflow.py      # 7-stage CascadeFlow pipeline
│   │   ├── hindsight.py     # Hindsight read/write client
│   │   ├── groq_client.py   # Groq SDK wrapper + retry logic
│   │   └── parser.py        # libcst code parser
│   ├── models/
│   │   └── review.py        # Pydantic schemas
│   ├── data/
│   │   └── pr_history.json  # Synthetic PR #1-4 memory entries
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx           # 5-step demo scenario
│       ├── components/       # UI components
│       ├── api.ts            # FastAPI client
│       └── types.ts          # TypeScript interfaces
├── .env.example
└── README.md
```

---

*ReviewMind AI*
