# AI-Powered Resume Screener

This is a Flask web application that allows users to upload resumes (PDF or DOCX), set a job description, and screen resumes based on keyword matching with the job description.

## Features

- Upload multiple resumes (PDF, DOCX)
- Set and manage job description keywords
- View uploaded resumes and their screening results
- Download and preview resumes
- Keyword extraction using spaCy and NLTK
- Resume text extraction using PyPDF2, python-docx, and PyMuPDF

## Setup and Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd AI-Powered-Resume-Screener
```

2. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Download spaCy English model:

```bash
python -m spacy download en_core_web_sm
```

5. Run the application:

```bash
export FLASK_DEBUG=true  # On Windows: set FLASK_DEBUG=true
python app.py
```

6. Open your browser and navigate to `http://localhost:5000`

## Deployment

- The app is ready for deployment on platforms like Heroku.
- Use environment variable `FLASK_DEBUG` to control debug mode.
- Make sure to add `uploads/` to `.gitignore` to avoid uploading user files to the repository.

## License

MIT License
