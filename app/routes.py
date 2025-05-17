import os
import zipfile
import base64
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
import google.generativeai as genai
from PIL import Image
import io
import json
import logging
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from shutil import copyfile
import re
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import uuid
from datetime import datetime
import magic
import threading
import time
from queue import Queue
import heapq

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(filename='/var/log/photoyarn/app.log', level=logging.INFO)
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

# Configure Google Gemini API
DEFAULT_GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=DEFAULT_GEMINI_API_KEY)

# Configure safety settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# Set up Redis for rate limiting
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    default_limits=[]
)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def process_image(image_path, api_key=None):
    """Process a single image using Gemini Vision API"""
    try:
        # Skip macOS metadata files
        if os.path.basename(image_path).startswith('._'):
            logger.info(f"Skipping macOS metadata file: {os.path.basename(image_path)}")
            return None
        logger.info(f"Processing image: {os.path.basename(image_path)}")
        with Image.open(image_path) as img:
            logger.info(f"Image loaded successfully. Original size: {img.size}")
            # Use thumbnail for memory-efficient resizing
            max_width = 400
            width, height = img.size
            if width > max_width:
                img.thumbnail((max_width, max_width * 10), Image.LANCZOS)  # maintain aspect ratio
                logger.info(f"Image resized to: {img.size}")
            img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=70)
            img_byte_arr = img_byte_arr.getvalue()
            logger.info("Image converted to JPEG format")
            # Use the provided API key if present, else default
            if api_key:
                genai.configure(api_key=api_key)
            else:
                genai.configure(api_key=DEFAULT_GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
            prompt = "Analyze this image. Describe the primary subjects, the setting, and any actions taking place. Focus on objective details relevant for storytelling."
            image_data = base64.b64encode(img_byte_arr).decode()
            logger.info("Preparing Gemini API request:")
            logger.info(f"Model: gemini-1.5-flash")
            logger.info(f"Prompt: {prompt}")
            logger.info(f"Image data length: {len(image_data)} characters")
            logger.info(f"Safety settings: {safety_settings}")
            logger.info("Sending image to Gemini API for analysis...")
            try:
                request_content = [
                    prompt,
                    {"mime_type": "image/jpeg", "data": image_data}
                ]
                import time
                start_time = time.time()
                logger.info("Starting API call...")
                response = model.generate_content(request_content)
                elapsed_time = time.time() - start_time
                logger.info(f"API call completed in {elapsed_time:.2f} seconds")
                logger.info("Successfully received response from Gemini API")
                logger.info("Gemini API Response Details:")
                logger.info(f"Response type: {type(response)}")
                if response.prompt_feedback:
                    logger.info("Prompt Feedback:")
                    logger.info(f"Block reason: {response.prompt_feedback.block_reason}")
                    logger.info(f"Safety ratings: {response.prompt_feedback.safety_ratings}")
                if response.candidates:
                    logger.info(f"Number of candidates: {len(response.candidates)}")
                    for i, candidate in enumerate(response.candidates):
                        logger.info(f"\nCandidate {i+1}:")
                        logger.info(f"Finish reason: {candidate.finish_reason}")
                        logger.info(f"Safety ratings: {candidate.safety_ratings}")
                        if hasattr(candidate, 'token_count'):
                            if isinstance(candidate.token_count, dict):
                                token_info = f"Token usage - Prompt: {candidate.token_count.get('prompt', 'N/A')}, " \
                                           f"Candidates: {candidate.token_count.get('candidates', 'N/A')}, " \
                                           f"Total: {candidate.token_count.get('total', 'N/A')}"
                            else:
                                token_info = f"Token usage - Total: {candidate.token_count}"
                            logger.info(token_info)
                if response.text:
                    logger.info("\nComplete Response Text:")
                    logger.info(response.text)
                    return response.text
                else:
                    logger.error("Gemini API returned empty response text")
                    return None
            except Exception as api_error:
                elapsed_time = time.time() - start_time
                logger.error(f"Gemini API call failed after {elapsed_time:.2f} seconds: {str(api_error)}")
                logger.error(f"Error type: {type(api_error)}")
                if hasattr(api_error, 'response'):
                    logger.error(f"Gemini API error response: {api_error.response}")
                return None
    except Exception as e:
        error_msg = f"Error processing image {image_path}: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Error type: {type(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Gemini API error response: {e.response}")
        return None

