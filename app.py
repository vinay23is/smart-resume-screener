import os
import re
import streamlit as st
import streamlit.components.v1 as components
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

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

/* ── Reset Streamlit chrome ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #0d1117 !important;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}
[data-testid="stHeader"]       { display: none !important; }
[data-testid="stToolbar"]      { display: none !important; }
[data-testid="stDecoration"]   { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
#MainMenu, footer, header      { visibility: hidden !important; }
[data-testid="stMain"] > div   { padding-top: 1.5rem !important; }
[data-testid="block-container"] {
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
    max-width: 1100px !important;
}

/* ── Top bar ── */
.nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 0 1.5rem;
    border-bottom: 1px solid #161b22;
    margin-bottom: 2.5rem;
}
.nav-left { display: flex; align-items: center; gap: 10px; }
.nav-logo {
    font-size: 1.1rem;
    font-weight: 700;
    color: #e6edf3;
    letter-spacing: -0.01em;
}
.nav-logo em {
    font-style: normal;
    color: #10b981;
}
.nav-pill {
    font-size: 0.65rem;
    font-weight: 600;
    color: #10b981;
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 100px;
    padding: 2px 9px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.nav-right {
    font-size: 0.75rem;
    color: #30363d;
}
.nav-right a { color: #484f58; text-decoration: none; }
.nav-right a:hover { color: #8b949e; }

/* ── Field label ── */
.field-lbl {
    font-size: 0.68rem;
    font-weight: 600;
    color: #484f58;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.field-lbl::before {
    content: '';
    display: inline-block;
    width: 3px; height: 3px;
    border-radius: 50%;
    background: #10b981;
}

/* ── Inputs ── */
div[data-testid="stTextArea"] textarea {
    background: #0d1117 !important;
    color: #c9d1d9 !important;
    border: 1px solid #21262d !important;
    border-radius: 8px !important;
    font-size: 0.83rem !important;
    font-family: 'Inter', sans-serif !important;
    line-height: 1.7 !important;
    padding: 12px 14px !important;
    transition: border-color 0.15s !important;
    resize: vertical !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(16,185,129,0.4) !important;
    box-shadow: 0 0 0 3px rgba(16,185,129,0.07) !important;
    outline: none !important;
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background: #0d1117 !important;
    border: 1px dashed #21262d !important;
    border-radius: 8px !important;
    transition: border-color 0.15s !important;
    padding: 2rem !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: rgba(16,185,129,0.3) !important;
}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] div {
    color: #484f58 !important;
    font-size: 0.82rem !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Analyze button ── */
[data-testid="stButton"] > button[kind="primary"] {
    background: #10b981 !important;
    color: #0d1117 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    padding: 0.65rem 1.5rem !important;
    width: 100% !important;
    transition: background 0.15s, transform 0.1s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #0ea572 !important;
    transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="primary"]:active {
    transform: translateY(0) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    background: transparent !important;
    color: #484f58 !important;
    border: 1px solid #21262d !important;
    border-radius: 7px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    transition: border-color 0.15s, color 0.15s !important;
    width: 100% !important;
}
[data-testid="stDownloadButton"] > button:hover {
    border-color: #30363d !important;
    color: #8b949e !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: transparent !important;
    border: 1px solid #161b22 !important;
    border-radius: 7px !important;
    margin-bottom: 4px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #30363d !important;
    letter-spacing: 0.02em !important;
    padding: 10px 14px !important;
}
[data-testid="stExpander"] summary:hover { color: #484f58 !important; }
[data-testid="stExpander"] .stMarkdown {
    padding: 0 14px 12px !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 7px !important;
    font-size: 0.82rem !important;
    color: #8b949e !important;
}
hr[data-testid="stDivider"] {
    border-color: #161b22 !important;
    margin: 2rem 0 !important;
}

/* ── Result animations ── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fillBar {
    from { width: 0; }
}
@keyframes popIn {
    from { opacity: 0; transform: scale(0.92); }
    to   { opacity: 1; transform: scale(1); }
}

/* ── Score card ── */
.sc {
    background: #0d1117;
    border: 1px solid #161b22;
    border-top: 2px solid #10b981;
    border-radius: 10px;
    padding: 1.6rem 2rem;
    display: flex;
    align-items: center;
    gap: 2.5rem;
    margin-bottom: 1.25rem;
    animation: fadeUp 0.4s ease both;
}
.sc-num {
    font-size: 4rem;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.04em;
    flex-shrink: 0;
    font-variant-numeric: tabular-nums;
}
.sc-denom {
    font-size: 1.1rem;
    font-weight: 400;
    color: #30363d;
    margin-left: 4px;
}
.sc-right { flex: 1; min-width: 0; }
.sc-status {
    font-size: 0.88rem;
    font-weight: 600;
    margin-bottom: 10px;
}
.sc-bar-bg {
    height: 4px;
    background: #161b22;
    border-radius: 2px;
    overflow: hidden;
}
.sc-bar {
    height: 100%;
    border-radius: 2px;
    animation: fillBar 1.2s cubic-bezier(0.4,0,0.2,1) 0.2s both;
}
.sc-caption {
    font-size: 0.73rem;
    color: #30363d;
    margin-top: 6px;
}

/* ── Two-col grid ── */
.grid2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.25rem;
}
@media(max-width:640px){ .grid2 { grid-template-columns: 1fr; } }

/* ── Strength list ── */
.str-wrap { animation: fadeUp 0.4s ease 0.15s both; }
.str-head {
    font-size: 0.66rem;
    font-weight: 600;
    color: #484f58;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.str-row {
    display: flex;
    gap: 11px;
    align-items: flex-start;
    padding: 9px 0;
    border-bottom: 1px solid #161b22;
    animation: fadeUp 0.35s ease both;
}
.str-row:first-of-type { padding-top: 0; }
.str-row:last-child { border-bottom: none; padding-bottom: 0; }
.str-tick {
    width: 14px; height: 14px;
    border-radius: 50%;
    border: 1.5px solid #10b981;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    margin-top: 2px;
    font-size: 0.55rem;
    color: #10b981;
}
.str-title { font-size: 0.84rem; font-weight: 600; color: #c9d1d9; margin-bottom: 2px; }
.str-body  { font-size: 0.78rem; color: #484f58; line-height: 1.55; }

/* ── Missing chips ── */
.miss-wrap { animation: fadeUp 0.4s ease 0.2s both; }
.miss-head {
    font-size: 0.66rem;
    font-weight: 600;
    color: #484f58;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
    font-size: 0.74rem;
    font-weight: 500;
    color: #ffa198;
    background: rgba(255,129,130,0.07);
    border: 1px solid rgba(255,129,130,0.18);
    border-radius: 5px;
    padding: 4px 10px;
    animation: popIn 0.25s ease both;
}

/* ── Explanation ── */
.expl {
    border-left: 2px solid #10b981;
    padding: 1rem 1.25rem;
    margin-bottom: 1.25rem;
    animation: fadeUp 0.4s ease 0.25s both;
}
.expl-lbl {
    font-size: 0.66rem;
    font-weight: 600;
    color: #10b981;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.expl-text {
    font-size: 0.875rem;
    color: #8b949e;
    line-height: 1.8;
    font-style: italic;
}

/* ── File pill ── */
.fpill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px 6px 9px;
    border: 1px solid #161b22;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 500;
    color: #484f58;
    margin: 2rem 0 1.25rem;
}
.fpill-dot {
    width: 6px; height: 6px;
    background: #10b981;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ── Footer ── */
.footer {
    text-align: center;
    padding: 3rem 0 1.5rem;
    font-size: 0.73rem;
    color: #21262d;
}
.footer a { color: #30363d; text-decoration: none; }
.footer a:hover { color: #484f58; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Core logic (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([p.extract_text() or "" for p in pdf.pages])

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def get_resume_text(f):
    if f.name.endswith(".pdf"):  return extract_text_from_pdf(f)
    if f.name.endswith(".docx"): return extract_text_from_docx(f)
    return "Unsupported format."

def gemini_prompt(sys, usr):
    m = genai.GenerativeModel("gemini-1.5-flash")
    return m.generate_content([{"role":"user","parts":[sys+"\n\n"+usr]}]).text

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
            if 0 <= v <= 100: return v
    return None

def agentic_resume_screening(resume_text, jd):
    info = gemini_prompt(
        "You are a resume parser. Extract structured candidate details: "
        "skills, years of experience, education, certifications, achievements.",
        resume_text)
    match = gemini_prompt(
        "You are a senior recruiter. Start your response with exactly: "
        "'SCORE: XX/100'. Then list key matching skills and experiences.",
        f"Resume:\n{info}\n\nJob Description:\n{jd}")
    explain = gemini_prompt(
        "You are an HR business partner. Write 3-5 sentences in plain language "
        "explaining how well this candidate fits the role for a non-technical hiring manager.",
        match)
    missing = gemini_prompt(
        "List ONLY the skills and keywords in the JD that are absent from the resume. "
        "One short item per line, prefixed with •. No explanations.",
        f"Resume:\n{info}\n\nJob Description:\n{jd}")
    strengths = gemini_prompt(
        "Identify top 3-5 resume strengths for this specific job. "
        "Format: • Short title — one sentence why it matters for this role.",
        f"Resume:\n{info}\n\nJob Description:\n{jd}")
    return info, match, explain, missing, strengths

def generate_pdf(fname, info, match, explain, missing, strengths, score):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica","B",18)
    pdf.set_text_color(16,185,129)
    pdf.cell(0,12,"HireIQ — Resume Analysis",ln=True,align="C")
    pdf.set_font("Helvetica","",9)
    pdf.set_text_color(139,148,158)
    pdf.cell(0,6,fname,ln=True,align="C")
    pdf.ln(4)
    if score:
        c = (16,185,129) if score>=70 else (245,158,11) if score>=50 else (248,81,73)
        pdf.set_font("Helvetica","B",13)
        pdf.set_text_color(*c)
        pdf.cell(0,9,f"Match Score: {score} / 100",ln=True)
        pdf.ln(2)
    for t,b in [("Extracted Info",info),("Match Report",match),
                ("HR Summary",explain),("Missing Skills",missing),("Strengths",strengths)]:
        pdf.set_font("Helvetica","B",11)
        pdf.set_text_color(22,27,34)
        pdf.set_fill_color(246,248,250)
        pdf.cell(0,8,f"  {t}",ln=True,fill=True)
        pdf.set_font("Helvetica","",9)
        pdf.set_text_color(51,65,85)
        pdf.multi_cell(0,5,b.encode("latin-1","replace").decode("latin-1"))
        pdf.ln(2)
    return bytes(pdf.output())


# ─────────────────────────────────────────────────────────────────────────────
# HTML renderers
# ─────────────────────────────────────────────────────────────────────────────
def _bullets(text):
    return [
        l.strip().lstrip("•·▪-*").strip()
        for l in text.splitlines()
        if l.strip() and len(l.strip().lstrip("•·▪-*").strip()) > 1
    ]

def render_score(score):
    color = "#10b981" if score>=70 else "#f59e0b" if score>=50 else "#f85149"
    status = "Strong Match" if score>=70 else "Partial Match" if score>=50 else "Weak Match"
    caption = (
        "Candidate aligns well with the role."       if score>=70 else
        "Some gaps — review the details below."      if score>=50 else
        "Significant skill gaps identified."
    )
    return f"""
    <div class="sc">
      <div>
        <span class="sc-num" style="color:{color};">{score}</span>
        <span class="sc-denom">/ 100</span>
      </div>
      <div class="sc-right">
        <div class="sc-status" style="color:{color};">{status}</div>
        <div class="sc-bar-bg">
          <div class="sc-bar" style="width:{score}%; background:{color};"></div>
        </div>
        <div class="sc-caption">{caption}</div>
      </div>
    </div>"""

def render_strengths(text):
    rows = []
    for i, item in enumerate(_bullets(text)):
        delay = f"{0.3 + i*0.07:.2f}s"
        for sep in (" — "," - ",": "):
            if sep in item:
                t, b = item.split(sep,1)
                rows.append(f"""
                <div class="str-row" style="animation-delay:{delay};">
                  <div class="str-tick">✓</div>
                  <div>
                    <div class="str-title">{t.strip()}</div>
                    <div class="str-body">{b.strip()}</div>
                  </div>
                </div>""")
                break
        else:
            rows.append(f"""
            <div class="str-row" style="animation-delay:{delay};">
              <div class="str-tick">✓</div>
              <div><div class="str-title">{item}</div></div>
            </div>""")
    body = "".join(rows) or f'<p style="color:#30363d;font-size:0.8rem;margin:0;">{text}</p>'
    return f"""
    <div class="str-wrap">
      <div class="str-head">Top Strengths</div>
      {body}
    </div>"""

def render_missing(text):
    items = [i for i in _bullets(text) if len(i)<55]
    if not items:
        return f'<div class="miss-wrap"><div class="miss-head">Missing Skills</div><p style="color:#30363d;font-size:0.8rem;margin:0;">{text}</p></div>'
    chips = "".join(
        f'<span class="chip" style="animation-delay:{0.1+j*0.04:.2f}s;">{i}</span>'
        for j,i in enumerate(items)
    )
    return f"""
    <div class="miss-wrap">
      <div class="miss-head">Missing Skills</div>
      <div class="chips">{chips}</div>
    </div>"""

def render_explanation(text):
    safe = text.replace("<","&lt;").replace(">","&gt;")
    return f"""
    <div class="expl">
      <div class="expl-lbl">Recruiter Summary</div>
      <div class="expl-text">{safe}</div>
    </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# Sample JD
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_JD = """\
Software Engineer — Full Stack
Company: TechCorp Inc.

Looking for a Software Engineer experienced in:
• Python, JavaScript, TypeScript
• React, Node.js, REST APIs, GraphQL
• PostgreSQL, MongoDB, Redis
• AWS or GCP, Docker, Kubernetes
• CI/CD (GitHub Actions / Jenkins), Git, Agile

Responsibilities:
- Build scalable production web applications
- Collaborate with Product, Design, and Data teams
- Write clean, tested code; participate in code reviews

Requirements:
- B.S. in Computer Science or related field
- 2+ years professional development experience
- ML / data pipeline experience is a plus
"""


# ─────────────────────────────────────────────────────────────────────────────
# Layout
# ─────────────────────────────────────────────────────────────────────────────

# Nav
st.markdown("""
<div class="nav">
  <div class="nav-left">
    <span class="nav-logo">Hire<em>IQ</em></span>
    <span class="nav-pill">Beta</span>
  </div>
  <div class="nav-right">
    <a href="https://github.com/vinay23is/smart-resume-screener" target="_blank">GitHub ↗</a>
  </div>
</div>
""", unsafe_allow_html=True)

# Inputs
col_jd, col_up = st.columns([6, 5], gap="large")

with col_jd:
    st.markdown('<div class="field-lbl">Job Description</div>', unsafe_allow_html=True)
    job_description = st.text_area(
        "jd", value=SAMPLE_JD, height=300,
        label_visibility="collapsed",
        help="A sample JD is pre-filled — upload any resume to test.",
    )

with col_up:
    st.markdown('<div class="field-lbl">Resume — PDF or DOCX</div>', unsafe_allow_html=True)
    uploaded_resumes = st.file_uploader(
        "ul", type=["pdf","docx"], accept_multiple_files=True,
        label_visibility="collapsed",
    )
    st.caption("Multiple resumes supported.")

st.divider()

# ── Analyze ─────────────────────────────────────────────────────────────────
if st.button("Analyze Resume", type="primary", use_container_width=True):
    if not job_description.strip() or not uploaded_resumes:
        st.warning("Upload a resume and provide a job description to continue.")
    else:
        for file in uploaded_resumes:

            # File header
            st.markdown(f"""
            <div class="fpill">
              <div class="fpill-dot"></div>
              {file.name}
            </div>""", unsafe_allow_html=True)

            resume_text = get_resume_text(file)

            with st.spinner("Analyzing…"):
                info, match, explain, missing, strengths = (
                    agentic_resume_screening(resume_text, job_description)
                )

            score = extract_score(match)

            # Score
            if score is not None:
                st.markdown(render_score(score), unsafe_allow_html=True)
            else:
                st.info("Score not detected — see Match Report below.")

            # Strengths + Missing (Streamlit columns so layout stays intact)
            col_s, col_m = st.columns(2, gap="medium")
            with col_s:
                st.markdown(render_strengths(strengths), unsafe_allow_html=True)
            with col_m:
                st.markdown(render_missing(missing), unsafe_allow_html=True)

            # Explanation
            st.markdown(render_explanation(explain), unsafe_allow_html=True)

            # Raw agent outputs
            with st.expander("Agent 1 — Extracted Resume Info"):
                st.text(info)
            with st.expander("Agent 2 — Full Match Report"):
                st.text(match)

            # PDF download
            pdf = generate_pdf(file.name, info, match, explain, missing, strengths, score)
            st.download_button(
                "Download Report (PDF)",
                data=pdf,
                file_name=f"HireIQ_{file.name.rsplit('.',1)[0]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            st.divider()

# Footer
st.markdown("""
<div class="footer">
  Built by <a href="https://github.com/vinay23is" target="_blank">Vinay Dodla</a>
  &nbsp;·&nbsp;
  Powered by Gemini Flash
  &nbsp;·&nbsp;
  <a href="https://github.com/vinay23is/smart-resume-screener" target="_blank">View source</a>
</div>
""", unsafe_allow_html=True)
