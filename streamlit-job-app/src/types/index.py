from typing import List, Dict, Any

# Define a type for job details
JobDetail = Dict[str, Any]

# Define a type for the resume information
ResumeInfo = Dict[str, str]

# Define a type for the email content
EmailContent = Dict[str, str]

# Define a type for the company information
CompanyInfo = Dict[str, str]

# Define a type for the application state
ApplicationState = Dict[str, Any]

# Exporting types for use in other modules
__all__ = [
    "JobDetail",
    "ResumeInfo",
    "EmailContent",
    "CompanyInfo",
    "ApplicationState"
]