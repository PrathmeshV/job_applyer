from streamlit import button, session_state
from utils.email_generator import generate_email
from utils.resume_editor import edit_resume
from utils.excel_handler import get_job_details
from utils.groq_scraper import scrape_recruiter_email

def submit_button(user_resume, selected_company, selected_date):
    if button("Submit Application"):
        job_details = get_job_details(selected_company, 'path/to/job_details.xlsx')
        
        if job_details:
            recruiter_email = job_details.get('recruiter_email')
            if not recruiter_email:
                recruiter_email = scrape_recruiter_email(job_details['company_name'])
            
            email_content = generate_email(job_details)
            edited_resume_path = edit_resume(user_resume)
            
            # Code to send the email would go here
            # send_email(recruiter_email, email_content, edited_resume_path)
            
            session_state.message = "Application submitted successfully!"
        else:
            session_state.message = "Job details not found."