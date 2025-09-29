def edit_resume(user_resume_path, job_description, output_path):
    from PyPDF2 import PdfReader, PdfWriter
    from docx import Document
    import os

    # Check the file extension of the user's resume
    file_extension = os.path.splitext(user_resume_path)[1].lower()

    if file_extension == '.pdf':
        # Read the PDF resume
        reader = PdfReader(user_resume_path)
        writer = PdfWriter()

        # Extract text from each page and modify as needed
        for page in reader.pages:
            text = page.extract_text()
            # Here you can modify the text based on the job description
            modified_text = f"{text}\n\nJob Description:\n{job_description}"
            writer.add_page(page)

        # Save the modified PDF
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

    elif file_extension == '.docx':
        # Read the Word resume
        doc = Document(user_resume_path)

        # Modify the document as needed
        doc.add_paragraph(f"\nJob Description:\n{job_description}")

        # Save the modified Word document
        doc.save(output_path)

    else:
        raise ValueError("Unsupported file format. Please provide a PDF or Word document.")

    return output_path