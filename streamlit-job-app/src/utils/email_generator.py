def generate_email(company_name, job_description, recruiter_name, user_name, user_email):
    subject = f"Application for {job_description} at {company_name}"
    body = f"""
    Dear {recruiter_name},

    I hope this message finds you well. My name is {user_name}, and I am writing to express my interest in the {job_description} position at {company_name}. 

    I believe my skills and experiences align well with the requirements of this role, and I am excited about the opportunity to contribute to your team.

    Please find my resume attached for your review. I look forward to the possibility of discussing this exciting opportunity with you.

    Thank you for your time and consideration.

    Best regards,
    {user_name}
    {user_email}
    """
    return subject, body