def generate_story(image_summaries, user_prompt=None, max_words=100, max_beats=10, api_key=None):
    """Generate a story using Gemini API based on image summaries, optional user prompt, max words per beat, max number of beats, and optional API key"""
    try:
        logger.info("Starting story generation")
        # Use the provided API key if present, else default
        if api_key:
            genai.configure(api_key=api_key)
        else:
            genai.configure(api_key=DEFAULT_GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)
        
        # Create a formatted list of image summaries
        image_list = "\n".join([f"Image {i+1}: {summary['summary']}" for i, summary in enumerate(image_summaries)])
        
        if len(image_summaries) > max_beats:
            prompt = f"""You are given {len(image_summaries)} images and their descriptions. Your task is to craft a compelling story using a selection of these images. You may reorder, omit, or select the images that best fit the narrative flow. You do not need to use every image. Aim for a story with no more than {max_beats} concise beats, each under {max_words} words.\n"""
            if user_prompt:
                prompt += f"\nThe user has requested the following guidance for the story: {user_prompt}\n"
            prompt += f"""
For each selected image, write a story segment that:
1. Describes what's happening in that moment
2. Advances the overall narrative
3. Connects smoothly with the previous and next segments
4. Is concise and no more than {max_words} words

Format your response with clear markers for each image's segment like this:
[IMAGE X] (where X is the original image number)
Story segment for that image...

And so on for each selected image.

Here are the image descriptions:
""" + image_list
        else:
            prompt = f"""Given these {len(image_summaries)} images and their descriptions, create a compelling story where each image represents a key moment in the narrative.\n"""
            if user_prompt:
                prompt += f"\nThe user has requested the following guidance for the story: {user_prompt}\n"
            prompt += f"""
For each image, write a story segment that:
1. Describes what's happening in that moment
2. Advances the overall narrative
3. Connects smoothly with the previous and next segments
4. Is concise and no more than {max_words} words

Format your response with clear markers for each image's segment like this:
[IMAGE 1]
Story segment for first image...

[IMAGE 2]
Story segment for second image...

And so on for each image.

Here are the image descriptions:
""" + image_list
        
        logger.info("Sending prompt to Gemini API for story generation")
        response = model.generate_content(prompt)
        
        # Log token usage
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'token_count'):
                if isinstance(candidate.token_count, dict):
                    token_info = f"Token usage - Prompt: {candidate.token_count.get('prompt', 'N/A')}, " \
                               f"Candidates: {candidate.token_count.get('candidates', 'N/A')}, " \
                               f"Total: {candidate.token_count.get('total', 'N/A')}"
                else:
                    token_info = f"Token usage - Total: {candidate.token_count}"
                logger.info(token_info)
        
        # Check for errors in the response
        if response.prompt_feedback:
            logger.info(f"Prompt feedback: {response.prompt_feedback}")
            if response.prompt_feedback.block_reason:
                logger.error(f"Gemini API blocked the story generation: {response.prompt_feedback.block_reason}")
                return None
            
        if response.candidates and response.candidates[0].finish_reason:
            logger.info(f"Gemini API story generation finish reason: {response.candidates[0].finish_reason}")
        
        # Parse the story into segments
        if response.text:
            logger.info("Full Gemini API story response text:\n" + response.text)
            
            # Split the story into segments based on [IMAGE X] markers
            segments = []
            current_segment = []
            current_marker = None
            marker_pattern = re.compile(r'^\[IMAGE\s*(\d+)\]', re.IGNORECASE)
            for line in response.text.split('\n'):
                marker_match = marker_pattern.match(line.strip())
                if marker_match:
                    if current_segment and current_marker is not None:
                        segments.append({'marker': current_marker, 'text': '\n'.join(current_segment).strip()})
                        current_segment = []
                    current_marker = int(marker_match.group(1))
                elif line.strip():
                    current_segment.append(line)
            if current_segment and current_marker is not None:
                segments.append({'marker': current_marker, 'text': '\n'.join(current_segment).strip()})
            
            logger.info(f"Parsed story segments and markers: {segments}")
            
            # If markers are present, use them to map to images
            if segments and all('marker' in seg for seg in segments):
                image_slides = []
                for seg in segments:
                    idx = seg['marker'] - 1
                    if 0 <= idx < len(image_summaries):
                        image_url = f"/static/temp_images/{idx+1}_{os.path.basename(image_summaries[idx]['filename'])}"
                        image_slides.append({
                            'image_url': image_url,
                            'story_segment': seg['text']
                        })
                    else:
                        logger.warning(f"[IMAGE {seg['marker']}] marker out of range for available images.")
                if len(image_slides) != len(segments):
                    logger.warning(f"Number of mapped slides ({len(image_slides)}) does not match number of story segments ({len(segments)})")
                return image_slides
            else:
                # Fallback: old logic, split by order
                logger.warning("No [IMAGE X] markers found or parsing failed; falling back to order-based mapping.")
                segments_text = []
                current_segment = []
                for line in response.text.split('\n'):
                    if line.strip().startswith('[IMAGE'):
                        if current_segment:
                            segments_text.append('\n'.join(current_segment))
                            current_segment = []
                    elif line.strip():
                        current_segment.append(line)
                if current_segment:
                    segments_text.append('\n'.join(current_segment))
                image_slides = []
                for i, segment in enumerate(segments_text):
                    if i < len(image_summaries):
                        image_url = f"/static/temp_images/{i+1}_{os.path.basename(image_summaries[i]['filename'])}"
                        image_slides.append({
                            'image_url': image_url,
                            'story_segment': segment
                        })
                if len(image_slides) != len(segments_text):
                    logger.warning(f"Number of mapped slides ({len(image_slides)}) doesn't match number of story segments ({len(segments_text)})")
                return image_slides
        else:
            logger.error("Gemini API returned empty response text")
            return None
            
    except Exception as e:
        logger.error(f"Error generating story: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Gemini API error response: {e.response}")
        return None

