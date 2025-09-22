import streamlit as st
import pandas as pd
import io
import re
import os
from datetime import datetime
from email.message import EmailMessage
import smtplib
from pathlib import Path

# Optional libraries you'll need to install:
# pip install python-docx PyPDF2 reportlab openpyxl
from docx import Document
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="AI Job Mail & Resume Sender", layout="wide")

st.title("AI-assisted Job Application Sender")
st.markdown(
    """
    Upload your resume (PDF or DOCX) and the company's job Excel sheet. Select a date and company, preview the generated email & ATS-optimized resume, then send directly to the recruiter's email (or a domain-derived email if missing).

    **Notes:**
    - The code contains hooks where you can plug an LLM (OpenAI or other) to generate crisp emails and resume content. Currently the app can fall back to a simple template generator.
    - You must supply SMTP credentials to enable sending.
    """
)

# Sidebar: SMTP and AI configuration
st.sidebar.header("Configuration")
smtp_host = st.sidebar.text_input("SMTP host (eg. smtp.gmail.com)")
smtp_port = st.sidebar.number_input("SMTP port", value=587)
smtp_user = st.sidebar.text_input("SMTP username / from-email")
smtp_pass = st.sidebar.text_input("SMTP password (or app password)", type="password")

use_llm = st.sidebar.checkbox("Use LLM for email/resume generation (requires API integration)", value=False)
if use_llm:
    st.sidebar.info("Add your LLM integration in the code at the generate_email_and_resume() function.")

# Upload files
st.header("1) Upload files")
resume_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
job_excel = st.file_uploader("Upload company's job details Excel (xlsx)", type=["xlsx", "xls"])

if job_excel is None:
    st.info("Please upload the job details Excel file. The app expects a sheet with columns: serial number, date, company name, job description, recruiter name, recruiter email (optional).")

# Helper functions

def read_jobs_from_excel(file) -> pd.DataFrame:
    # Try to read the first sheet that contains required columns
    try:
        df = pd.read_excel(file, sheet_name=None)
    except Exception as e:
        st.error(f"Failed to read excel: {e}")
        raise
    # find a sheet with required columns
    required = ["serial number", "date", "company name", "job description", "recruiter name"]
    for name, sheet in df.items():
        cols = [c.lower().strip() for c in sheet.columns]
        if all(r in cols for r in required):
            # normalize columns
            sheet.columns = [c.lower().strip() for c in sheet.columns]
            return sheet
    # fallback: try first sheet but normalize
    first = list(df.values())[0]
    first.columns = [c.lower().strip() for c in first.columns]
    return first


def extract_text_from_resume(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    uploaded_file.seek(0)
    if name.endswith('.pdf'):
        try:
            reader = PdfReader(uploaded_file)
            texts = []
            for page in reader.pages:
                texts.append(page.extract_text() or "")
            return "\n".join(texts)
        except Exception as e:
            st.warning(f"Could not extract text from PDF: {e}")
            return ""
    elif name.endswith('.docx'):
        try:
            doc = Document(uploaded_file)
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            st.warning(f"Could not extract text from DOCX: {e}")
            return ""
    else:
        return ""


def create_pdf_from_text(text: str, output_path: str, title: str = "Resume"):
    # Simple PDF renderer using reportlab
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    margin = 40
    y = height - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, title)
    y -= 24
    c.setFont("Helvetica", 10)
    lines = text.splitlines()
    for line in lines:
        if y < margin + 20:
            c.showPage()
            y = height - margin
            c.setFont("Helvetica", 10)
        # wrap long lines
        if len(line) > 120:
            chunks = [line[i:i+120] for i in range(0, len(line), 120)]
            for ch in chunks:
                c.drawString(margin, y, ch)
                y -= 12
        else:
            c.drawString(margin, y, line)
            y -= 12
    c.save()


