# HireIQ — Interview Prep Guide

Use this doc to confidently answer any recruiter or technical interviewer question about this project.

---

## Q: What does this app do?

**Answer:**

HireIQ is an AI-powered resume screening tool. You upload a resume (PDF or DOCX) and paste a job description, and the system analyses how well the candidate fits the role. It gives you:

- A numeric match score (0–100) shown as a colour-coded progress bar
- A list of the candidate's top strengths relative to this specific job
- A list of keywords and skills in the JD that are missing from the resume
- A plain-language HR summary, readable by non-technical hiring managers
- A downloadable PDF report with the full analysis

The whole thing runs in seconds using Google Gemini Flash's free tier, so there is no cost to operate it.

---

## Q: What is a multi-agent system and why did you use one?

**Answer:**

A multi-agent system is an architecture where you break a complex task into smaller, specialised sub-tasks, each handled by a separate AI "agent" — meaning a separate prompt with its own role, persona, and defined output format. The agents run in sequence (or in parallel), and each one's output feeds the next.

I used this approach instead of a single monolithic prompt for three reasons:

1. **Reliability.** One giant prompt asking for extraction + matching + scoring + gap analysis + strengths in a single call produces inconsistent, unstructured output. Specialised agents each do one thing well.

2. **Debuggability.** If the match score is wrong, I know it's Agent 2. If the extraction is missing a skill, it's Agent 1. I can fix agents independently.

3. **Explainability.** When presenting to a non-technical audience, I can describe each agent as a job role (parser, recruiter, HR manager, gap analyst, career coach) that maps to something they already understand.

---

## Q: How does each agent work?

**Answer:**

**Agent 1 — Resume Extractor**
- Input: raw resume text (extracted by pdfplumber or python-docx)
- Persona: "You are a resume parser"
- Output: structured list of skills, experience, education, and achievements
- Why: transforms messy raw text into clean structured data that downstream agents can reason about

**Agent 2 — Matcher**
- Input: Agent 1 output + job description
- Persona: "You are a senior recruiter"
- Output: a score in the format `SCORE: XX/100` plus key matching areas
- Why: the explicit format instruction (`SCORE: XX/100`) lets me reliably parse the numeric value with a regex, without needing a JSON schema or structured output API

**Agent 3 — HR Explainer**
- Input: Agent 2's match report
- Persona: "You are an HR business partner"
- Output: 3-5 sentence plain-language narrative
- Why: hiring managers don't want bullet points — they want a recommendation they can act on

**Agent 4 — Gap Analyst**
- Input: Agent 1 output + job description
- Persona: "You are a skills-gap analyst"
- Output: bullet list of missing keywords/skills
- Why: surfacing gaps is more actionable than just a score — the candidate knows what to learn or how to tailor their resume

**Agent 5 — Career Coach**
- Input: Agent 1 output + job description
- Persona: "You are a career coach"
- Output: top 3-5 bullet-point strengths with one-line rationale per point
- Why: a score alone doesn't tell recruiters what they're getting — the strengths section gives them a reason to pick up the phone

---

## Q: Why Gemini Flash specifically?

**Answer:**

Three practical reasons:

1. **Free tier.** Google AI Studio provides Gemini 1.5 Flash access with no billing required. For a portfolio project, that means $0/month to keep it running.

2. **Speed.** Flash is Google's throughput-optimised model — it's significantly faster than larger models like Gemini Pro or GPT-4. Since my pipeline makes 5 sequential API calls per resume, speed compounds.

3. **Sufficient capability.** Resume screening doesn't require frontier-level reasoning. Flash handles structured extraction, scoring, and plain-language summarisation reliably. Using a more expensive model would be over-engineering.

---

## Q: What would you improve with more time?

**Answer:**

1. **Parallel agent execution.** Currently Agents 4 and 5 run sequentially. They both only need Agent 1's output, so I could fire them concurrently with `asyncio` or `concurrent.futures` — cutting latency roughly in half.

2. **Structured output.** Instead of parsing a score with regex, I'd use Gemini's JSON mode or function-calling to get a typed object back from Agent 2. More robust.

3. **Bias detection.** Add an Agent 6 that flags potentially biased language in the job description or identifies if the scoring correlates with non-job-relevant factors.

4. **Database + history.** Persist screening results in a lightweight database (SQLite or Supabase) so recruiters can compare candidates across sessions and track decisions over time.

5. **Candidate ranking.** When multiple resumes are uploaded, auto-sort them by match score and produce a comparison table.

6. **Resume rewrite suggestions.** An additional agent that suggests specific changes the candidate could make to improve their score for this JD.

---

## Q: How is this different from just prompting ChatGPT?

**Answer:**

Pasting a resume into ChatGPT and asking "how good is this?" gives you a one-shot, unstructured answer that varies every time you ask. It doesn't parse files automatically, doesn't extract structured data, can't handle multiple resumes systematically, and produces no downloadable artifact.

HireIQ is a product, not a prompt. Specific differences:

- **File handling.** Supports PDF and DOCX upload with proper text extraction, including multi-page documents.
- **Structured pipeline.** Five agents with defined roles, consistent output formats, and a regex-parsed numeric score you can sort or filter on.
- **UI.** A real web app with progress bars, expandable sections, and a one-click PDF export.
- **Reproducibility.** The same resume + JD pair runs through the exact same pipeline every time, making comparisons fair.
- **No copy-paste.** Recruiters don't manually touch the AI — they upload, click, and get a report.

The architecture is also worth noting: this is closer to an agentic workflow (the term used in AI engineering for chaining LLM calls with specialised roles) than a simple chatbot interaction.

---

## Quick facts for recruiter screens

| Question | Answer |
|---|---|
| Language | Python |
| AI model | Google Gemini 1.5 Flash |
| UI framework | Streamlit |
| Deployment | Streamlit Cloud (free) |
| API cost | $0 — Gemini free tier |
| File formats | PDF, DOCX |
| Agents | 5 |
| Key output | Match score, strengths, gaps, PDF report |
| Repo | github.com/vinay23is/smart-resume-screener |
