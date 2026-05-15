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

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HireIQ — AI Resume Screener",
    page_icon="🧠",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global background */
[data-testid="stAppViewContainer"] { background: #0f172a; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #1e293b; }

/* Main title */
.hire-iq-title {
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #818cf8 0%, #6366f1 50%, #4f46e5 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.hire-iq-sub {
    color: #64748b;
    font-size: 1rem;
    margin-bottom: 1.5rem;
    letter-spacing: 0.04em;
}

/* Metric card */
.score-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 1rem;
}
.score-label {
    color: #94a3b8;
    font-size: 0.85rem;
    margin-bottom: 6px;
}
.score-value {
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 8px;
}
.score-bar-track {
    background: #334155;
    border-radius: 6px;
    height: 14px;
    overflow: hidden;
}
.score-bar-fill {
    height: 100%;
    border-radius: 6px;
    transition: width 0.6s ease;
}

/* Section cards */
.section-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 1rem;
}
.section-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #c7d2fe;
    margin-bottom: 8px;
}

/* Footer */
.footer {
    text-align: center;
    padding: 2rem 0 1.2rem;
    color: #475569;
    font-size: 0.82rem;
}
.footer a { color: #6366f1; text-decoration: none; }
.footer a:hover { text-decoration: underline; }

/* Streamlit overrides */
div[data-testid="stTextArea"] textarea {
    background: #1e293b !important;
    color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
    border-radius: 8px !important;
}
div[data-testid="stFileUploader"] {
    background: #1e293b !important;
    border: 1px dashed #4f46e5 !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Resume text extraction ────────────────────────────────────────────────────
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

# ── Gemini helper ─────────────────────────────────────────────────────────────
def gemini_prompt(system_prompt, user_input):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(
        [{"role": "user", "parts": [system_prompt + "\n\n" + user_input]}]
    )
    return response.text

# ── Score parser ──────────────────────────────────────────────────────────────
def extract_score(text):
    patterns = [
        r"SCORE\s*:\s*(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*/\s*100",
        r"[Ss]core[:\s]+(\d{1,3})",
        r"(\d{1,3})\s*out\s*of\s*100",
        r"(\d{1,3})\s*%",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val
    return None

# ── 5-Agent pipeline ──────────────────────────────────────────────────────────
def agentic_resume_screening(resume_text, job_description):
    # Agent 1 — Extractor
    info = gemini_prompt(
        "You are a resume parser. Extract all structured candidate details: "
        "skills, years of experience, education, certifications, and key achievements. "
        "Be thorough and organised.",
        resume_text,
    )

    # Agent 2 — Matcher
    match = gemini_prompt(
        "You are a senior recruiter. Match the resume to the job description. "
        "Start your response with a line in EXACTLY this format: 'SCORE: XX/100' "
        "(replace XX with the numeric score). "
        "Then list the key matching skills and experiences.",
        f"Resume Info:\n{info}\n\nJob Description:\n{job_description}",
    )

    # Agent 3 — Explainer
    explain = gemini_prompt(
        "You are an HR business partner. Write a 3-5 sentence plain-language summary "
        "of how well this candidate fits the role, suitable for a hiring manager with "
        "no technical background.",
        match,
    )

    # Agent 4 — Missing Keywords
    missing = gemini_prompt(
        "You are a skills-gap analyst. List ONLY the skills, technologies, and keywords "
        "that appear in the job description but are ABSENT from the resume. "
        "Return a clean bullet list (• item). Be concise — no explanations needed.",
        f"Resume Info:\n{info}\n\nJob Description:\n{job_description}",
    )

    # Agent 5 — Top Strengths
    strengths = gemini_prompt(
        "You are a career coach. Identify the top 3-5 strengths of this resume "
        "relative to this specific job description. "
        "Return a bullet list where each point is: • Strength — one-line reason why it matters for this role.",
        f"Resume Info:\n{info}\n\nJob Description:\n{job_description}",
    )

    return info, match, explain, missing, strengths

# ── PDF export ────────────────────────────────────────────────────────────────
def generate_pdf_report(filename, extracted_info, match_report, explanation,
                        missing_keywords, top_strengths, score):
    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 14, "HireIQ  AI Resume Screener", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 7, f"Resume: {filename}", ln=True, align="C")
    pdf.ln(4)

    # Score badge
    if score is not None:
        color = (34, 197, 94) if score >= 70 else (245, 158, 11) if score >= 50 else (239, 68, 68)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*color)
        pdf.cell(0, 10, f"Match Score: {score}/100", ln=True)
        pdf.ln(2)

    sections = [
        ("Agent 1 — Extracted Resume Info", extracted_info),
        ("Agent 2 — Match Report", match_report),
        ("Agent 3 — HR-Friendly Explanation", explanation),
        ("Agent 4 — Missing Keywords", missing_keywords),
        ("Agent 5 — Top Strengths", top_strengths),
    ]

    for title, body in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 9, f"  {title}", ln=True, fill=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        safe = body.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 5.5, safe)
        pdf.ln(3)

    return bytes(pdf.output())