def name_to_email(name: str, company_domain: str) -> str:
    # crude conversion: 'John Doe' -> j.doe@company.com or john.doe@company.com
    parts = re.findall(r"[A-Za-z]+", name)
    if not parts:
        return f"hr@{company_domain}"
    if len(parts) == 1:
        local = parts[0].lower()   
    else:
        local = f"{parts[0][0].lower()}.{parts[-1].lower()}"
    return f"{local}@{company_domain}"


def extract_domain_from_company(company_name: str) -> str:
    # crude heuristic: take company name words and append .com
    # You should replace this with a proper domain lookup or a mapping file.
    cleaned = re.sub(r"[^A-Za-z0-9 ]", "", company_name).split()
    if not cleaned:
        return "example.com"
    domain = ''.join(cleaned[:2]).lower() + ".com"
    return domain


def ats_score_resume(job_desc: str, resume_text: str) -> int:
    # very simple ATS-ish matcher: count keyword overlaps
    jd = job_desc.lower()
    # extract words >3 chars
    words = set(re.findall(r"\b[a-z]{4,}\b", jd))
    resume_words = set(re.findall(r"\b[a-z]{4,}\b", resume_text.lower()))
    if not words:
        return 0
    overlap = words & resume_words
    score = int(100 * len(overlap) / len(words))
    return score


def generate_email_and_resume(job_row: pd.Series, resume_text: str, use_llm_flag=False) -> (str, bytes):
    # This is the central function that should call an LLM ideally.
    # If use_llm_flag is True, replace the body here with a call to your LLM (OpenAI, etc.)
    # The LLM prompt should include job description, recruiter's name, company, and resume_text.

    company = str(job_row.get('company name', ''))
    jd = str(job_row.get('job description', ''))
    rec_name = str(job_row.get('recruiter name', ''))

    # Basic template email
    subj = f"Application for role — {company}"
    greeting = f"Dear {rec_name.split()[0] if rec_name else 'Hiring Team'},"
    body = (
        f"{greeting}\n\n"
        f"I hope you're well. I'm writing to apply for the role posted at {company}. Attached is my resume that highlights relevant experience and skills for this position. "
        f"I've worked on projects and roles that directly match the requirements listed in your job description, including: \n"
    )
    # include short bullets by extracting key phrases from job description (naive approach)
    bullets = re.findall(r"[A-Z][a-zA-Z0-9 \-]{4,50}", jd)
    if bullets:
        sample = '\n'.join([f"- {b.strip()}" for b in bullets[:4]])
        body += sample + "\n\n"
    body += (
        "I'd love to discuss how my background can add value to your team. "
        "Please find my ATS-optimized resume attached.\n\n"
        "Best regards,\n[Your Name]"
    )

    # Create a simple ATS-optimized resume: try to include top keywords from job description
    # naive keyword extraction: top frequent words
    tokens = re.findall(r"\b[a-z]{4,}\b", jd.lower())
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    top = sorted(freq.items(), key=lambda x: -x[1])[:10]
    keywords = [k for k, _ in top]

    resume_builder = []
    resume_builder.append(f"Name: [Your Name]")
    resume_builder.append(f"Contact: [Your Email] | [Your Phone]")
    resume_builder.append("\nSummary:\nMotivated professional with experience relevant to the role. Key strengths include: " + ', '.join(keywords))
    resume_builder.append("\nExperience:\n" + (resume_text[:2000] if resume_text else "Add your relevant experience here."))
    resume_builder.append("\nSkills:\n" + ', '.join(keywords))

    final_resume_text = "\n\n".join(resume_builder)

    # Convert to PDF bytes
    out_path = "temp_resume_output.pdf"
    create_pdf_from_text(final_resume_text, out_path, title=f"Resume - {company}")
    with open(out_path, 'rb') as f:
        pdf_bytes = f.read()
    try:
        os.remove(out_path)
    except:
        pass

    # If using LLM, you'd replace subj/body/final_resume_text with LLM outputs
    return subj, body, pdf_bytes


