document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const dropArea = document.getElementById('dropArea');
    const startButton = document.getElementById('startButton');
    const fileList = document.getElementById('fileList');
    const processingSpinner = document.getElementById('processingSpinner');
    const patienceMessage = document.getElementById('patienceMessage');
    
    let isUploading = false;
    
    // Only set up drag-and-drop and upload logic if dropArea exists (upload page)
    if (dropArea) {
        // Drag and drop handlers
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
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
            handleFiles({ target: { files: files } });
        }
        
        const selectedFile = null;

        uploadButton.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', handleFiles, false);

        startButton.addEventListener('click', startProcessing);

        function handleFiles(e) {
            const files = [...e.target.files];
            updateFileList(files);
            startButton.disabled = files.length === 0;
        }
        
        function updateFileList(files) {
            fileList.innerHTML = '';
            const ul = document.createElement('ul');
            ul.style.listStyle = 'none';
            ul.style.padding = '0';
            ul.style.margin = '0';
            
            files.forEach(file => {
                const li = document.createElement('li');
                li.style.padding = '0.5rem';
                li.style.borderBottom = '1px solid #eee';
                li.textContent = `${file.name} (${formatFileSize(file.size)})`;
                ul.appendChild(li);
            });
            
            fileList.appendChild(ul);
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function startProcessing() {
            const files = fileInput.files;
            if (files.length === 0) return;

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files[]', files[i]);
            }

            // Add optional fields
            const storyPrompt = document.getElementById('storyPrompt').value;
            const maxWords = document.getElementById('maxWords').value;
            const maxBeats = document.getElementById('maxBeats').value;
            const apiKey = document.getElementById('apiKey').value;

            if (storyPrompt) formData.append('storyPrompt', storyPrompt);
            if (maxWords) formData.append('maxWords', maxWords);
            if (maxBeats) formData.append('maxBeats', maxBeats);
            if (apiKey) formData.append('apiKey', apiKey);

            // Show processing UI
            processingSpinner.style.display = 'block';
            patienceMessage.style.display = 'block';
            startButton.disabled = true;
            dropArea.style.display = 'none';
            fileList.style.display = 'none';

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                // Redirect to the story page
                window.location.href = `/story/${data.story_id}`;
            })
            .catch(error => {
                alert('Error: ' + error.message);
                processingSpinner.style.display = 'none';
                patienceMessage.style.display = 'none';
                startButton.disabled = false;
                dropArea.style.display = 'block';
                fileList.style.display = 'block';
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