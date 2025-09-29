import pandas as pd

def read_job_details(file_path):
    """Reads job details from an Excel file and returns a DataFrame."""
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        return None

def get_company_names(df):
    """Extracts unique company names from the job details DataFrame."""
    if df is not None:
        return df['company name'].unique().tolist()
    return []

def get_job_details_by_company(df, company_name):
    """Fetches job details for a specific company from the DataFrame."""
    if df is not None:
        return df[df['company name'] == company_name]
    return None

def get_recruiter_info(df, company_name):
    """Retrieves recruiter information for a specific company."""
    job_details = get_job_details_by_company(df, company_name)
    if job_details is not None and not job_details.empty:
        return job_details[['recruiter name', 'recruiter email']].iloc[0]
    return None

def get_job_details(company_name, excel_path):
    job_details_df = pd.read_excel(excel_path)
    return job_details_df[job_details_df['company_name'] == company_name].iloc[0]