# Main app logic
if job_excel is not None:
    jobs_df = read_jobs_from_excel(job_excel)
    # normalize columns expectations
    jobs_df.columns = [c.lower().strip() for c in jobs_df.columns]
    # show unique companies
    companies = sorted(jobs_df['company name'].dropna().unique())

    st.header("2) Select date and company")
    chosen_date = st.date_input("Application date", value=datetime.today())
    company_choice = st.selectbox("Choose company", options=["-- select --"] + list(companies))

    # filter jobs for chosen company
    filtered = jobs_df[jobs_df['company name'] == company_choice] if company_choice and company_choice != "-- select --" else jobs_df
    st.write(f"Showing {len(filtered)} rows for selection")

    # show job rows in a table and let user pick a row
    st.header("3) Pick a job row to apply to")
    st.dataframe(filtered.reset_index(drop=True))

    row_index = st.number_input("Enter the index (0-based) of the row to apply", min_value=0, max_value=max(0, len(filtered)-1), value=0)
    if len(filtered) == 0:
        st.warning("No jobs available for this company. Upload a proper excel.")
    else:
        job_row = filtered.reset_index(drop=True).iloc[int(row_index)]
        st.subheader("Selected job")
        st.write(job_row)

        # Extract resume text
        resume_text = extract_text_from_resume(resume_file)
        if not resume_text:
            st.warning("Resume text could not be extracted. For best results, upload a DOCX. The app will still try to create a resume PDF from templates.")

        # Preview generation
        st.header("4) Preview generated email & resume")
        show_preview = st.checkbox("Generate preview now")
        if show_preview:
            subj, body, pdf_bytes = generate_email_and_resume(job_row, resume_text, use_llm_flag=use_llm)
            st.markdown("**Subject:** " + subj)
            st.markdown("**Body:**")
            st.text(body)
            st.download_button("Download generated resume (PDF)", data=pdf_bytes, file_name=f"resume_{company_choice}.pdf", mime="application/pdf")

        st.header("5) Send application")
        recruiter_email = job_row.get('recruiter email', '') if 'recruiter email' in job_row.index else ''
        recruiter_name = job_row.get('recruiter name', '') if 'recruiter name' in job_row.index else ''
        st.write(f"Recruiter: {recruiter_name} | Email: {recruiter_email}")

        # If recruiter email missing, propose generated
        if not recruiter_email or pd.isna(recruiter_email):
            domain = extract_domain_from_company(job_row.get('company name', ''))
            generated_email = name_to_email(str(recruiter_name) or 'hr', domain)
            st.info(f"Recruiter email missing. Generated candidate email: {generated_email}")
            recruiter_email = st.text_input("Use this email (or edit)", value=generated_email)
        else:
            recruiter_email = st.text_input("Recruiter email (edit if needed)", value=str(recruiter_email))

        send_now = st.button("Send Application")
        if send_now:
            subj, body, pdf_bytes = generate_email_and_resume(job_row, resume_text, use_llm_flag=use_llm)

            # Build email
            msg = EmailMessage()
            msg['Subject'] = subj
            msg['From'] = smtp_user or 'no-reply@example.com'
            msg['To'] = recruiter_email
            msg.set_content(body)
            msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f"resume_{company_choice}.pdf")

            if not smtp_host or not smtp_user or not smtp_pass:
                st.error("SMTP details not provided in sidebar. Cannot send email.")
            else:
                try:
                    with smtplib.SMTP(smtp_host, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_pass)
                        server.send_message(msg)
                    st.success(f"Email sent to {recruiter_email}")
                except Exception as e:
                    st.error(f"Failed to send email: {e}")

else:
    st.info("Upload the job details Excel to proceed.")

st.markdown("---")
st.caption("This app is a starter. Replace the simple template generator with a production LLM integration and a reliable domain lookup for best results.")
