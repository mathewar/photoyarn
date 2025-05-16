# Project Requirements: Photo Yarn

## 1. Introduction
The Story Weaver application is a web-based tool that automates the creation of a narrative slideshow from a collection of images. Users will upload a `.zip` file containing images. The application will leverage the Google Gemini API to analyze each image, summarize its content, and then generate a coherent story that maps each 'beat' of the narrative to a specific image. The final output will be an interactive slideshow displaying each image with its corresponding story segment.

## 2. Core Features

* **File Upload:**
    * Support for large zip files up to 500MB
    * Drag-and-drop interface
    * Progress tracking during upload
    * Chunked file upload for better performance
* **Image Processing:**
    * Extract images from the uploaded `.zip` file
    * Automatic image resizing to 400px width while maintaining aspect ratio
    * RGB conversion and JPEG standardization for API compatibility
    * For each image:
        * Generate a concise summary using the Google Gemini Vision API
        * Store the summary in association with the image
* **Story Generation:**
    * Using the collected image summaries, generate a complete, coherent story using the Google Gemini API
    * Ensure the generated story has distinct 'beats' or segments, with each segment mapping directly to one of the input images
* **Slideshow Presentation:**
    * Display a dynamic slideshow where each slide features an image and its corresponding story segment
    * Provide navigation controls (Next/Previous)
* **User Feedback & Progress:**
    * Comprehensive logging system for tracking processing status
    * Clear visual feedback during file upload and processing
    * Detailed error messages for API failures and processing issues
    * Progress tracking for each image being processed

## 3. Technical Stack

* **Backend:**
    * **Language:** Python 3.x
    * **Framework:** Flask 3.0.2
    * **Libraries:**
        * `Flask`: Web framework
        * `python-dotenv`: For managing environment variables
        * `google-generativeai`: Official Google Gemini API client library (v0.3.2)
        * `Pillow`: For image processing and manipulation (v10.2.0)
        * `Werkzeug`: For WSGI utilities (v3.0.1)
* **Frontend:**
    * **Languages:** HTML, CSS, JavaScript
    * **Features:**
        * Drag-and-drop file upload
        * Progress bar for upload status
        * Responsive design
        * Interactive slideshow navigation

## 4. Implementation Details

### Image Processing Pipeline
1. **Upload Handling:**
    * Accept zip files up to 500MB
    * Save files in 1MB chunks for efficient memory usage
    * Validate file type and size before processing

2. **Image Processing:**
    * Extract images from zip file
    * Resize images to 400px width while maintaining aspect ratio
    * Convert to RGB color space
    * Standardize to JPEG format
    * Process through Gemini Vision API

3. **Story Generation:**
    * Collect all image summaries
    * Generate coherent narrative using Gemini API
    * Map story segments to corresponding images

### Error Handling
* Comprehensive logging system for debugging
* Detailed error messages for:
    * File upload issues
    * Image processing failures
    * API errors and rate limits
    * Content filtering blocks
* Automatic cleanup of temporary files

### Security Considerations
* Secure file handling
* Input validation
* Temporary file cleanup
* API key management

## 5. Dependencies
```
Flask==3.0.2
python-dotenv==1.0.1
google-generativeai==0.3.2
Pillow==10.2.0
Werkzeug==3.0.1
```

## 6. Future Enhancements
* User accounts and story saving
* Custom story generation parameters
* Advanced image processing options
* Download options for generated stories
* Batch processing capabilities
* API rate limit handling
* Image order customization

## 7. User Interface (UI) / User Experience (UX) Requirements

* **Landing Page:**
    * Clear title: "Story Weaver"
    * Brief description of the application's purpose.
    * Prominent file upload area (drag-and-drop support preferred, or a standard file input).
* **File Upload State:**
    * Visual indicator of file selection.
    * Progress bar or spinner during upload.
* **Processing State:**
    * "Processing..." message with an animated spinner/progress indicator.
    * Consider showing sub-steps: "Summarizing images...", "Generating story...".
