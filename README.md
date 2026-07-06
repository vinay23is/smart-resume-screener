# HireIQ — AI Resume Screener

A multi-agent AI system that screens resumes against a job description in seconds: upload one or more PDF/DOCX resumes, paste a job description, and get a match score, top strengths, missing keywords, and a downloadable PDF report.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Gemini Flash](https://img.shields.io/badge/Gemini%20Flash-Free%20Tier-4285F4?style=flat&logo=google&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![Multi-Agent AI](https://img.shields.io/badge/Multi--Agent%20AI-5-6366F1?style=flat)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat)

> **Note on origin:** this repo started as a fork of [rohini-sp/agentic-resume-screener](https://github.com/rohini-sp/agentic-resume-screener), which had a basic resume-vs-JD matching flow. Everything past the initial commit is original work built on top of that idea: rebranding to HireIQ, expanding it into a 5-agent pipeline, three full UI rewrites, PDF export, and a batch evaluation harness. `app.py` alone has grown from the forked base to ~1,100 lines. There is no live deployment currently up for this one — see "Running Locally" below to run it yourself.

## What problem does this solve?
Reviewing a stack of resumes against a job description is repetitive and inconsistent — different reviewers weigh things differently, and it's easy to miss a candidate's relevant experience buried on page two. This project automates the first pass: it extracts structured info from a resume, scores it against a job description, explains the score in plain language for a non-technical hiring manager, and calls out both the candidate's strengths and the gaps versus the JD — all from one upload.

## Tech Stack
- **UI:** Streamlit (custom dark theme, hand-built CSS on top of Streamlit's default chrome)
- **AI:** Google Gemini Flash (`google-generativeai`), free tier
- **Resume parsing:** `pdfplumber` (PDF), `python-docx` (DOCX)
- **Report export:** `fpdf2` for downloadable PDF reports
- **Config:** `python-dotenv` / Streamlit Secrets for the API key
- **Evaluation:** standalone batch harness (`evaluate_batch.py`) for latency, scoring consistency, and keyword-recall metrics

## Architecture
This is the core design decision worth explaining in an interview: instead of one giant prompt trying to extract, match, explain, and gap-analyze in a single call, the app chains five narrow, single-purpose Gemini agents, each with its own prompt and persona.
```
Resume Text + JD
       |
       v
Agent 1 -- Resume Extractor     parses raw text into structured info
       | structured info         (skills, education, experience)
       v
Agent 2 -- Matcher              scores fit ("SCORE: XX/100") and
       | match report            lists key matching areas
       v
Agent 3 -- HR Explainer         3-5 sentence plain-language summary
                                 for non-technical hiring managers

[Agents 4 and 5 run in parallel off Agent 1's output]

Agent 4 -- Gap Analyst          keywords in the JD absent from the resume
Agent 5 -- Career Coach         top 3-5 resume strengths for this role
```
Each agent's output is parsed with a regex (e.g. `extract_score()` pulls the `SCORE: XX/100` pattern out of Agent 2's free-text response) and rendered into its own UI section, so a bad output from one agent doesn't corrupt the others.

## Key Features
- Parses both PDF and DOCX resumes automatically.
- Runs the 5-agent Gemini pipeline to extract, match, explain, and gap-analyze in one pass.
- Displays a 0-100 match score with a color-coded gauge, a list of top strengths, and a list of missing keywords versus the JD.
- Generates an HR-friendly plain-language explanation of the score.
- Exports the full analysis as a downloadable PDF report.
- Supports multiple resumes in one run, so a whole candidate pool can be screened at once.
- `evaluate_batch.py` runs the full pipeline against a folder of resume/JD pairs, measures per-stage latency, checks scoring consistency by re-running the scoring stage 3x on the same input, and measures keyword recall on the gap-analysis agent.

## Interesting Engineering Decisions
- **Router/specialist agent split over one mega-prompt:** a single prompt asking for extraction + matching + scoring + gap analysis + strengths in one shot produced inconsistent, tangled output during development. Splitting into five focused agents made each piece independently debuggable and easier to reason about when something goes wrong.
- **Regex extraction over structured output APIs:** the match score is pulled from free-text with a targeted regex (`SCORE\s*:\s*(\d{1,3})\s*/\s*100`) rather than a JSON schema call — a pragmatic choice given the free-tier Gemini SDK version in use, with the tradeoff being it's more brittle to prompt-format drift than schema-constrained output.
- **Scoring consistency is measured, not assumed:** `evaluate_batch.py` re-runs the scoring stage 3 times per resume/JD pair specifically to catch cases where the same input produces a wildly different score — important for a tool whose whole value proposition is a trustworthy number.
- **Gemini Flash over GPT-4/Claude:** free tier with generous rate limits and no billing account needed, which matters for a project meant to be cloned and run by anyone without a paid API dependency.

## Running Locally
```bash
git clone https://github.com/vinay23is/smart-resume-screener.git
cd smart-resume-screener
pip install -r requirements.txt

echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
# get a free key at https://aistudio.google.com -- no billing required

streamlit run app.py
```
Open `http://localhost:8501`. A sample job description is pre-filled so you can test immediately by uploading any resume.

Run the batch evaluation:
```bash
python evaluate_batch.py --pairs-dir eval_pairs/
```

## Author
Built by [Vinay Dodla](https://github.com/vinay23is), forked and extended from [rohini-sp/agentic-resume-screener](https://github.com/rohini-sp/agentic-resume-screener).
