"""
Batch evaluation for the HireIQ 5-stage pipeline.

Folder layout expected under --pairs-dir (default: eval_pairs/):
    eval_pairs/
        pair_001/
            resume.pdf   (or resume.docx)
            jd.txt
        pair_002/
            ...

For each pair the script:
  1. Runs all 5 pipeline stages and records per-stage latency.
  2. Runs the scoring stage 3× on the same input to measure consistency (±5 pts).
  3. Measures keyword recall: fraction of JD keywords absent from the resume
     that the gap-analysis agent actually flagged.

Summary printed to stdout and written to eval_results.csv.
"""

import argparse
import csv
import os
import re
import time
from pathlib import Path

import pdfplumber
import docx as python_docx
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

STOPWORDS = {
    "and","the","for","are","with","that","this","have","from","will",
    "your","you","our","their","been","also","into","more","than","its",
    "not","but","all","any","can","was","has","job","role","team","work",
    "such","must","able","both","each","who","they","what","how","when",
    "where","which","while","about","above","across","after","against",
    "along","among","around","because","before","behind","below","beside",
    "between","beyond","during","except","inside","outside","since","through",
    "under","until","upon","within","without","based","using","well","good",
    "high","strong","plus","including","experience","skills","year","years",
    "requirements","responsibilities","company","looking","build","write",
    "participate",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def extract_text(path: Path) -> str:
    if path.suffix == ".pdf":
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    if path.suffix == ".docx":
        doc = python_docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Unsupported format: {path.suffix}")


def gemini_call(system_prompt: str, user_text: str) -> tuple[str, float]:
    """Returns (response_text, latency_seconds)."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    t0 = time.perf_counter()
    resp = model.generate_content(
        [{"role": "user", "parts": [system_prompt + "\n\n" + user_text]}]
    )
    return resp.text, time.perf_counter() - t0


def extract_score(text: str):
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


def jd_keywords(jd_text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9.#+\-]{2,}", jd_text)
    return {t.lower() for t in tokens if t.lower() not in STOPWORDS}


def resume_has(keyword: str, resume_text: str) -> bool:
    return bool(re.search(re.escape(keyword), resume_text, re.IGNORECASE))


def missing_agent_flagged(keyword: str, missing_text: str) -> bool:
    return bool(re.search(re.escape(keyword), missing_text, re.IGNORECASE))


# ── pipeline ─────────────────────────────────────────────────────────────────

STAGE_PROMPTS = {
    "parser": (
        "You are a resume parser. Extract structured candidate details: "
        "skills, years of experience, education, certifications, achievements."
    ),
    "scorer": (
        "You are a senior recruiter. Start your response with exactly: "
        "'SCORE: XX/100'. Then list key matching skills and experiences."
    ),
    "explainer": (
        "You are an HR business partner. Write 3-5 sentences in plain language "
        "explaining how well this candidate fits the role for a non-technical hiring manager."
    ),
    "gap_analysis": (
        "List ONLY the skills and keywords in the JD that are absent from the resume. "
        "One short item per line, prefixed with •. No explanations."
    ),
    "strengths": (
        "Identify top 3-5 resume strengths for this specific job. "
        "Format: • Short title — one sentence why it matters for this role."
    ),
}


def run_pipeline(resume_text: str, jd: str) -> dict:
    """Run all 5 stages once; return texts + latencies."""
    result = {}

    info, t = gemini_call(STAGE_PROMPTS["parser"], resume_text)
    result["parser_text"] = info
    result["t_parser"] = t

    scorer_input = f"Resume:\n{info}\n\nJob Description:\n{jd}"
    match, t = gemini_call(STAGE_PROMPTS["scorer"], scorer_input)
    result["scorer_text"] = match
    result["t_scorer"] = t

    explain, t = gemini_call(STAGE_PROMPTS["explainer"], match)
    result["explainer_text"] = explain
    result["t_explainer"] = t

    gap_input = f"Resume:\n{info}\n\nJob Description:\n{jd}"
    missing, t = gemini_call(STAGE_PROMPTS["gap_analysis"], gap_input)
    result["gap_text"] = missing
    result["t_gap"] = t

    strengths, t = gemini_call(STAGE_PROMPTS["strengths"], gap_input)
    result["strengths_text"] = strengths
    result["t_strengths"] = t

    return result


def score_consistency(resume_text: str, jd: str, parsed_info: str, runs: int = 3) -> dict:
    """Run the scoring stage `runs` times and return consistency metrics."""
    scorer_input = f"Resume:\n{parsed_info}\n\nJob Description:\n{jd}"
    scores = []
    latencies = []
    for _ in range(runs):
        text, t = gemini_call(STAGE_PROMPTS["scorer"], scorer_input)
        s = extract_score(text)
        if s is not None:
            scores.append(s)
        latencies.append(t)
    spread = (max(scores) - min(scores)) if len(scores) >= 2 else None
    consistent = spread is not None and spread <= 5
    return {
        "scores": scores,
        "spread": spread,
        "consistent": consistent,
        "mean_score": round(sum(scores) / len(scores), 1) if scores else None,
    }


def keyword_recall(jd_text: str, resume_text: str, gap_text: str) -> dict:
    """
    Ground truth: keywords in JD that are NOT in resume.
    Predicted:    keywords that appear in the gap-analysis output.
    Recall = |predicted ∩ ground_truth| / |ground_truth|  (or 1.0 if GT is empty).
    """
    all_kw = jd_keywords(jd_text)
    truly_missing = {kw for kw in all_kw if not resume_has(kw, resume_text)}
    if not truly_missing:
        return {"recall": 1.0, "true_missing": 0, "flagged": 0, "total_kw": len(all_kw)}
    flagged = {kw for kw in truly_missing if missing_agent_flagged(kw, gap_text)}
    return {
        "recall": round(len(flagged) / len(truly_missing), 4),
        "true_missing": len(truly_missing),
        "flagged": len(flagged),
        "total_kw": len(all_kw),
    }


# ── evaluation loop ───────────────────────────────────────────────────────────

def evaluate_pairs(pairs_dir: Path, consistency_runs: int = 3) -> list[dict]:
    pairs = sorted(p for p in pairs_dir.iterdir() if p.is_dir())
    if not pairs:
        raise SystemExit(f"No subdirectories found in {pairs_dir}")

    rows = []
    for pair_dir in pairs:
        resume_path = None
        for ext in (".pdf", ".docx"):
            candidate = pair_dir / f"resume{ext}"
            if candidate.exists():
                resume_path = candidate
                break
        jd_path = pair_dir / "jd.txt"

        if resume_path is None or not jd_path.exists():
            print(f"  [SKIP] {pair_dir.name} — missing resume or jd.txt")
            continue

        print(f"\n{'─'*60}")
        print(f"  Pair: {pair_dir.name}  |  resume: {resume_path.name}")

        jd_text = jd_path.read_text(encoding="utf-8")
        resume_text = extract_text(resume_path)

        print("  Running main pipeline …")
        pipeline = run_pipeline(resume_text, jd_text)

        score = extract_score(pipeline["scorer_text"])
        print(f"    score={score}  t_parser={pipeline['t_parser']:.2f}s  "
              f"t_scorer={pipeline['t_scorer']:.2f}s  "
              f"t_explainer={pipeline['t_explainer']:.2f}s  "
              f"t_gap={pipeline['t_gap']:.2f}s  "
              f"t_strengths={pipeline['t_strengths']:.2f}s")

        print(f"  Running scorer {consistency_runs}× for consistency …")
        cons = score_consistency(
            resume_text, jd_text, pipeline["parser_text"], runs=consistency_runs
        )
        print(f"    scores={cons['scores']}  spread={cons['spread']}  "
              f"consistent={cons['consistent']}")

        print("  Computing keyword recall …")
        recall = keyword_recall(jd_text, resume_text, pipeline["gap_text"])
        print(f"    recall={recall['recall']:.1%}  "
              f"({recall['flagged']}/{recall['true_missing']} of {recall['total_kw']} JD keywords)")

        rows.append({
            "pair": pair_dir.name,
            "score": score,
            "t_parser": round(pipeline["t_parser"], 3),
            "t_scorer": round(pipeline["t_scorer"], 3),
            "t_explainer": round(pipeline["t_explainer"], 3),
            "t_gap": round(pipeline["t_gap"], 3),
            "t_strengths": round(pipeline["t_strengths"], 3),
            "consistency_scores": str(cons["scores"]),
            "score_spread": cons["spread"],
            "consistent": cons["consistent"],
            "kw_recall": recall["recall"],
            "true_missing_kw": recall["true_missing"],
            "flagged_kw": recall["flagged"],
        })

    return rows


def print_summary(rows: list[dict]) -> None:
    if not rows:
        print("\nNo results to summarize.")
        return

    def mean(vals):
        vals = [v for v in vals if v is not None]
        return round(sum(vals) / len(vals), 3) if vals else None

    print(f"\n{'═'*60}")
    print("  SUMMARY")
    print(f"{'═'*60}")
    print(f"  Pairs evaluated        : {len(rows)}")
    print(f"  Mean latency — parser  : {mean([r['t_parser']    for r in rows])}s")
    print(f"  Mean latency — scorer  : {mean([r['t_scorer']    for r in rows])}s")
    print(f"  Mean latency — explainer: {mean([r['t_explainer'] for r in rows])}s")
    print(f"  Mean latency — gap     : {mean([r['t_gap']       for r in rows])}s")
    print(f"  Mean latency — strengths: {mean([r['t_strengths'] for r in rows])}s")
    consistent = [r for r in rows if r["consistent"] is True]
    print(f"  Consistency rate (±5pt): {len(consistent)}/{len(rows)} "
          f"= {len(consistent)/len(rows):.1%}")
    print(f"  Mean keyword recall    : {mean([r['kw_recall'] for r in rows]):.1%}")
    print(f"{'═'*60}\n")


def save_csv(rows: list[dict], out_path: Path) -> None:
    if not rows:
        return
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Results written to: {out_path}")


# ── entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HireIQ batch evaluator")
    parser.add_argument(
        "--pairs-dir", default="eval_pairs",
        help="Root folder containing pair subdirectories (default: eval_pairs/)"
    )
    parser.add_argument(
        "--consistency-runs", type=int, default=3,
        help="Number of scorer re-runs per pair for consistency check (default: 3)"
    )
    parser.add_argument(
        "--out", default="eval_results.csv",
        help="Output CSV path (default: eval_results.csv)"
    )
    args = parser.parse_args()

    pairs_dir = Path(args.pairs_dir)
    if not pairs_dir.exists():
        raise SystemExit(f"Pairs directory not found: {pairs_dir}\n"
                         "Create eval_pairs/pair_001/resume.pdf + jd.txt etc.")

    rows = evaluate_pairs(pairs_dir, consistency_runs=args.consistency_runs)
    print_summary(rows)
    save_csv(rows, Path(args.out))


if __name__ == "__main__":
    main()