def generate_short_uuid():
    """Generate a short UUID (8 characters) for story IDs"""
    return str(uuid.uuid4())[:8]

# Global cleanup manager
class CleanupManager:
    def __init__(self):
        self.cleanup_queue = []  # Priority queue of (timestamp, story_id)
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.thread.start()
        logger.info("Cleanup manager initialized")

    def schedule_cleanup(self, story_id):
        """Schedule a story for cleanup in 4 hours"""
        cleanup_time = time.time() + (4 * 60 * 60)  # 4 hours from now
        with self.lock:
            heapq.heappush(self.cleanup_queue, (cleanup_time, story_id))
            logger.info(f"Scheduled cleanup for story {story_id} at {datetime.fromtimestamp(cleanup_time)}")

    def _cleanup_worker(self):
        """Background worker that handles all cleanup operations"""
        while True:
            try:
                current_time = time.time()
                
                with self.lock:
                    # Check if there are any stories to clean up
                    while self.cleanup_queue and self.cleanup_queue[0][0] <= current_time:
                        _, story_id = heapq.heappop(self.cleanup_queue)
                        story_dir = os.path.join(current_app.static_folder, 'stories', story_id)
                        
                        if os.path.exists(story_dir):
                            try:
                                shutil.rmtree(story_dir)
                                logger.info(f"Cleaned up story {story_id}")
                            except Exception as e:
                                logger.error(f"Error cleaning up story {story_id}: {str(e)}")
                
                # Sleep for a short time before next check
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {str(e)}")
                time.sleep(60)  # Wait before retrying

