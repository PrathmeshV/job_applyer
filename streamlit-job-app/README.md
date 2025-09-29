# Streamlit Job Application

This project is a Streamlit application designed to facilitate job applications by allowing users to select a date, choose a company, and submit their resumes. The application integrates various components to streamline the process of applying for jobs and generating application emails.

## Project Structure

```
streamlit-job-app
├── src
│   ├── app.py                     # Main entry point of the Streamlit application
│   ├── components
│   │   ├── calendar_dropdown.py    # Calendar dropdown for date selection
│   │   ├── company_dropdown.py     # Company name dropdown for job selection
│   │   └── submit_button.py        # Submit button to trigger application process
│   ├── utils
│   │   ├── excel_handler.py        # Functions to handle Excel data
│   │   ├── resume_editor.py        # Functions to edit and format resumes
│   │   ├── email_generator.py      # Functions to generate application emails
│   │   └── groq_scraper.py         # Functions to scrape recruiter emails using Groq API
│   └── types
│       └── index.py                # Type definitions for the application
├── requirements.txt                # List of project dependencies
└── README.md                       # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd streamlit-job-app
   ```

2. **Install the required dependencies:**
   ```
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```
   streamlit run src/app.py
   ```

## Usage Guidelines

- Upon launching the application, users will be presented with a calendar dropdown to select the date for their job application.
- Users can select a company from the dropdown, which fetches data from the job details Excel sheet.
- After selecting the necessary details, users can upload their resumes in PDF or Word format.
- Pressing the submit button will generate an email for the job application, utilizing the provided Excel data.
- If the recruiter's email is not available, the application will use the Groq API to find the email through web scraping.
- The application will then send the email to the organization's recruiter.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.