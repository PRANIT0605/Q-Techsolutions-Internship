// Base URL of your Flask backend
const BASE_URL = "http://127.0.0.1:5000";

// Initialize when page loads
document.addEventListener("DOMContentLoaded", function() {
    // Only initialize upload form if on upload page
    if (document.getElementById('uploadForm')) {
        setupUploadForm();
    }
    // Only fetch resumes if on a page that needs them
    if (document.getElementById('resumesContainer')) {
        fetchResumes();
    }
});

// Setup upload form and event listeners
function setupUploadForm() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');
    const progressBar = document.getElementById('progressBar');
    
    if (!dropZone || !fileInput || !uploadForm || !progressBar) {
        console.log('Upload form elements not found');
        return;
    }
    
    const progress = progressBar.querySelector('.progress-bar');
    const fileList = document.getElementById('fileList');

    // Handle file selection
    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFiles);

    // Handle drag and drop
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('drop-zone--over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('drop-zone--over'), false);
    });

    dropZone.addEventListener('drop', handleDrop, false);

    // Handle form submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const files = fileInput.files;
        if (files.length === 0) {
            alert('Please select at least one file to upload');
            return;
        }
        await uploadFiles(files);
    });
}

// Prevent default drag and drop behavior
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Handle dropped files
function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

// Handle selected files
function handleFiles(files) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    
    if (files.length === 0) {
        const emptyItem = document.createElement('li');
        emptyItem.className = 'list-group-item text-muted';
        emptyItem.textContent = 'No files selected';
        fileList.appendChild(emptyItem);
        return;
    }
    
    [...files].forEach(file => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        listItem.innerHTML = `
            <span>${file.name} (${(file.size / 1024).toFixed(2)} KB)</span>
            <span class="badge bg-primary rounded-pill">Pending</span>
        `;
        fileList.appendChild(listItem);
    });
}

// Upload files to server
async function uploadFiles(files) {
    const progressBar = document.getElementById('progressBar');
    const progress = progressBar.querySelector('.progress-bar');
    const uploadBtn = document.getElementById('uploadBtn');
    
    try {
        // Disable upload button during upload
        uploadBtn.disabled = true;
        uploadBtn.querySelector('.spinner-border').classList.remove('d-none');
        progressBar.classList.remove('d-none');
        
        const formData = new FormData();
        [...files].forEach(file => {
            formData.append('resume', file);
        });

        const response = await fetch(`${BASE_URL}/upload_resume`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        const result = await response.json();
        if (result.error) {
            throw new Error(result.error);
        }

        // Handle multiple file upload results
        if (result.results && result.results.length > 0) {
            const successCount = result.results.filter(r => !r.error).length;
            const errorCount = result.results.length - successCount;
            
            if (successCount > 0) {
                alert(`Successfully uploaded ${successCount} file(s)`);
            }
            if (errorCount > 0) {
                const errorFiles = result.results
                    .filter(r => r.error)
                    .map(r => `${r.filename}: ${r.error}`)
                    .join('\n');
                alert(`Failed to upload ${errorCount} file(s):\n${errorFiles}`);
            }
        } else {
            alert('No files were uploaded');
        }

        fileInput.value = ''; // Clear file input
        document.getElementById('fileList').innerHTML = ''; // Clear file list
        fetchResumes(); // Refresh the list of uploaded resumes

    } catch (error) {
        console.error('Upload error:', error);
        alert(`Upload failed: ${error.message}`);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.querySelector('.spinner-border').classList.add('d-none');
        progressBar.classList.add('d-none');
        progress.style.width = '0%';
    }
}

// Fetch and display uploaded resumes with preview
async function fetchResumes() {
    try {
        const response = await fetch(`${BASE_URL}/get_uploaded_resumes`);
        const data = await response.json();

        const resumesContainer = document.getElementById("resumesContainer");
        if (!resumesContainer) return;

        resumesContainer.innerHTML = "";

        if (data.uploaded_resumes && data.uploaded_resumes.length > 0) {
            data.uploaded_resumes.forEach(resume => {
                const card = document.createElement("div");
                card.className = "col-md-6 col-lg-4 mb-4";
                card.innerHTML = `
                    <div class="resume-card">
                        <div class="form-check">
                            <input class="form-check-input resume-checkbox" type="checkbox" value="${resume}" id="checkbox-${resume}">
                            <label class="form-check-label" for="checkbox-${resume}">
                                <h5 class="card-title">${resume}</h5>
                            </label>
                        </div>
                        <div class="btn-group mt-2">
                            <button onclick="viewResume('${resume}')" class="btn btn-sm btn-primary">View</button>
                            <button onclick="downloadResume('${resume}')" class="btn btn-sm btn-secondary">Download</button>
                        </div>
                        <div id="preview-${resume}" class="resume-preview mt-2"></div>
                    </div>
                `;
                resumesContainer.appendChild(card);
                
                // Load preview content
                loadPreview(resume);
            });
        } else {
            resumesContainer.innerHTML = `
                <div class="col-12 text-center text-muted">
                    No resumes uploaded yet.
                </div>
            `;
        }
    } catch (error) {
        console.error("Error fetching resumes:", error);
        alert("Failed to load resumes. Please try again.");
    }
}

// View resume in new tab
async function viewResume(filename) {
    try {
        const response = await fetch(`${BASE_URL}/view_resume/${encodeURIComponent(filename)}`);
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            window.open(url, '_blank');
        } else {
            throw new Error('Failed to view file');
        }
    } catch (error) {
        console.error("Error viewing resume:", error);
        alert("Failed to view resume. Please try again.");
    }
}

// Download resume
function downloadResume(filename) {
    window.location.href = `${BASE_URL}/download_resume/${encodeURIComponent(filename)}`;
}

// Load preview content
async function loadPreview(filename) {
    try {
        const response = await fetch(`${BASE_URL}/get_resume_preview/${encodeURIComponent(filename)}`);
        const data = await response.json();
        
        const previewDiv = document.getElementById(`preview-${filename}`);
        if (previewDiv && data.preview) {
            previewDiv.innerHTML = data.preview;
        }
    } catch (error) {
        console.error("Error loading preview:", error);
    }
}