# Initialize the cleanup manager
cleanup_manager = CleanupManager()

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
@limiter.limit('10 per day')
def upload_file():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400

    # Generate unique story ID
    story_id = generate_short_uuid()
    story_dir = os.path.join(current_app.static_folder, 'stories', story_id)
    temp_dir = os.path.join(story_dir, 'temp_images')
    
    # Create directories
    os.makedirs(story_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    image_summaries = []
    image_slides = []
    
    try:
        for file in files:
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            
            if ext == 'zip':
                # Process zip file
                zip_path = os.path.join(temp_dir, filename)
                file.save(zip_path)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                os.remove(zip_path)
                
                for i, image_file in enumerate(sorted(os.listdir(temp_dir))):
                    if image_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                        image_path = os.path.join(temp_dir, image_file)
                        static_image_name = f"{i+1}_{os.path.basename(image_file)}"
                        static_image_path = os.path.join(temp_dir, static_image_name)
                        copyfile(image_path, static_image_path)
                        image_url = f"/static/stories/{story_id}/temp_images/{static_image_name}"
                        summary = process_image(static_image_path, request.form.get('apiKey'))
                        if summary:
                            image_summaries.append({
                                'filename': image_file,
                                'summary': summary
                            })
                            image_slides.append({
                                'image_url': image_url,
                                'story_segment': summary
                            })
                            logger.info(f"Successfully processed image {image_file}")
                        else:
                            logger.warning(f"Failed to process image {image_file}")
                        os.remove(image_path)
            
            elif ext in ('jpg', 'jpeg') and (filename.endswith('.jpg') or filename.endswith('.jpeg')):
                static_image_name = f"{len(image_summaries)+1}_{filename}"
                static_image_path = os.path.join(temp_dir, static_image_name)
                file.save(static_image_path)
                image_url = f"/static/stories/{story_id}/temp_images/{static_image_name}"
                summary = process_image(static_image_path, request.form.get('apiKey'))
                if summary:
                    image_summaries.append({
                        'filename': filename,
                        'summary': summary
                    })
                    image_slides.append({
                        'image_url': image_url,
                        'story_segment': summary
                    })
                    logger.info(f"Successfully processed image {filename}")
                else:
                    logger.warning(f"Failed to process image {filename}")

        if not image_summaries:
            return jsonify({'error': 'No valid images found'}), 400

        logger.info(f"Successfully processed {len(image_summaries)} images from all uploads")
        
        # Generate story
        logger.info("Generating story from image summaries...")
        story = generate_story(image_summaries, request.form.get('storyPrompt'), request.form.get('maxWords'), request.form.get('maxBeats'), request.form.get('apiKey'))
        
        if not story:
            return jsonify({'error': 'Failed to generate story'}), 500

        # Save story data
        story_data = {
            'id': story_id,
            'created_at': datetime.now().isoformat(),
            'slides': image_slides,
            'story': story
        }
        
        with open(os.path.join(story_dir, 'story.json'), 'w') as f:
            json.dump(story_data, f)

        # Schedule cleanup for this story
        cleanup_manager.schedule_cleanup(story_id)

        return jsonify({
            'success': True,
            'story_id': story_id,
            'story': story,
            'image_slides': image_slides
        })

    except Exception as e:
        logger.error(f"Error processing files: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main.route('/story/<story_id>')
def view_story(story_id):
    story_dir = os.path.join(current_app.static_folder, 'stories', story_id)
    story_file = os.path.join(story_dir, 'story.json')
    
    if not os.path.exists(story_file):
        return jsonify({'error': 'Story not found'}), 404
        
    with open(story_file, 'r') as f:
        story_data = json.load(f)
    
    return render_template('story.html', 
                         story_id=story_id,
                         slides=story_data['slides'],
                         story=story_data['story'])

@main.route('/slideshow')
def slideshow():
    return render_template('slideshow.html') 