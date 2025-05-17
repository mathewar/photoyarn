document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const fileList = document.getElementById('fileList');
    const startButton = document.getElementById('startButton');
    const processingSpinner = document.getElementById('processingSpinner');
    const patienceMessage = document.getElementById('patienceMessage');
    const advancedToggle = document.getElementById('advancedToggle');
    const advancedFields = document.getElementById('advancedFields');
    const advancedIcon = document.getElementById('advancedIcon');

    // Initialize advanced section
    advancedFields.style.display = 'block';
    advancedIcon.style.transform = 'rotate(90deg)';

    // Handle advanced toggle
    advancedToggle.addEventListener('click', function() {
        const isVisible = advancedFields.style.display !== 'none';
        advancedFields.style.display = isVisible ? 'none' : 'block';
        advancedIcon.style.transform = isVisible ? 'rotate(0deg)' : 'rotate(90deg)';
    });

    // Handle file input click
    uploadButton.addEventListener('click', () => fileInput.click());

    // Handle file selection
    fileInput.addEventListener('change', handleFiles);

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropArea.classList.add('highlight');
    }

    function unhighlight(e) {
        dropArea.classList.remove('highlight');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles({ target: { files: files } });
    }

    function handleFiles(e) {
        const files = [...e.target.files];
        updateFileList(files);
    }

    function updateFileList(files) {
        if (files.length === 0) {
            fileList.style.display = 'none';
            startButton.disabled = true;
            return;
        }

        fileList.style.display = 'block';
        fileList.innerHTML = '<ul></ul>';
        const ul = fileList.querySelector('ul');

        files.forEach(file => {
            const li = document.createElement('li');
            const fileName = document.createElement('span');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            const fileSize = document.createElement('span');
            fileSize.className = 'file-size';
            fileSize.textContent = formatFileSize(file.size);
            
            li.appendChild(fileName);
            li.appendChild(fileSize);
            ul.appendChild(li);
        });

        startButton.disabled = false;
    }

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    startButton.addEventListener('click', async function() {
        const files = fileInput.files;
        if (files.length === 0) return;

        // Show processing state
        startButton.disabled = true;
        processingSpinner.style.display = 'block';
        patienceMessage.style.display = 'block';

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files[]', files[i]);
        }

        // Add advanced options
        const storyPrompt = document.getElementById('storyPrompt').value;
        const maxWords = document.getElementById('maxWords').value;
        const maxBeats = document.getElementById('maxBeats').value;
        const apiKey = document.getElementById('apiKey').value;

        if (storyPrompt) formData.append('story_prompt', storyPrompt);
        if (maxWords) formData.append('max_words', maxWords);
        if (maxBeats) formData.append('max_beats', maxBeats);
        if (apiKey) formData.append('api_key', apiKey);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                window.location.href = `/story/${result.story_id}`;
            } else {
                alert(result.error || 'An error occurred while processing your files.');
                processingSpinner.style.display = 'none';
                patienceMessage.style.display = 'none';
                startButton.disabled = false;
            }
        } catch (error) {
            console.error('Error:', error);
            alert('An error occurred while uploading your files.');
            processingSpinner.style.display = 'none';
            patienceMessage.style.display = 'none';
            startButton.disabled = false;
        }
    });

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