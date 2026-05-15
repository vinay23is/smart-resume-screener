import os
import re
import streamlit as st
import pdfplumber
import docx
import google.generativeai as genai
from dotenv import load_dotenv
from fpdf import FPDF

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(
    page_title="HireIQ — AI Resume Screener",
    page_icon="🧠",
    layout="wide",
)

# ─── Design tokens ─────────────────────────────────────────────────────────
# bg:       #0d1117   surface: #161b22   border: #21262d
# text:     #e6edf3   muted:   #8b949e
# accent:   #10b981   warn:    #f59e0b   danger: #f85149

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Inter', system-ui, sans-serif;
}
[data-testid="stHeader"]  { background: transparent; }
[data-testid="stMain"] > div { padding-top: 0 !important; }
#MainMenu, footer { visibility: hidden; }

/* ─ Top bar ─ */
.topbar {
    border-bottom: 1px solid #21262d;
    padding: 1.1rem 0 1rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: baseline;
    gap: 12px;
}
.logo {
    font-size: 1.35rem;
    font-weight: 700;
    color: #e6edf3;
    letter-spacing: -0.01em;
}
.logo-dot { color: #10b981; }
.tagline {
    font-size: 0.78rem;
    color: #484f58;
    font-weight: 500;
}

/* ─ Section labels ─ */
.label {
    font-size: 0.7rem;
    font-weight: 600;
    color: #8b949e;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* ─ Score block ─ */
.score-block {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.25rem;
    display: flex;
    align-items: center;
    gap: 2rem;
}
.score-num {
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.03em;
    flex-shrink: 0;
}
.score-denom {
    font-size: 1rem;
    color: #484f58;
    font-weight: 400;
}
.score-right { flex: 1; min-width: 0; }
.score-status {
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 8px;
}
.score-bar-bg {
    background: #21262d;
    border-radius: 3px;
    height: 5px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 3px;
}

/* ─ Two-column result grid ─ */
.result-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.25rem;
}
@media(max-width:640px) { .result-grid { grid-template-columns: 1fr; } }

.rcard {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
}
.rcard-header {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8b949e;
    margin-bottom: 0.9rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #21262d;
}

/* Strength list */
.str-item {
    display: flex;
    gap: 10px;
    padding: 7px 0;
    border-bottom: 1px solid #161b22;
}
.str-item:first-child { padding-top: 0; }
.str-item:last-child { border-bottom: none; padding-bottom: 0; }
.str-bar {
    width: 2px;
    border-radius: 2px;
    background: #10b981;
    flex-shrink: 0;
    align-self: stretch;
    min-height: 14px;
}
.str-title { font-size: 0.83rem; font-weight: 600; color: #e6edf3; margin-bottom: 2px; }
.str-body  { font-size: 0.78rem; color: #8b949e; line-height: 1.5; }

/* Missing keyword chips */
.chips { display: flex; flex-wrap: wrap; gap: 5px; }
.chip {
    font-size: 0.74rem;
    font-weight: 500;
    color: #f85149;
    background: rgba(248,81,73,0.08);
    border: 1px solid rgba(248,81,73,0.2);
    border-radius: 5px;
    padding: 3px 9px;
}

/* ─ Explanation block ─ */
.explain {
    border-left: 3px solid #10b981;
    padding: 0.75rem 1rem;
    background: #161b22;
    border-radius: 0 8px 8px 0;
    margin-bottom: 1.25rem;
}
.explain-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #10b981;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.explain-text {
    font-size: 0.875rem;
    color: #8b949e;
    line-height: 1.75;
}

/* ─ File pill ─ */
.file-pill {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 0.82rem;
    font-weight: 500;
    color: #8b949e;
    margin: 1.5rem 0 1.1rem;
}
.file-pill-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #10b981;
    flex-shrink: 0;
}

/* ─ Expander ─ */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    margin-bottom: 6px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: #484f58 !important;
}
[data-testid="stExpander"] summary:hover { color: #8b949e !important; }

/* ─ Inputs ─ */
div[data-testid="stTextArea"] textarea {
    background: #161b22 !important;
    color: #e6edf3 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    font-size: 0.84rem !important;
    font-family: 'Inter', sans-serif !important;
    line-height: 1.65 !important;
    resize: vertical !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 2px rgba(16,185,129,0.12) !important;
    outline: none !important;
}
[data-testid="stFileUploaderDropzone"] {
    background: #161b22 !important;
    border: 1px dashed #21262d !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: #30363d !important;
}

/* ─ Primary button ─ */
[data-testid="stButton"] > button[kind="primary"] {
    background: #10b981 !important;
    color: #0d1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    padding: 0.6rem 1.5rem !important;
    transition: background 0.15s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #0ea572 !important;
}

/* ─ Download button ─ */
[data-testid="stDownloadButton"] > button {
    background: #161b22 !important;
    color: #8b949e !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    transition: border-color 0.15s, color 0.15s !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: #30363d !important;
    color: #e6edf3 !important;
}

/* ─ Misc ─ */
[data-testid="stAlert"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    font-size: 0.83rem !important;
}
hr[data-testid="stDivider"] {
    border-color: #21262d !important;
    margin: 1.5rem 0 !important;
}
.footer {
    text-align: center;
    padding: 2.5rem 0 1.2rem;
    font-size: 0.76rem;
    color: #30363d;
}
.footer a { color: #484f58; text-decoration: none; }
.footer a:hover { color: #8b949e; }
</style>
""", unsafe_allow_html=True)


# ─── Text extraction ────────────────────────────────────────────────────────
def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() or "" for p in pdf.pages])

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def get_resume_text(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        return extract_text_from_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        return extract_text_from_docx(uploaded_file)
    return "Unsupported file format."


# ─── Gemini ────────────────────────────────────────────────────────────────
def gemini_prompt(system_prompt, user_input):
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content(
        [{"role": "user", "parts": [system_prompt + "\n\n" + user_input]}]
    )
    return resp.text


# ─── Score parser ──────────────────────────────────────────────────────────
def extract_score(text):
    for pat in [
        r"SCORE\s*:\s*(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*/\s*100",
        r"[Ss]core[:\s]+(\d{1,3})",
        r"(\d{1,3})\s*out\s*of\s*100",
        r"(\d{1,3})\s*%",
    ]:
        m = re.search(pat, text)
        if m:
            v = int(m.group(1))
            if 0 <= v <= 100:
                return v
    return None


# ─── 5-Agent pipeline ──────────────────────────────────────────────────────
def agentic_resume_screening(resume_text, job_description):
    info = gemini_prompt(
        "You are a resume parser. Extract all structured candidate details: "
        "skills, years of experience, education, certifications, and key achievements.",
        resume_text,
    )
    match = gemini_prompt(
        "You are a senior recruiter. Match the resume to the job description. "
        "Start your response with exactly: 'SCORE: XX/100'. "
        "Then list key matching skills and experiences.",
        f"Resume Info:\n{info}\n\nJob Description:\n{job_description}",
    )
    explain = gemini_prompt(
        "You are an HR business partner. Write 3-5 sentences in plain language "
        "explaining how well this candidate fits the role, for a non-technical hiring manager.",
        match,
    )
    missing = gemini_prompt(
        "List ONLY the skills and keywords in the job description that are absent from the resume. "
        "One item per line, prefixed with •. No explanations, just the skill names.",
        f"Resume Info:\n{info}\n\nJob Description:\n{job_description}",
    )
    strengths = gemini_prompt(
        "Identify the top 3-5 resume strengths for this specific job. "
        "Format each as: • Short title — one-line reason it matters for this role.",
        f"Resume Info:\n{info}\n\nJob Description:\n{job_description}",
    )
    return info, match, explain, missing, strengths


# ─── HTML helpers ──────────────────────────────────────────────────────────
def _bullets(text):
    return [
        l.strip().lstrip("•·▪-*").strip()
        for l in text.splitlines()
        if l.strip() and len(l.strip().lstrip("•·▪-*").strip()) > 1
    ]

def strength_html(text):
    rows = []
    for item in _bullets(text):
        for sep in (" — ", " - ", ": "):
            if sep in item:
                t, b = item.split(sep, 1)
                rows.append(f"""
                <div class="str-item">
                  <div class="str-bar"></div>
                  <div>
                    <div class="str-title">{t.strip()}</div>
                    <div class="str-body">{b.strip()}</div>
                  </div>
                </div>""")
                break
        else:
            rows.append(f"""
            <div class="str-item">
              <div class="str-bar"></div>
              <div><div class="str-title">{item}</div></div>
            </div>""")
    return "".join(rows) or f'<p style="color:#484f58;font-size:0.82rem;">{text}</p>'

def chips_html(text):
    items = [i for i in _bullets(text) if len(i) < 50]
    if not items:
        return f'<p style="color:#484f58;font-size:0.82rem;">{text}</p>'
    return '<div class="chips">' + "".join(
        f'<span class="chip">{i}</span>' for i in items
    ) + "</div>"


# ─── PDF export ────────────────────────────────────────────────────────────
def generate_pdf_report(filename, extracted_info, match_report, explanation,
                        missing_keywords, top_strengths, score):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 12, "HireIQ — Resume Analysis Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(139, 148, 158)
    pdf.cell(0, 6, filename, ln=True, align="C")
    pdf.ln(5)
    if score is not None:
        clr = (16,185,129) if score >= 70 else (245,158,11) if score >= 50 else (248,81,73)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*clr)
        pdf.cell(0, 9, f"Match Score: {score} / 100", ln=True)
        pdf.ln(2)
    for title, body in [
        ("Extracted Resume Info",    extracted_info),
        ("Match Report",             match_report),
        ("HR-Friendly Explanation",  explanation),
        ("Missing Keywords",         missing_keywords),
        ("Top Strengths",            top_strengths),
    ]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(22, 27, 34)
        pdf.set_fill_color(246, 248, 250)
        pdf.cell(0, 8, f"  {title}", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 5, body.encode("latin-1", "replace").decode("latin-1"))
        pdf.ln(2)
    return bytes(pdf.output())


# ─── Sample JD ─────────────────────────────────────────────────────────────
SAMPLE_JD = """\
Software Engineer — Full Stack
Company: TechCorp Inc.

We are looking for a Software Engineer with experience in:
• Python, JavaScript, TypeScript
• React, Node.js, REST APIs and GraphQL
• SQL (PostgreSQL / MySQL) and NoSQL (MongoDB, Redis)
• Cloud platforms: AWS or GCP
• Docker, Kubernetes, CI/CD (GitHub Actions / Jenkins)
• Git, Agile / Scrum

Responsibilities:
- Build scalable, production-ready web applications
- Collaborate with Product, Design, and Data teams
- Write clean, tested code; participate in code reviews

Requirements:
- B.S. in Computer Science or related field
- 2+ years of software development experience
- Machine learning or data pipeline experience is a plus
"""


# ═══════════════════════════════════════════════════════════════════════════
# App layout
# ═══════════════════════════════════════════════════════════════════════════

# Top bar
st.markdown("""
<div class="topbar">
  <span class="logo">Hire<span class="logo-dot">IQ</span></span>
  <span class="tagline">AI Resume Screener</span>
</div>
""", unsafe_allow_html=True)

# Inputs
col_jd, col_up = st.columns([1, 1], gap="large")

with col_jd:
    st.markdown('<div class="label">Job Description</div>', unsafe_allow_html=True)
    job_description = st.text_area(
        "jd", value=SAMPLE_JD, height=280,
        label_visibility="collapsed",
        help="A sample JD is pre-filled — upload a resume to test immediately.",
    )

with col_up:
    st.markdown('<div class="label">Resume — PDF or DOCX</div>', unsafe_allow_html=True)
    uploaded_resumes = st.file_uploader(
        "ul", type=["pdf", "docx"], accept_multiple_files=True,
        label_visibility="collapsed",
    )
    st.caption("Upload multiple resumes to screen several candidates.")

st.divider()

if st.button("Analyze", type="primary", use_container_width=True):
    if not job_description.strip() or not uploaded_resumes:
        st.warning("Upload at least one resume and provide a job description.")
    else:
        for file in uploaded_resumes:

            # File pill
            st.markdown(f"""
            <div class="file-pill">
              <div class="file-pill-dot"></div>
              {file.name}
            </div>""", unsafe_allow_html=True)

            resume_text = get_resume_text(file)

            with st.spinner("Running analysis…"):
                extracted_info, match_report, explanation, missing_keywords, top_strengths = (
                    agentic_resume_screening(resume_text, job_description)
                )

            score = extract_score(match_report)
            color = (
                "#10b981" if score is not None and score >= 70 else
                "#f59e0b" if score is not None and score >= 50 else
                "#f85149"
            )
            status = (
                "Strong Match" if score is not None and score >= 70 else
                "Partial Match" if score is not None and score >= 50 else
                "Weak Match"
            )

            # Score block
            if score is not None:
                st.markdown(f"""
                <div class="score-block">
                  <div>
                    <span class="score-num" style="color:{color};">{score}</span>
                    <span class="score-denom"> / 100</span>
                  </div>
                  <div class="score-right">
                    <div class="score-status" style="color:{color};">{status}</div>
                    <div class="score-bar-bg">
                      <div class="score-bar-fill"
                           style="width:{score}%; background:{color};"></div>
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.info("Score not found — see Match Report below.")

            # Strengths + Missing
            col_s, col_m = st.columns(2, gap="medium")
            with col_s:
                st.markdown(f"""
                <div class="rcard">
                  <div class="rcard-header">Top Strengths</div>
                  {strength_html(top_strengths)}
                </div>""", unsafe_allow_html=True)
            with col_m:
                st.markdown(f"""
                <div class="rcard">
                  <div class="rcard-header">Missing Skills</div>
                  {chips_html(missing_keywords)}
                </div>""", unsafe_allow_html=True)

            # Explanation
            safe_explain = explanation.replace("<", "&lt;").replace(">", "&gt;")
            st.markdown(f"""
            <div class="explain">
              <div class="explain-label">Recruiter Summary</div>
              <div class="explain-text">{safe_explain}</div>
            </div>""", unsafe_allow_html=True)

            # Raw agent outputs
            with st.expander("Agent 1 — Extracted Resume Info"):
                st.text(extracted_info)
            with st.expander("Agent 2 — Full Match Report"):
                st.text(match_report)

            # Download
            pdf_bytes = generate_pdf_report(
                file.name, extracted_info, match_report, explanation,
                missing_keywords, top_strengths, score,
            )
            st.download_button(
                "Download Report (PDF)",
                data=pdf_bytes,
                file_name=f"HireIQ_{file.name.rsplit('.', 1)[0]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            st.divider()

# Footer
st.markdown("""
<div class="footer">
  Built by <a href="https://github.com/vinay23is" target="_blank">Vinay Dodla</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/vinay23is/smart-resume-screener" target="_blank">GitHub</a>
</div>
""", unsafe_allow_html=True)
