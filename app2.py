import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
from email.message import EmailMessage
import smtplib
from pathlib import Path
from openai import OpenAI

# --- LLM Client Setup ---
client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "dummy")
)

# --- Streamlit Config ---
st.set_page_config(page_title="Agentic Job Apply — Minimal UI", layout="centered")
st.title("Quick-Apply — Agentic AI Job Submitter")
st.markdown(
    "Upload your resume, pick a date, and press Submit. The agent will generate ATS-optimized emails & resumes using Llama 3 and send applications to recruiters for all jobs on that date.\n\n"
    "**Frontend intentionally hides company/job details** so users can run bulk applies without reviewing each posting."
)

# --- Sidebar (Admin/Hidden) ---
st.sidebar.header("Admin / Upload (hidden from main UI)")
job_excel_upload = st.sidebar.file_uploader("(Hidden) Upload company job Excel (optional)", type=["xlsx", "xls"], key="hidden_jobs")
load_from_disk = st.sidebar.checkbox("Load jobs from local file 'company_jobs.xlsx' (if present)")

st.sidebar.markdown("---")
st.sidebar.header("LLM Configuration")
llama3_api_key = st.sidebar.text_input("Llama 3 API Key (or leave blank to use local placeholder)", type="password")

st.sidebar.markdown("---")
st.sidebar.header("SMTP (for sending emails)")
smtp_host = st.sidebar.text_input("SMTP host (eg smtp.gmail.com)")
smtp_port = st.sidebar.number_input("SMTP port", value=587)
smtp_user = st.sidebar.text_input("SMTP username / from-email")
smtp_pass = st.sidebar.text_input("SMTP password (app password)", type="password")

# --- Main UI ---
st.header("1) Upload / Update Document")
resume_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"], help="Resume will be used by the agent to craft an ATS-optimized version per-job")

st.header("2) Select date when you want to apply")
selected_date = st.date_input("Application date", value=datetime.today())

st.header("3) Submit — let the agent apply for you")
submit = st.button("Submit applications for selected date")

# --- Helper Functions ---

def read_jobs_source():
    """Read jobs dataframe from either uploaded file, local file, or fail."""
    df = None
    try:
        if job_excel_upload is not None:
            df = pd.read_excel(job_excel_upload)
        elif load_from_disk and Path("company_jobs.xlsx").exists():
            df = pd.read_excel("company_jobs.xlsx")
        else:
            st.sidebar.info("No jobs source provided. Please upload via the sidebar (hidden) or place company_jobs.xlsx next to the app.")
            return None
        df.columns = [c.lower().strip() for c in df.columns]
        return df
    except Exception as e:
        st.sidebar.error(f"Failed to read jobs excel: {e}")
        return None

def extract_text_from_resume(uploaded_file) -> str:
    """Extract text from PDF or DOCX resume."""
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    try:
        if name.endswith('.pdf'):
            from PyPDF2 import PdfReader
            reader = PdfReader(uploaded_file)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith('.docx'):
            from docx import Document
            doc = Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        st.sidebar.warning(f"Resume text extraction failed: {e}")
    return ""

def name_to_email(name: str, company_domain: str) -> str:
    """Generate fallback recruiter email from name and domain."""
    parts = re.findall(r"[A-Za-z]+", str(name))
    if not parts:
        return f"hr@{company_domain}"
    local = f"{parts[0][0].lower()}.{parts[-1].lower()}" if len(parts) > 1 else parts[0].lower()
    return f"{local}@{company_domain}"

def extract_domain_from_company(company_name: str) -> str:
    """Create a plausible domain from company name."""
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", str(company_name)).split()
    return (''.join(cleaned[:2]).lower() + ".com") if cleaned else "example.com"

def generate_pdf_from_text(text: str) -> bytes:
    """Generate PDF bytes from text using reportlab."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    from io import BytesIO
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    flow = [Paragraph(text, styles["Normal"])]
    doc.build(flow)
    return buffer.getvalue()

def llama3_generate(job: dict, resume_text: str):
    """Call LLaMA 3 to generate a custom email + ATS-optimized resume PDF."""
    prompt = f"""
