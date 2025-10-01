import streamlit as st
import pandas as pd
import os
import re
import difflib
from datetime import datetime
from components.calendar_dropdown import calendar_dropdown
from utils.resume_editor import edit_resume
from utils.email_generator import generate_email
from utils.groq_scraper import scrape_recruiter_email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Path to job details Excel
EXCEL_PATH = r"F:\TKSR PRODUCTION\job1\job_details.xlsx"


# -------------------------------
# Email Sending Function
# -------------------------------
def send_email(to_email, subject, body, from_email, from_password, attachment_path=None):
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add plain text email body
    msg.attach(MIMEText(body, "plain"))

    # Attach resume if provided
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)

    # Gmail SMTP
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()

    try:
        server.login(from_email, from_password)
    except smtplib.SMTPAuthenticationError:
        raise Exception(
            "Authentication failed! Make sure you are using a Gmail App Password, "
            "not your regular Gmail password."
        )

    server.send_message(msg)
    server.quit()


# -------------------------------
# Recruiter Email Finder
# -------------------------------
def find_recruiter_email(job_details, hr_name="", company_name=""):
    """
    Priority:
    1. Direct Recruiter Email column in Excel
    2. Fuzzy match with Recruiter Name if available
    3. Fallback to scrape/patterns
    """
    try:
        # 1. Check recruiter_email or Recruiter Email column
        if "recruiter_email" in job_details and pd.notna(job_details["recruiter_email"]):
            return str(job_details["recruiter_email"]).strip()

        if "Recruiter Email" in job_details and pd.notna(job_details["Recruiter Email"]):
            return str(job_details["Recruiter Email"]).strip()

        # 2. Fuzzy match Recruiter Name
        if hr_name and "Recruiter Name" in job_details:
            names = [str(job_details["Recruiter Name"]).lower().strip()]
            closest = difflib.get_close_matches(hr_name.lower().strip(), names, n=1, cutoff=0.6)
            if closest:
                return str(job_details["Recruiter Email"]).strip()

        # 3. Last resort → regex from job description
        return scrape_recruiter_email(job_details.get("job_description", ""))

    except Exception as e:
        print(f"[RecruiterEmail] Error: {e}")
        return None


# -------------------------------
# Main App
# -------------------------------
def main():
    st.title("📩 Job Application Portal")

    # User Inputs
    selected_date = calendar_dropdown()
    user_resume = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
    user_name = st.text_input("Your Name")
    user_email = st.text_input("Your Gmail Address")
    from_password = st.text_input("Enter your Gmail App Password", type="password")

    # Load Job Details
    try:
        job_details_df = pd.read_excel(EXCEL_PATH)
        job_details_df["date"] = pd.to_datetime(job_details_df["date"]).dt.date
    except Exception as e:
        st.error(f"Failed to read job details Excel: {e}")
        return

    # Ensure date selected
    if hasattr(selected_date, "date"):
        selected_date = selected_date.date()

    # Filter jobs for selected date
    jobs_for_date = job_details_df[job_details_df["date"] == selected_date]

    # Debugging info
    st.write("Excel columns:", job_details_df.columns.tolist())

    # -------------------------------
    # Submit Application Button
    # -------------------------------
    if st.button("Submit Application"):
        if not selected_date:
            st.error("Please select a date before submitting.")
            return
        if user_resume is None:
            st.error("Please upload your resume before submitting.")
            return
        if not user_name or not user_email:
            st.error("Please enter your name and email.")
            return
        if not from_password:
            st.error("Please enter your Gmail App Password.")
            return
        if jobs_for_date.empty:
            st.warning("No companies available for the selected date. Please choose another date.")
            return

        # Save uploaded resume with timestamp to avoid overwrites
        os.makedirs("temp_resume", exist_ok=True)
        resume_save_path = os.path.join(
            "temp_resume", f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_resume.name}"
        )
        with open(resume_save_path, "wb") as f:
            f.write(user_resume.getbuffer())

        success_count = 0
        fail_count = 0
        debug_results = []  # to show emails per company in Streamlit

        # Process jobs
        for _, job_details in jobs_for_date.iterrows():
            job_description = job_details.get("job_description", "")
            company_name = job_details.get("Company Name", "UnknownCompany")

            # Create job-specific edited resume
            output_path = f"edited_resume_{company_name}_{datetime.now().strftime('%H%M%S')}.pdf"
            edited_resume_result = edit_resume(resume_save_path, job_description, output_path)

            # Handle tuple or direct return
            if isinstance(edited_resume_result, tuple):
                edited_resume_path = edited_resume_result[0]
            else:
                edited_resume_path = edited_resume_result

            # Recruiter info
            recruiter_name = job_details.get("recruiter_name", "")
            recruiter_email = find_recruiter_email(job_details, recruiter_name, company_name)

            # Fix common typos
            if recruiter_email:
                recruiter_email = recruiter_email.replace("@gamil.com", "@gmail.com")

            debug_results.append({
                "Company": company_name,
                "Recruiter": recruiter_name,
                "Resolved Email": recruiter_email or "❌ Not Found"
            })

            # Skip if no email found
            if not recruiter_email or recruiter_email == "None":
                st.error(f"No recruiter email found for {company_name}, skipping...")
                fail_count += 1
                continue

            # Generate email body
            email_content = generate_email(
                job_details, edited_resume_path, recruiter_name, user_name, user_email
            )
            if isinstance(email_content, tuple):
                email_content = email_content[0]

            # Send email
            try:
                send_email(
                    recruiter_email,
                    "Job Application",
                    email_content,
                    user_email,
                    from_password,
                    edited_resume_path,
                )
                success_count += 1
            except Exception as e:
                st.error(f"❌ Failed to send email to {recruiter_email}: {e}")
                fail_count += 1

        # Show debug table
        st.subheader("📊 Recruiter Email Resolution")
        st.dataframe(pd.DataFrame(debug_results))

        # Final summary
        if success_count > 0:
            st.success(f"✅ Applications sent to {success_count} companies for {selected_date}!")
        if fail_count > 0:
            st.warning(f"⚠️ Failed to send applications to {fail_count} companies.")


if __name__ == "__main__":
    main()
