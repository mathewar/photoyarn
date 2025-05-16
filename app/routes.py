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

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
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
            max_width = 400
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_height = int(height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"Image resized to: ({max_width}, {new_height})")
            img_byte_arr = io.BytesIO()
            img = img.convert('RGB')
            img.save(img_byte_arr, format='JPEG')
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

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/upload', methods=['POST'])
@limiter.limit('10 per day')
def upload_file():
    if 'file' not in request.files:
        logger.error("No file part in request")
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.error("No selected file")
        return jsonify({'error': 'No selected file'}), 400
    
    # Get the optional story prompt, max words, max beats, and api_key from the form
    user_prompt = request.form.get('story_prompt', None)
    api_key = request.form.get('api_key', None)
    try:
        max_words = int(request.form.get('max_words', 100))
        if max_words < 10 or max_words > 500:
            max_words = 100
    except Exception:
        max_words = 100
    try:
        max_beats = int(request.form.get('max_beats', 10))
        if max_beats < 1 or max_beats > 50:
            max_beats = 10
    except Exception:
        max_beats = 10
    
    if file and allowed_file(file.filename):
        try:
            logger.info(f"Processing upload: {file.filename}")
            
            # Save the zip file
            filename = secure_filename(file.filename)
            zip_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            logger.info(f"Saving zip file to: {filename}")
            
            # Save file in chunks to handle large files
            chunk_size = 1024 * 1024  # 1MB chunks
            with open(zip_path, 'wb') as f:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
            logger.info("Zip file saved successfully")
            
            # Prepare static temp_images directory
            static_temp_dir = os.path.join(current_app.root_path, 'static', 'temp_images')
            os.makedirs(static_temp_dir, exist_ok=True)
            
            # Extract images
            image_summaries = []
            image_slides = []
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Create a temporary directory for extracted images
                extract_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'extracted')
                os.makedirs(extract_dir, exist_ok=True)
                logger.info(f"Created extraction directory")
                
                # Extract and process each image
                image_files = [f for f in zip_ref.namelist() 
                             if f.lower().endswith(('.png', '.jpg', '.jpeg')) 
                             and not f.startswith('._')  # Skip macOS metadata files
                             and not f.startswith('__MACOSX')]  # Skip macOS system files
                total_images = len(image_files)
                logger.info(f"Found {total_images} images in zip file")
                
                for i, image_file in enumerate(image_files, 1):
                    try:
                        logger.info(f"Processing image {i}/{total_images}: {os.path.basename(image_file)}")
                        
                        # Extract the image
                        zip_ref.extract(image_file, extract_dir)
                        image_path = os.path.join(extract_dir, image_file)
                        
                        # Copy image to static/temp_images for serving
                        static_image_name = f"{i}_{os.path.basename(image_file)}"
                        static_image_path = os.path.join(static_temp_dir, static_image_name)
                        copyfile(image_path, static_image_path)
                        image_url = f"/static/temp_images/{static_image_name}"
                        
                        # Process the image
                        summary = process_image(image_path, api_key)
                        if summary:
                            image_summaries.append({
                                'filename': image_file,
                                'summary': summary
                            })
                            image_slides.append({
                                'image_url': image_url,
                                'story_segment': summary
                            })
                            logger.info(f"Successfully processed image {i}/{total_images}")
                        else:
                            logger.warning(f"Failed to process image {i}/{total_images}")
                    except Exception as e:
                        logger.error(f"Error processing {image_file}: {str(e)}")
                        continue
            
            if not image_summaries:
                logger.error("No valid images found in the zip file")
                return jsonify({'error': 'No valid images found in the zip file'}), 400
            
            logger.info(f"Successfully processed {len(image_summaries)} images")
            
            # Generate story
            logger.info("Generating story from image summaries...")
            slides = generate_story(image_summaries, user_prompt, max_words, max_beats, api_key)
            if not slides:
                logger.error("Failed to generate story")
                return jsonify({'error': 'Failed to generate story'}), 500
            
            logger.info("Story generated successfully")
            
            # Clean up
            try:
                os.remove(zip_path)
                for file in os.listdir(extract_dir):
                    os.remove(os.path.join(extract_dir, file))
                os.rmdir(extract_dir)
                logger.info("Cleanup completed successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            
            return jsonify({
                'success': True,
                'slides': slides,
                'images': image_summaries,
            })
            
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            # Clean up on error
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                if os.path.exists(extract_dir):
                    for file in os.listdir(extract_dir):
                        os.remove(os.path.join(extract_dir, file))
                    os.rmdir(extract_dir)
                logger.info("Cleanup completed after error")
            except:
                logger.error("Error during cleanup after error")
            return jsonify({'error': str(e)}), 500
    
    logger.error("Invalid file type")
    return jsonify({'error': 'Invalid file type'}), 400

@main.route('/slideshow')
def slideshow():
    return render_template('slideshow.html') 