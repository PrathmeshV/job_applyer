import streamlit as st
import pandas as pd
import os
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
            recruiter_email = job_details.get("recruiter_email")
            recruiter_name = job_details.get("recruiter_name", "")
            if not recruiter_email:
                recruiter_email = scrape_recruiter_email(company_name)

            # Skip if no email found
            if not recruiter_email or recruiter_email == "None":
                st.error(f"No recruiter email found for {company_name}, skipping...")
                fail_count += 1
                continue
            # Generate email body
            email_content = generate_email(
                job_details, edited_resume_path, recruiter_name, user_name, user_email
            )
            # fix tuple return
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

        # Final summary
        if success_count > 0:
            st.success(f"✅ Applications sent to {success_count} companies for {selected_date}!")
        if fail_count > 0:
            st.warning(f"⚠️ Failed to send applications to {fail_count} companies.")


if __name__ == "__main__":
    main()
