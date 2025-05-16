document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const dropArea = document.getElementById('dropArea');
    
    let isUploading = false;
    
    // Only set up drag-and-drop and upload logic if dropArea exists (upload page)
    if (dropArea) {
        // Drag and drop handlers
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            dropArea.classList.add('highlight');
        }
        
        function unhighlight(e) {
            dropArea.classList.remove('highlight');
        }
        
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }
        
        const startButton = document.getElementById('startButton');
        let selectedFile = null;

        uploadButton.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            // Accept multiple files
            let validFiles = [];
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                const ext = file.name.toLowerCase().split('.').pop();
                if ((ext === 'zip' && file.name.toLowerCase().endsWith('.zip')) ||
                    (ext === 'jpg' && file.name.toLowerCase().endsWith('.jpg')) ||
                    (ext === 'jpeg' && file.name.toLowerCase().endsWith('.jpeg'))) {
                    validFiles.push(file);
                }
            }
            if (validFiles.length > 0) {
                selectedFile = validFiles;
                startButton.disabled = false;
            } else {
                selectedFile = null;
                startButton.disabled = true;
            }
        });

        startButton.addEventListener('click', function() {
            if (selectedFile && selectedFile.length > 0) {
                uploadFile(selectedFile);
            }
        });

        function handleFiles(files) {
            let validFiles = [];
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const ext = file.name.toLowerCase().split('.').pop();
                if ((ext === 'zip' && file.name.toLowerCase().endsWith('.zip')) ||
                    (ext === 'jpg' && file.name.toLowerCase().endsWith('.jpg')) ||
                    (ext === 'jpeg' && file.name.toLowerCase().endsWith('.jpeg'))) {
                    validFiles.push(file);
                }
            }
            if (validFiles.length > 0) {
                selectedFile = validFiles;
                startButton.disabled = false;
            } else {
                selectedFile = null;
                startButton.disabled = true;
            }
        }
        
        function uploadFile(files) {
            const formData = new FormData();
            // Add all valid files
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }
            // Add story prompt if present
            const promptBox = document.getElementById('storyPrompt');
            if (promptBox && promptBox.value.trim()) {
                formData.append('story_prompt', promptBox.value.trim());
            }
            // Add max words if present
            const maxWordsBox = document.getElementById('maxWords');
            if (maxWordsBox && maxWordsBox.value) {
                formData.append('max_words', maxWordsBox.value);
            }
            // Add max beats if present
            const maxBeatsBox = document.getElementById('maxBeats');
            if (maxBeatsBox && maxBeatsBox.value) {
                formData.append('max_beats', maxBeatsBox.value);
            }
            // Add API key if present
            const apiKeyBox = document.getElementById('apiKey');
            if (apiKeyBox && apiKeyBox.value.trim()) {
                formData.append('api_key', apiKeyBox.value.trim());
            }
            
            isUploading = true;
            // Show spinner and hide drop area
            const spinner = document.getElementById('processingSpinner');
            if (spinner) spinner.style.display = 'block';
            dropArea.style.display = 'none';
            
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                isUploading = false;
                // Hide spinner (will redirect soon)
                if (spinner) spinner.style.display = 'none';
                if (data.error) {
                    // Show drop area again if error
                    dropArea.style.display = '';
                    throw new Error(data.error);
                }
                
                if (data.success) {
                    // Store the story data in sessionStorage
                    sessionStorage.setItem('storyData', JSON.stringify(data));
                    // Redirect to slideshow
                    window.location.href = '/slideshow';
                }
            })
            .catch(error => {
                isUploading = false;
                // Hide spinner and show drop area on error
                if (spinner) spinner.style.display = 'none';
                dropArea.style.display = '';
            });
        }
    }

    // Slideshow logic for /slideshow page
    if (window.location.pathname === '/slideshow') {
        const slideImage = document.getElementById('slide-image');
        const storySegment = document.getElementById('story-segment');
        const prevButton = document.getElementById('prev-button');
        const nextButton = document.getElementById('next-button');
        const slideCounter = document.getElementById('slide-counter');
        const restartButton = document.getElementById('restart-button');

        let slides = [];
        let currentIndex = 0;

        // Load slides from sessionStorage
        const storyData = sessionStorage.getItem('storyData');
        if (storyData) {
            const data = JSON.parse(storyData);
            console.log('Loaded storyData:', data);
            slides = data.slides || [];
            console.log('Slides array:', slides);
            if (slides.length > 0) {
                console.log('First slide:', slides[0]);
            }
        }

        function showSlide(index) {
            if (!slides.length) {
                slideImage.src = '';
                storySegment.textContent = '';
                slideCounter.textContent = '0 of 0';
                return;
            }
            const slide = slides[index];
            slideImage.src = slide.image_url;
            storySegment.textContent = slide.story_segment;
            slideCounter.textContent = `${index + 1} of ${slides.length}`;
            prevButton.disabled = index === 0;
            nextButton.disabled = index === slides.length - 1;
        }

        prevButton.addEventListener('click', function() {
            if (currentIndex > 0) {
                currentIndex--;
                showSlide(currentIndex);
            }
        });
        nextButton.addEventListener('click', function() {
            if (currentIndex < slides.length - 1) {
                currentIndex++;
                showSlide(currentIndex);
            }
        });
        restartButton.addEventListener('click', function() {
            sessionStorage.removeItem('storyData');
            window.location.href = '/';
        });

        // Show the first slide
        showSlide(currentIndex);
    }
}); 