# ── Sample job description ────────────────────────────────────────────────────
SAMPLE_JD = """\
Software Engineer — Full Stack
Company: TechCorp Inc.

We are looking for a passionate Software Engineer with hands-on experience in:
• Python, JavaScript, TypeScript
• React, Node.js, REST APIs and GraphQL
• SQL (PostgreSQL / MySQL) and NoSQL databases (MongoDB, Redis)
• Cloud platforms: AWS or GCP
• Docker, Kubernetes, CI/CD pipelines (GitHub Actions / Jenkins)
• Git version control, Agile / Scrum methodology

Responsibilities:
- Design and develop scalable, production-ready web applications
- Collaborate with cross-functional teams (Product, Design, Data)
- Write clean, well-tested code; participate in code reviews
- Improve system reliability through monitoring and observability

Requirements:
- B.S. in Computer Science or related field
- 2+ years of professional software development experience
- Strong problem-solving and communication skills
- Experience with machine learning or data pipelines is a plus
"""

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<p class="hire-iq-title">🧠 HireIQ</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hire-iq-sub">AI-powered resume screener · '
    '5-agent Gemini Flash pipeline · instant PDF reports</p>',
    unsafe_allow_html=True,
)

# ── Input section ─────────────────────────────────────────────────────────────
col_jd, col_upload = st.columns([1, 1], gap="large")

with col_jd:
    job_description = st.text_area(
        "📋 Job Description",
        value=SAMPLE_JD,
        height=290,
        help="A sample JD is pre-filled — upload a resume and click Analyze to test immediately.",
    )

with col_upload:
    uploaded_resumes = st.file_uploader(
        "📂 Upload Resume(s) — PDF or DOCX",
        type=["pdf", "docx"],
        accept_multiple_files=True,
    )
    st.caption("Upload multiple resumes to screen several candidates at once.")

st.divider()

# ── Analyze button ────────────────────────────────────────────────────────────
if st.button("🔍 Analyze Resumes", type="primary", use_container_width=True):
    if not job_description.strip() or not uploaded_resumes:
        st.warning("Please upload at least one resume and provide a job description.")
    else:
        for file in uploaded_resumes:
            st.markdown(f"## 📄 {file.name}")

            resume_text = get_resume_text(file)

            with st.spinner("🧠 Running 5-agent AI pipeline…"):
                extracted_info, match_report, explanation, missing_keywords, top_strengths = (
                    agentic_resume_screening(resume_text, job_description)
                )

            score = extract_score(match_report)

            # ── Match score bar ───────────────────────────────────────────────
            if score is not None:
                bar_color = (
                    "#22c55e" if score >= 70 else
                    "#f59e0b" if score >= 50 else
                    "#ef4444"
                )
                st.markdown(f"""
                <div class="score-card">
                    <div class="score-label">Overall Match Score</div>
                    <div class="score-value" style="color:{bar_color};">{score}%</div>
                    <div class="score-bar-track">
                        <div class="score-bar-fill"
                             style="width:{score}%; background:{bar_color};"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Could not parse a numeric score — see Match Report below.")

            # ── Strengths & Missing Keywords (side-by-side) ───────────────────
            col_str, col_miss = st.columns(2, gap="medium")
            with col_str:
                with st.expander("✅ Top Strengths", expanded=True):
                    st.write(top_strengths)
            with col_miss:
                with st.expander("⚠️ Missing Keywords", expanded=True):
                    st.write(missing_keywords)

            # ── Agent outputs ─────────────────────────────────────────────────
            with st.expander("🕵️ Agent 1 — Extracted Resume Info"):
                st.text(extracted_info)
            with st.expander("🎯 Agent 2 — Match Report"):
                st.text(match_report)
            with st.expander("💬 Agent 3 — HR-Friendly Explanation"):
                st.write(explanation)

            # ── PDF download ──────────────────────────────────────────────────
            pdf_bytes = generate_pdf_report(
                file.name,
                extracted_info,
                match_report,
                explanation,
                missing_keywords,
                top_strengths,
                score,
            )
            stem = file.name.rsplit(".", 1)[0]
            st.download_button(
                label="📥 Download Full Report (PDF)",
                data=pdf_bytes,
                file_name=f"HireIQ_Report_{stem}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Built by
    <a href="https://github.com/vinay23is" target="_blank">Vinay Dodla</a>
    &nbsp;·&nbsp;
    Powered by Gemini Flash &amp; Streamlit
    &nbsp;·&nbsp;
    <a href="https://github.com/vinay23is/smart-resume-screener" target="_blank">View on GitHub</a>
</div>
""", unsafe_allow_html=True)
