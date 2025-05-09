import os
import logging
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
from werkzeug.exceptions import RequestEntityTooLarge

import spacy
import nltk
import PyPDF2
import docx
import fitz  # PyMuPDF for PDF processing

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB limit
app.config["UPLOAD_EXTENSIONS"] = [".pdf", ".docx"]

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nlp = spacy.load("en_core_web_sm")
nltk.download("punkt")
job_description_keywords = set()


def extract_keywords(text):
    doc = nlp(text)
    return {token.text for token in doc if token.is_alpha and not token.is_stop}


def extract_text_from_pdf(pdf_file):
    try:
        pdf_file.seek(0)
        try:
            reader = PyPDF2.PdfReader(pdf_file)
            text = " ".join([page.extract_text() or "" for page in reader.pages])
            if text.strip():
                return text
        except Exception:
            pdf_file.seek(0)
            with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
                return "".join(page.get_text() for page in doc)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""


def extract_text_from_docx(docx_file):
    try:
        docx_file.seek(0)
        doc = docx.Document(docx_file)
        return " ".join(para.text for para in doc.paragraphs)
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        return ""


def calculate_match_score(resume_keywords, job_keywords):
    if not job_keywords:
        return 0, []
    matched_keywords = resume_keywords & job_keywords
    missing_keywords = job_keywords - resume_keywords
    score = (len(matched_keywords) / len(job_keywords) * 100) if job_keywords else 0
    return round(score, 2), list(missing_keywords)


def process_resume(file, filename):
    try:
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file)
        elif filename.lower().endswith(".docx"):
            text = extract_text_from_docx(file)
        else:
            return {"filename": filename, "error": "Unsupported file format"}

        if not text:
            return {"filename": filename, "error": "Failed to extract text"}

        resume_keywords = extract_keywords(text)
        score, missing_requirements = calculate_match_score(
            resume_keywords, job_description_keywords
        )
        return {
            "filename": filename,
            "score": score,
            "missing_requirements": missing_requirements,
        }
    except Exception as e:
        logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
        return {"filename": filename, "error": f"Processing error: {str(e)}"}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload")
def upload_page():
    return render_template("upload.html")


@app.route("/job_description", methods=["GET", "POST"])
def job_description_page():
    if request.method == "POST":
        data = request.get_json()
        if not data or "job_description" not in data:
            return jsonify({"error": "No job description provided"}), 400
        global job_description_keywords
        job_description_keywords = extract_keywords(data["job_description"])
        return jsonify({"message": "Job description saved successfully"})
    return render_template("job_description.html")


@app.route("/api/job_description", methods=["POST"])
def set_job_description():
    global job_description_keywords
    data = request.json
    if "job_description" not in data:
        return jsonify({"error": "No job description provided"}), 400
    job_description_keywords = extract_keywords(data["job_description"])
    return jsonify({"message": "Job description set successfully"})


@app.route("/api/job_description", methods=["GET"])
def get_job_description():
    return jsonify({"job_description": list(job_description_keywords)})


@app.route("/api/job_description", methods=["DELETE"])
def clear_job_description():
    global job_description_keywords
    job_description_keywords = set()
    return jsonify({"message": "Job description cleared"})


@app.route("/get_uploaded_resumes", methods=["GET"])
def get_uploaded_resumes():
    try:
        files = [
            f
            for f in os.listdir(UPLOAD_FOLDER)
            if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))
        ]
        return jsonify({"uploaded_resumes": files})
    except Exception as e:
        logger.error(f"Error getting uploaded resumes: {str(e)}")
        return jsonify({"error": "Failed to retrieve uploaded resumes"}), 500


@app.route("/view_resume/<filename>", methods=["GET"])
def view_resume(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename)
    except Exception as e:
        logger.error(f"Error viewing resume: {str(e)}")
        return jsonify({"error": "Failed to view resume"}), 500


