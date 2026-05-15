# 🧠 HireIQ — AI Resume Screener

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Gemini Flash](https://img.shields.io/badge/Gemini%20Flash-Free%20Tier-4285F4?style=flat&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Multi-Agent AI](https://img.shields.io/badge/Multi--Agent%20AI-5-6366F1?style=flat)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat)

**HireIQ** is a multi-agent AI system that screens resumes against a job description in seconds. Upload one or more PDF/DOCX resumes, paste a job description, and get a structured analysis: match score, top strengths, missing keywords, and a downloadable PDF report — all powered by Google Gemini Flash (free tier).

> **Live Demo:** [Add Streamlit Cloud URL here after deployment]

---

## What It Does

- Parses resumes (PDF and DOCX) automatically
- Runs a **5-agent Gemini Flash pipeline** to extract, match, explain, and gap-analyse
- Displays a **match score (0-100)** with a colour-coded progress bar
- Lists **Top Strengths** — what the candidate does well for this role
- Lists **Missing Keywords** — skills in the JD that aren't on the resume
- Generates an **HR-friendly plain-language explanation**
- Exports the full analysis as a **downloadable PDF report**
- Supports **multiple resumes** — screen an entire candidate pool at once

---

## How the 5-Agent Pipeline Works

This is the core architectural decision worth explaining in an interview.

Instead of sending one giant prompt to a single AI call, the app chains five specialised agents. Each agent has a narrow, well-defined role. The output of one feeds into the next — just like a real hiring workflow.

```
Resume Text + JD
       │
       ▼
┌──────────────────────────────────┐
│  Agent 1 — Resume Extractor      │  Parses raw text → structured info
│  (Skills, Education, Experience) │
└──────────────────────────────────┘
       │ structured info
       ▼
┌──────────────────────────────────┐
│  Agent 2 — Matcher               │  Scores fit (SCORE: XX/100) +
│  (JD vs Resume)                  │  lists key matching areas
└──────────────────────────────────┘
       │ match report
       ▼
┌──────────────────────────────────┐
│  Agent 3 — HR Explainer          │  3-5 sentence plain-language
│  (Plain-Language Summary)        │  summary for non-technical managers
└──────────────────────────────────┘

[Runs in parallel from Agent 1 output]

┌──────────────────────────────────┐
│  Agent 4 — Gap Analyst           │  Keywords in JD absent from resume
│  (Missing Keywords)              │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│  Agent 5 — Career Coach          │  Top 3-5 resume strengths for
│  (Top Strengths)                 │  this specific role
└──────────────────────────────────┘
```

Each agent is a focused prompt with a specific persona and output format. This makes the system modular, testable, and easy to extend.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| AI Model | Google Gemini 1.5 Flash (free tier) |
| PDF Parsing | pdfplumber |
| DOCX Parsing | python-docx |
| PDF Export | fpdf2 |
| Secrets | python-dotenv / Streamlit Secrets |
| Deployment | Streamlit Cloud (free) |

---

## Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/vinay23is/smart-resume-screener.git
cd smart-resume-screener
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your Gemini API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get a free key at [Google AI Studio](https://aistudio.google.com) — no billing required.

### 4. Run the app

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. A sample job description is pre-filled so you can test immediately by uploading any resume.

---

## Deploy on Streamlit Cloud (Free)

1. Push this repo to your GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud) and sign in with GitHub
3. Click **New app** → select `vinay23is/smart-resume-screener` → `main` → `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_gemini_api_key_here"
   ```
5. Click **Deploy** — your app will be live in ~60 seconds

---

## Project Structure

```
smart-resume-screener/
├── app.py              # Full application — UI + 5-agent pipeline
├── requirements.txt    # Python dependencies
├── .gitignore          # Excludes .env and Python artifacts
├── README.md           # This file
└── INTERVIEW_PREP.md   # Q&A for technical interviews
```

---

## Screenshot

> *(Add screenshot after first deployment)*

---

## Design Decisions

### Why multi-agent over a single prompt?

A single prompt asking for extraction + matching + scoring + gap analysis + strengths in one shot produces inconsistent, tangled output. Splitting into agents gives each one a clear persona, a focused task, and a defined output format. This makes each piece independently debuggable and the overall pipeline explainable to non-technical stakeholders.

### Why Gemini Flash specifically?

- **Free tier** with generous rate limits — no credit card required
- **Fast** (optimised for throughput, not just quality)
- **Capable** — 1.5 Flash handles multi-step reasoning well enough for hiring use cases
- Alternatives (GPT-4, Claude Sonnet) require paid API access, adding friction for a portfolio project

### Why Streamlit?

Zero frontend code, instant deployment on Streamlit Cloud, and native support for file uploaders and progress indicators. Right tool for a data/AI demo.

---

## Author

Built by [Vinay Dodla](https://github.com/vinay23is)

---

*Forked and extended from [rohini-sp/agentic-resume-screener](https://github.com/rohini-sp/agentic-resume-screener)*