* **Slideshow View:**
    * Clean, minimalistic design to focus on image and text.
    * **Image Display:** Large, centrally aligned image.
    * **Story Text Display:** A clear, readable text box or overlay for the story segment corresponding to the current image.
    * **Navigation:** Clearly visible "Previous" and "Next" buttons.
    * (Optional) Current slide number indicator (e.g., "1 of 10").
    * (Optional) A "Restart" or "New Story" button to clear the current state.
* **Error Display:**
    * Friendly and informative error messages (e.g., "Invalid file type," "API rate limit exceeded," "Error processing images").
    * Guide the user on how to resolve common issues.

## 8. Backend Requirements

* **API Endpoint:**
    * `/upload` (POST): Accepts the `.zip` file.
        * **Input:** `multipart/form-data` with the zip file.
        * **Processing:**
            1.  Validate file type (must be `.zip`).
            2.  Save the `.zip` file to a temporary location.
            3.  Extract contents to another temporary directory.
            4.  Iterate through extracted image files (e.g., `.jpg`, `.png`).
            5.  For each image:
                * Read image data.
                * Base64 encode the image.
                * Call Gemini API (e.g., `gemini-pro-vision`) with a prompt like: "Describe this image: Who is present? Where is the scene set? What is happening?"
                * Store the filename and the received summary.
            6.  **Story Generation:**
                * Construct a comprehensive prompt for Gemini using all image summaries in their processed order. Example prompt: "Here are a series of image descriptions in sequence. Please write a coherent story, with a clear narrative beat corresponding to each image. Each beat should be a distinct paragraph or section. [List of summaries]"
                * Call Gemini API (e.g., `gemini-pro` for text generation) with the story prompt.
            7.  **Mapping:** Attempt to map the generated story text segments to the original images. This might require parsing the story text based on structure (e.g., by paragraphs if instructed in the prompt, or by adding specific markers in the prompt for Gemini to use).
            8.  **Response:** Return a JSON object containing a list of slideshow items, where each item is `{ "image_url": "/path/to/temp/image.jpg", "story_segment": "..." }`.
            9.  **Cleanup:** Implement a mechanism to delete temporary files/directories after processing or after a certain time.
* **API Key Management:**
    * Load Gemini API key securely from environment variables (e.g., `.env` file).
    * Never expose API keys to the frontend.
* **Temporary File Storage:**
    * Securely manage temporary storage for uploaded zip files and extracted images.
    * Ensure proper permissions and regular cleanup.
* **Error Handling:**
    * Catch and log errors from file operations, API calls, and processing.
    * Return appropriate HTTP status codes and error messages to the frontend.
    * Implement rate limiting and retry mechanisms for Gemini API calls if necessary.

## 9. Frontend Requirements

* **File Upload Component:**
    * An HTML `<form>` with an `<input type="file" accept=".zip">`.
    * JavaScript to handle the file selection and initiation of the upload.
    * Display filename and a "Upload" button.
* **AJAX Communication:**
    * Use `Workspace` API or `XMLHttpRequest` to send the `.zip` file to the backend's `/upload` endpoint.
    * Handle successful responses (parse JSON) and error responses.
* **Loading/Progress Indicators:**
    * Update the UI to show processing status (e.g., disable buttons, show spinner, update text).
* **Slideshow Component:**
    * Container for the current image and story text.
    * JavaScript to manage the current slide index.
    * Event listeners for "Next" and "Previous" buttons to update the displayed content.
    * Dynamically load images (or use pre-signed URLs if images are stored in cloud storage).
    * (Optional) Implement an `setInterval` for auto-play.
* **Responsive Design:** Ensure the application is usable and aesthetically pleasing on various screen sizes (desktop, tablet, mobile).

## 10. API Integration Requirements (Google Gemini)

* **Authentication:** Use the `google-generativeai` client library for API key authentication.
* **Image Summarization Prompt:**
    * Prompt should be clear and concise to elicit "who, what, where" details.
    * Example: `"Analyze this image. Describe the primary subjects, the setting, and any actions taking place. Focus on objective details relevant for storytelling."`