@app.route("/view_resumes", methods=["GET", "POST"])
def view_resumes():
    if request.method == "POST":
        try:
            data = request.get_json()
            if not data or "selected_resumes" not in data:
                return jsonify({"error": "No resumes selected"}), 400

            if not job_description_keywords:
                return jsonify(
                    {"error": "No job description set. Please set a job description first."}
                ), 400

            results = []
            for filename in data["selected_resumes"]:
                try:
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    if not os.path.exists(file_path):
                        results.append({"filename": filename, "error": "File not found"})
                        continue

                    if filename.lower().endswith(".pdf"):
                        with open(file_path, "rb") as f:
                            text = extract_text_from_pdf(f)
                    elif filename.lower().endswith(".docx"):
                        with open(file_path, "rb") as f:
                            text = extract_text_from_docx(f)
                    else:
                        results.append(
                            {"filename": filename, "error": "Unsupported file format"}
                        )
                        continue

                    if not text:
                        results.append(
                            {"filename": filename, "error": "Failed to extract text"}
                        )
                        continue

                    resume_keywords = extract_keywords(text)
                    score, missing_requirements = calculate_match_score(
                        resume_keywords, job_description_keywords
                    )
                    results.append(
                        {
                            "filename": filename,
                            "score": score,
                            "missing_requirements": missing_requirements,
                        }
                    )
                except Exception as e:
                    logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
                    results.append(
                        {"filename": filename, "error": f"Processing error: {str(e)}"}
                    )
                    continue

            return jsonify({"results": results}), 200
        except Exception as e:
            logger.error(f"Error in screening_result: {str(e)}", exc_info=True)
            return jsonify(
                {"error": "Internal server error. Please check the logs for more details."}
            ), 500
    else:
        try:
            logger.debug(f"Attempting to list files in UPLOAD_FOLDER: {UPLOAD_FOLDER}")
            files = os.listdir(UPLOAD_FOLDER)
            logger.debug(f"Found files: {files}")
            if not files:
                logger.warning("No files found in uploads directory")
            return render_template("view_resumes.html", resumes=files)
        except Exception as e:
            logger.error(f"Error fetching resumes: {str(e)}", exc_info=True)
            return jsonify({"error": "Failed to fetch resumes"}), 500


@app.route("/download_resume/<filename>", methods=["GET"])
def download_resume(filename):
    try:
        return send_file(os.path.join(UPLOAD_FOLDER, filename), as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading resume: {str(e)}")
        return jsonify({"error": "Failed to download resume"}), 500


@app.route("/get_resume_preview/<filename>", methods=["GET"])
def get_resume_preview(filename):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if filename.lower().endswith(".pdf"):
            with open(file_path, "rb") as f:
                content = extract_text_from_pdf(f)
        elif filename.lower().endswith(".docx"):
            with open(file_path, "rb") as f:
                content = extract_text_from_docx(f)
        else:
            return jsonify({"error": "Unsupported file format"}), 400
        return jsonify({"preview": content[:500] if content else "Unable to extract text"})
    except Exception as e:
        logger.error(f"Error getting resume preview: {str(e)}")
        return jsonify({"error": "Failed to get resume preview"}), 500


@app.route("/screening_result", methods=["POST"])
def screening_result():
    try:
        data = request.get_json()
        if not data or "selected_resumes" not in data:
            return jsonify({"error": "No resumes selected"}), 400

        if not job_description_keywords:
            return jsonify(
                {"error": "No job description set. Please set a job description first."}
            ), 400

        results = []
        for filename in data["selected_resumes"]:
            try:
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if not os.path.exists(file_path):
                    results.append({"filename": filename, "error": "File not found"})
                    continue

                if filename.lower().endswith(".pdf"):
                    with open(file_path, "rb") as f:
                        text = extract_text_from_pdf(f)
                elif filename.lower().endswith(".docx"):
                    with open(file_path, "rb") as f:
                        text = extract_text_from_docx(f)
                else:
                    results.append(
                        {"filename": filename, "error": "Unsupported file format"}
                    )
                    continue

                if not text:
                    results.append(
                        {"filename": filename, "error": "Failed to extract text"}
                    )
                    continue

                resume_keywords = extract_keywords(text)
                score, missing_requirements = calculate_match_score(
                    resume_keywords, job_description_keywords
                )
                results.append(
                    {
                        "filename": filename,
                        "score": score,
                        "missing_requirements": missing_requirements,
                    }
                )
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
                results.append(
                    {"filename": filename, "error": f"Processing error: {str(e)}"}
                )
                continue

        return jsonify({"results": results}), 200
    except Exception as e:
        logger.error(f"Error in screening_result: {str(e)}", exc_info=True)
        return jsonify(
            {"error": "Internal server error. Please check the logs for more details."}
        ), 500


@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        files = request.files.getlist("resume")
        if len(files) > 10:
            return jsonify({"error": "Maximum of 10 files allowed per upload"}), 400

        results = []
        for file in files:
            filename = file.filename.lower()
            if not any(filename.endswith(ext) for ext in app.config["UPLOAD_EXTENSIONS"]):
                results.append({"filename": filename, "error": "Unsupported file type"})
                continue

            if filename.endswith(".pdf"):
                text = extract_text_from_pdf(file)
            elif filename.endswith(".docx"):
                text = extract_text_from_docx(file)
            else:
                results.append({"filename": filename, "error": "Unsupported file format"})
                continue

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            save_path = os.path.join(UPLOAD_FOLDER, f"{timestamp}_{filename}")
            file.save(save_path)

            resume_keywords = extract_keywords(text)
            score, missing_requirements = calculate_match_score(
                resume_keywords, job_description_keywords
            )

            results.append(
                {
                    "filename": filename,
                    "save_path": save_path,
                    "resume_score": score,
                    "missing_requirements": missing_requirements,
                }
            )

        return jsonify(
            {"message": f"Uploaded {len(results)} files successfully!", "results": results}
        ), 200
    except Exception as e:
        logger.error(f"Error in upload_resume: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import os

    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