You are an AI job application assistant. 
User's original resume:
{resume_text}

Job description:
{job.get('job description', '')}

Recruiter: {job.get('recruiter name', 'Unknown')}

TASKS:
1. Rewrite the resume to maximize ATS score for this job. 
2. Generate a professional, concise email for applying.
Return your output as JSON with keys:
- subject
- email_body
- resume_text (optimized)
"""
    response = client.chat.completions.create(
        model="llama3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    import json
    content = response.choices[0].message.content
    try:
        result = json.loads(content)
    except Exception:
        result = {"subject": "Job Application", "email_body": content, "resume_text": resume_text}
    pdf_bytes = generate_pdf_from_text(result["resume_text"])
    return result["subject"], result["email_body"], pdf_bytes

def send_email(subject, body, pdf_bytes, recipient, company_name):
    """Send email with PDF attachment via SMTP."""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = recipient
    msg.set_content(body)
    msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f"resume_{company_name or 'app'}.pdf")
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

def filter_jobs_by_date(jobs_df, sel_date):
    """Filter jobs DataFrame by selected date."""
    date_cols = [c for c in jobs_df.columns if 'date' in c]
    if not date_cols:
        st.error("Jobs sheet must include a date column (e.g., 'date', 'posted date').")
        return None, None
    date_col = date_cols[0]
    jobs_df[date_col] = pd.to_datetime(jobs_df[date_col]).dt.date
    matches = jobs_df[jobs_df[date_col] == sel_date]
    return matches, date_col

def save_log(results, sel_date):
    """Save application results log."""
    logs_path = Path('agent_apply_logs')
    logs_path.mkdir(exist_ok=True)
    log_file = logs_path / f"apply_log_{sel_date}.csv"
    pd.DataFrame(results).to_csv(log_file, index=False)
    st.sidebar.info(f"A private log was saved to: {log_file}")

# --- Submission Flow ---
if submit:
    if resume_file is None:
        st.error("Please upload your resume before submitting.")
    else:
        jobs_df = read_jobs_source()
        if jobs_df is None or jobs_df.empty:
            st.error("No jobs data available. Upload the company_jobs.xlsx via the sidebar or enable load_from_disk.")
        else:
            matches, date_col = filter_jobs_by_date(jobs_df, selected_date)
            if matches is None:
                pass  # error already shown
            elif matches.empty:
                st.warning("No job postings found for this date.")
            else:
                st.info(f"Found {len(matches)} job(s) for {selected_date}. The agent will attempt to apply to all without showing company details.")
                resume_text = extract_text_from_resume(resume_file)
                results = []
                progress = st.progress(0)
                total = len(matches)
                for i, (idx, row) in enumerate(matches.iterrows(), 1):
                    company_name = row.get('company name', '')
                    recruiter_name = row.get('recruiter name', '')
                    recruiter_email = row.get('recruiter email', '')
                    subj, body, pdf_bytes = llama3_generate(row, resume_text)
                    recipient = recruiter_email if pd.notna(recruiter_email) and recruiter_email else name_to_email(recruiter_name or 'hr', extract_domain_from_company(company_name))
                    status, err_msg = "generated (smtp not configured)", None
                    if smtp_host and smtp_user and smtp_pass:
                        try:
                            send_email(subj, body, pdf_bytes, recipient, company_name)
                            status = 'sent'
                        except Exception as e:
                            status = 'error'
                            err_msg = str(e)
                    results.append({'_row_index': int(idx), 'recipient': recipient, 'status': status, 'error': err_msg})
                    progress.progress(int(i / total * 100))
                sent_count = sum(1 for r in results if r['status'] in ('sent', 'generated (smtp not configured)'))
                err_count = sum(1 for r in results if r['status'] == 'error')
                st.success(f"Agent finished — {sent_count} generated/sent, {err_count} errors.")
                st.write("Result summary (company identities hidden):")
                st.table(pd.DataFrame(results))
                save_log(results, selected_date)