* **Story Generation Prompt:**
    * Prompt must instruct Gemini to generate a coherent narrative.
    * Explicitly ask for distinct sections/paragraphs for each image's "beat."
    * Example: `"Given the following sequence of image summaries, please craft a compelling and continuous story. Each major event or 'beat' in the story should correspond to one of the images. Structure your response with a new paragraph for each image's story segment. \n\n[List of image summaries, ordered and perhaps labeled (e.g., 'Image 1: ...')]"`
* **Image Data Format:** Images sent to Gemini Pro Vision must be correctly formatted (e.g., `{"mime_type": "image/jpeg", "data": base64_encoded_string}`).
* **Error Handling:** Implement specific handling for Gemini API errors:
    * `429 Too Many Requests`: Implement exponential backoff and retry.
    * `400 Bad Request`: Check prompt content or image data.
    * `500 Internal Server Error`: Retry or inform user of a temporary issue.
    * Content filtering responses (if applicable): Inform the user about the filtering.

## 11. Data Structures

* **Backend `image_summaries` List (Python):**
    ```python
    [
        {"filename": "image1.jpg", "base64_data": "...", "summary": "Summary for image1"},
        {"filename": "image2.png", "base64_data": "...", "summary": "Summary for image2"},
        # ...
    ]
    ```
    *(Note: `base64_data` might be removed after summarization if memory is a concern for story generation, relying only on summaries)*
* **Frontend `slideshow_data` List (JavaScript):**
    ```javascript
    [
        {
            "image_url": "/static/temp_images/image1.jpg", // URL to access the image from the frontend
            "story_segment": "The first part of the story corresponding to image1."
        },
        {
            "image_url": "/static/temp_images/image2.png",
            "story_segment": "The second part of the story corresponding to image2."
        },
        // ...
    ]
    ```

## 12. Error Handling & Validation

* **Input Validation:**
    * Reject non-zip file uploads.
    * Set maximum file size for the zip upload.
    * Validate contents of the zip file to ensure they are indeed images.
* **API Errors:** Gracefully handle API errors (network issues, rate limits, content filtering, invalid API key).
* **File System Errors:** Handle issues like disk full, permission errors during file extraction/saving.
* **User Feedback:** Provide clear, user-friendly error messages on the frontend.

## 13. Security Considerations

* **API Key Security:** Store API keys as environment variables, never hardcode them or expose them in client-side code.
* **File Upload Security:**
    * Sanitize filenames upon extraction to prevent path traversal attacks.
    * Limit file types and sizes within the zip archive to prevent malicious uploads.
    * Store extracted files in a secure, isolated temporary directory.
* **Temporary File Management:** Ensure temporary directories and files are securely cleaned up to prevent unauthorized access or disk exhaustion.
* **Input Sanitization:** Sanitize any user-provided input (if applicable) to prevent injection attacks.

## 14. Deployment Considerations

* **Containerization:** Use Docker to containerize the Flask application for easy deployment to various cloud platforms.
* **Cloud Platform:** Consider deployment on platforms like Google Cloud Run, Google App Engine, Heroku, or AWS Elastic Beanstalk for scalable web hosting.
* **Environment Variables:** Ensure all configuration (API keys, temporary file paths) can be managed via environment variables for different deployment environments.

## 15. Future Enhancements (Optional)

* **Story Customization:** Allow users to specify the tone (e.g., humorous, dramatic, mysterious), genre, or length of the story.
* **User Accounts:** Allow users to save their generated stories.
* **Download Options:** Enable downloading the slideshow (e.g., as a PDF with images and text, or a video file).
* **Image Order Customization:** Allow users to reorder images after upload before story generation.
* **Advanced Parsing:** Use more sophisticated text parsing techniques (e.g., NLP libraries) to ensure more robust mapping of story segments to images.
* **Progress Bar during Gemini Calls:** Update frontend progress based on the number of images processed by Gemini.

---