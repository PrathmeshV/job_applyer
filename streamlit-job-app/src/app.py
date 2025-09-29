import streamlit as st
import pandas as pd
import os
from components.calendar_dropdown import calendar_dropdown
from utils.resume_editor import edit_resume
from utils.email_generator import generate_email
from utils.groq_scraper import scrape_recruiter_email

EXCEL_PATH = r"F:\TKSR PRODUCTION\job1\job_details.xlsx"

def main():
    st.title("Job Application Portal")

    # Calendar dropdown for date selection
    selected_date = calendar_dropdown()

    # File uploader for user's resume
    user_resume = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
    user_name = st.text_input("Your Name")
    user_email = st.text_input("Your Email")

    # Read job details and ensure date column is datetime
    job_details_df = pd.read_excel(EXCEL_PATH)
    job_details_df['date'] = pd.to_datetime(job_details_df['date']).dt.date

    # Convert selected_date to date object if it's datetime
    if hasattr(selected_date, 'date'):
        selected_date = selected_date.date()

    # Filter jobs for the selected date
    jobs_for_date = job_details_df[job_details_df['date'] == selected_date]

    # Display the columns of the Excel file
    st.write("Excel columns:", job_details_df.columns.tolist())

    if st.button("Submit Application"):
        if user_resume is None:
            st.error("Please upload your resume before submitting.")
            return

        if not user_name or not user_email:
            st.error("Please enter your name and email.")
            return

        if jobs_for_date.empty:
            st.warning("No companies available for the selected date. Please choose another date.")
            return

        # Save uploaded resume to disk
        resume_save_path = os.path.join("temp_resume", user_resume.name)
        os.makedirs("temp_resume", exist_ok=True)
        with open(resume_save_path, "wb") as f:
            f.write(user_resume.getbuffer())

        for idx, job_details in jobs_for_date.iterrows():
            job_description = job_details.get('job_description', '')
            output_path = f"edited_resume_{job_details['Company Name']}.pdf"  # or .docx based on your resume type

            # Pass the saved file path
            edited_resume = edit_resume(resume_save_path, job_description, output_path)

            recruiter_email = job_details.get('recruiter_email')
            recruiter_name = job_details.get('recruiter_name', '')
            if not recruiter_email:
                recruiter_email = scrape_recruiter_email(job_details['Company Name'])

            email_content = generate_email(
                job_details,
                edited_resume,
                recruiter_name,
                user_name,
                user_email
            )
            # send_email(recruiter_email, email_content)

        st.success("Applications submitted to all companies for the selected date!")

if __name__ == "__main__":
    main()