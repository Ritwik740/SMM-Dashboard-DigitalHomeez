from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response, flash, send_file
import json
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import os
import secrets
# from google import genai
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import io
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import textwrap
from io import BytesIO
# from google.genai import types
from google.generativeai import types
# Load environment variables
load_dotenv()

app = Flask(__name__)

# Production configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    SESSION_COOKIE_SECURE=True,  # Always use secure cookies for better security
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes session timeout
    UPLOAD_FOLDER='uploads'
)

# Ensure uploads directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Configure Google Gemini AI
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Initialize client
client = genai.Client()

# Model IDs
TEXT_MODEL_ID = "models/gemini-2.0-flash"
IMAGE_MODEL_ID = "models/gemini-2.0-flash-exp"

# Ensure HTTPS on Render
if 'RENDER' in os.environ:
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', "admin@alvina19")

# Production error logging
if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Use Render's log directory if available
    log_dir = os.environ.get('RENDER_LOG_DIR', 'logs')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10240,
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Application startup')

def check_auth():
    return session.get('authenticated', False)

@app.after_request
def add_header(response):
    # Prevent caching of all responses
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['authenticated'] = True
            session.permanent = True  # Make session permanent
            return redirect(url_for('clients'))
        return render_template('login.html', error="Invalid password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('login')))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    return response

def load_data():
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            # Ensure required keys exist
            if 'clients' not in data:
                data['clients'] = {}
            if 'projects' not in data:
                data['projects'] = {}
            return data
    except FileNotFoundError:
        return {"clients": {}, "projects": {}}

def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    if not check_auth():
        return redirect(url_for('login'))
    return redirect(url_for('clients'))

@app.route('/clients')
def clients():
    if not check_auth():
        return redirect(url_for('login'))
    data = load_data()
    return render_template('client_management.html', clients=data.get('clients', {}))

def generate_text(prompt):
    """Generate text using Gemini."""
    try:
        response = client.models.generate_content(
            model=TEXT_MODEL_ID,
            contents=prompt
        )
        return response.text
    except Exception as e:
        app.logger.error(f"Error generating text: {str(e)}")
        return None

def generate_content_calendar(client_name, industry, target_audience, goals, target_month, platforms, num_posts, num_reels):
    try:
        # Parse the target month (expected format: YYYY-MM)
        year, month = map(int, target_month.split('-'))
        
        # Get the first and last day of the target month
        first_day = datetime(year, month, 1)
        last_day = datetime(year, month + 1, 1) - relativedelta(days=1)
        
        # Calculate total posts needed
        total_posts = num_posts + num_reels
        
        # Create content type mapping with proper case
        content_types = {
            'Instagram': ['Image', 'Reel', 'Carousel'],
            'Facebook': ['Image', 'Video', 'Status'],
            'LinkedIn': ['Article', 'Image', 'Video'],
            'Twitter': ['Tweet', 'Thread', 'Poll']
        }
        
        # Normalize platform names to proper case
        normalized_platforms = []
        for platform in platforms:
            # Find the proper case version of the platform name
            proper_case = next((k for k in content_types.keys() if k.lower() == platform.lower()), platform)
            normalized_platforms.append(proper_case)
        
        # Filter content types based on selected platforms
        allowed_content_types = []
        for platform in normalized_platforms:
            if platform in content_types:
                allowed_content_types.extend(content_types[platform])
        
        prompt = f"""Generate a content calendar for {client_name}, a {industry} business targeting {target_audience}.
        Goals: {goals}
        
        IMPORTANT: You MUST generate a JSON array with EXACT dates for {first_day.strftime('%B %Y')}.
        Each entry MUST have a valid date in YYYY-MM-DD format.
        
        Selected Platforms: {', '.join(normalized_platforms)}
        Number of Posts: {num_posts}
        Number of Reels: {num_reels}
        Allowed Content Types: {', '.join(allowed_content_types)}
        
        Format the response as a JSON array with the following structure:
        [
            {{
                "date": "YYYY-MM-DD",  # Must be a valid date between {first_day.strftime('%Y-%m-%d')} and {last_day.strftime('%Y-%m-%d')}
                "platform": "platform_name",  # Must be one of: {', '.join(normalized_platforms)}
                "content_type": "type_of_content",  # Must be one of: {', '.join(allowed_content_types)}
                "topic": "main_topic",
                "description": "short_phrase",  # MUST be a concise phrase with maximum 15 words
                "hashtags": "relevant_hashtags",
                "call_to_action": "action_phrase"  # MUST be a short phrase with maximum 10 words
            }}
        ]
        
        Requirements:
        1. Generate exactly {total_posts} posts
        2. Use only the selected platforms: {', '.join(normalized_platforms)}
        3. Use only the allowed content types: {', '.join(allowed_content_types)}
        4. Each entry MUST have a valid date
        5. Dates must be in chronological order
        6. Content should align with business goals and target audience
        7. Include relevant hashtags and call-to-action phrases
        8. For each platform, use appropriate content types:
           - Instagram: {', '.join(content_types['Instagram'])}
           - Facebook: {', '.join(content_types['Facebook'])}
           - LinkedIn: {', '.join(content_types['LinkedIn'])}
           - Twitter: {', '.join(content_types['Twitter'])}
        9. Keep descriptions concise and impactful (max 15 words)
        10. Keep call-to-action phrases short and clear (max 10 words)
        
        IMPORTANT: Your response must be ONLY the JSON array, with no additional text or formatting.
        """
        
        response_text = generate_text(prompt)
        if not response_text:
            return None
            
        response_text = response_text.strip()
        
        # Remove any markdown formatting if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        print(f"Raw API response: {response_text}")  # Debug log
        
        try:
            calendar_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Response text: {response_text}")
            return None
        
        # Validate dates and content types
        for entry in calendar_data:
            entry_date = datetime.strptime(entry['date'], '%Y-%m-%d')
            if not (first_day <= entry_date <= last_day):
                raise ValueError(f"Invalid date {entry['date']} - must be between {first_day.strftime('%Y-%m-%d')} and {last_day.strftime('%Y-%m-%d')}")
            
            # Normalize platform name for comparison
            entry_platform = next((k for k in content_types.keys() if k.lower() == entry['platform'].lower()), entry['platform'])
            if entry_platform not in normalized_platforms:
                raise ValueError(f"Invalid platform {entry['platform']} - must be one of {', '.join(normalized_platforms)}")
            
            if entry['content_type'] not in allowed_content_types:
                raise ValueError(f"Invalid content type {entry['content_type']} - must be one of {', '.join(allowed_content_types)}")
            
            # Update the platform name to proper case
            entry['platform'] = entry_platform
            
            # Validate description length
            if len(entry['description'].split()) > 15:
                raise ValueError(f"Description too long: {entry['description']} - must be maximum 15 words")
            
            # Validate call-to-action length
            if len(entry['call_to_action'].split()) > 10:
                raise ValueError(f"Call-to-action too long: {entry['call_to_action']} - must be maximum 10 words")
        
        return json.dumps(calendar_data)
    except Exception as e:
        print(f"Error generating content calendar: {str(e)}")
        return None

def analyze_reference_images(image_files):
    try:
        image_insights = []
        for image in image_files:
            img = Image.open(image)
            response = client.models.generate_content(
                model=IMAGE_MODEL_ID,
                contents=[
                    "Analyze this reference image and provide insights for social media content creation. Include style, mood, color scheme, and potential content themes.",
                    img
                ]
            )
            image_insights.append(response.text)
        return "\n\n".join(image_insights)
    except Exception as e:
        app.logger.error(f"Error analyzing images: {str(e)}")
        return None

@app.route('/add_client', methods=['POST'])
def add_client():
    if not check_auth():
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        data = load_data()
        
        # Get form data
        client_data = {
            'companyName': request.form['companyName'],
            'numPosts': int(request.form['numPosts']),
            'numReels': int(request.form['numReels']),
            'platforms': json.loads(request.form['platforms']),
            'targetMonth': request.form['targetMonth'],
            'suggestions': request.form.get('suggestions', '')
        }
        
        # Handle image uploads
        image_insights = None
        if 'suggestionImages' in request.files:
            files = request.files.getlist('suggestionImages')
            if files and any(file.filename != '' for file in files):
                image_insights = analyze_reference_images(files)
                if image_insights:
                    client_data['imageInsights'] = image_insights
        
        # Generate content calendar with target month and platform selections
        content_calendar = generate_content_calendar(
            client_data['companyName'], 
            '', 
            '', 
            '', 
            client_data['targetMonth'],
            client_data['platforms'],
            client_data['numPosts'],
            client_data['numReels']
        )
        if content_calendar:
            client_data['contentCalendar'] = content_calendar
        else:
            return jsonify({"success": False, "error": "Failed to generate content calendar"})
        
        # Save client data
        company_name = client_data['companyName']
        if company_name not in data['clients']:
            data['clients'][company_name] = client_data
            save_data(data)
            
            # Create project entries for the content calendar
            data['projects'][company_name] = {
                "calendar_entries": []
            }
            save_data(data)
            
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Client already exists"})
            
    except Exception as e:
        app.logger.error(f"Error adding client: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/get_calendar_data/<project>')
def get_calendar_data(project):
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    
    # Get project data
    project_data = data['projects'].get(project, {"calendar_entries": []})
    
    # Get client data if it exists
    client_data = data['clients'].get(project)
    if client_data and 'contentCalendar' in client_data:
        try:
            # Parse the content calendar JSON
            calendar_data = json.loads(client_data['contentCalendar'])
            entries = []
            
            for entry in calendar_data:
                # Create a calendar entry with the parsed data
                calendar_entry = {
                    'date': entry['date'],
                    'day': datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%A'),
                    'content_type': entry['content_type'],
                    'channel': entry['platform'],
                    'status': 'pending',
                    'text_content': f"{entry['topic']}\n{entry['description']}",
                    'approval': 'pending',
                    'hashtags': entry['hashtags'],  # Add hashtags separately
                    'call_to_action': entry['call_to_action'],  # Add call-to-action separately
                    'references': f"Hashtags: {entry['hashtags']}\nCall to Action: {entry['call_to_action']}"
                }
                entries.append(calendar_entry)
            
            # Add these entries to the project data
            project_data['calendar_entries'] = entries
            save_data(data)
            
        except json.JSONDecodeError as e:
            app.logger.error(f"Error parsing calendar JSON: {str(e)}")
            return jsonify({"error": "Invalid calendar data format"}), 400
        except Exception as e:
            app.logger.error(f"Error processing calendar data: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify(project_data)

@app.route('/add_entry', methods=['POST'])
def add_entry():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    entry = request.json
    project = entry['project']
    
    if project not in data['projects']:
        data['projects'][project] = {"calendar_entries": []}
    
    data['projects'][project]['calendar_entries'].append({
        'date': entry['date'],
        'day': entry['day'],
        'content_type': entry['content_type'],
        'channel': entry['channel'],
        'status': entry['status'],
        'text_content': entry['text_content'],
        'approval': entry['approval'],
        'references': entry['references']
    })
    
    save_data(data)
    return jsonify({"success": True})

@app.route('/update_entry', methods=['POST'])
def update_entry():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    entry = request.json
    project = entry['project']
    index = entry['index']
    
    if project in data['projects']:
        if 0 <= index < len(data['projects'][project]['calendar_entries']):
            data['projects'][project]['calendar_entries'][index] = {
                'date': entry['date'],
                'day': entry['day'],
                'content_type': entry['content_type'],
                'channel': entry['channel'],
                'status': entry['status'],
                'text_content': entry['text_content'],
                'approval': entry['approval'],
                'references': entry['references']
            }
            save_data(data)
            return jsonify({"success": True})
    
    return jsonify({"success": False})

@app.route('/delete_entry', methods=['POST'])
def delete_entry():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    entry = request.json
    project = entry['project']
    index = entry['index']
    
    if project in data['projects']:
        if 0 <= index < len(data['projects'][project]['calendar_entries']):
            del data['projects'][project]['calendar_entries'][index]
            save_data(data)
            return jsonify({"success": True})
    
    return jsonify({"success": False})

@app.route('/dashboard')
def dashboard():
    if not check_auth():
        return redirect(url_for('login'))
    data = load_data()
    return render_template('index.html', projects=list(data['clients'].keys()))

@app.route('/test_gemini')
def test_gemini():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Test the text generation model
        response_text = generate_text("Test message: Hello, this is a test of the Gemini API connection.")
        return jsonify({
            "success": True,
            "message": "API connection successful!",
            "test_response": response_text
        })
    except Exception as e:
        app.logger.error(f"Gemini API test failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def generate_preview_image(text_content, content_type, client_name, hashtags, call_to_action):
    """Generate a preview image using Gemini."""
    try:
        # Create prompt for image generation
        prompt = f"""Create a professional social media advertisement image with the following specifications:
        - Brand: {client_name}
        - Main Text: '{text_content}'
        - Style: Modern and appetizing
        - Colors: Warm tones with red and orange
        - Include: Professional product image with visual elements
        """
        
        app.logger.info(f"Generating image with prompt: {prompt}")
        
        # Generate image using Gemini
        response = client.models.generate_content(
            model=IMAGE_MODEL_ID,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['Text', 'Image']
            )
        )
        app.logger.info(f"Got response from Gemini: {response}")
        
        # Extract image from response
        if hasattr(response, 'candidates') and response.candidates:
            app.logger.info(f"Response has candidates")
            for part in response.candidates[0].content.parts:
                app.logger.info(f"Checking part: {part}")
                if hasattr(part, 'inline_data') and part.inline_data is not None:
                    app.logger.info("Found image data in response")
                    # Convert image data to bytes
                    img_data = part.inline_data.data
                    img_bytes = bytes(img_data)
                    
                    # Create a BytesIO object
                    img_buffer = BytesIO(img_bytes)
                    
                    # Return the image buffer
                    return img_buffer
        else:
            app.logger.error("No candidates found in response")
                
        app.logger.error("No image generated in response")
        return None
        
    except Exception as e:
        app.logger.error(f"Error generating preview image: {str(e)}")
        return None

@app.route('/preview/<client_name>/<int:index>')
def preview_image(client_name, index):
    """Generate and display a preview image for a specific post."""
    try:
        # Get calendar data
        calendar_response = get_calendar_data(client_name)
        calendar_data = calendar_response.get_json()  # Convert response to JSON
        
        if not calendar_data or 'calendar_entries' not in calendar_data or index >= len(calendar_data['calendar_entries']):
            app.logger.error("Post not found in calendar data")
            return "Post not found", 404
            
        post = calendar_data['calendar_entries'][index]
        app.logger.info(f"Generating preview for post: {post}")
        
        # Generate preview image
        img_buffer = generate_preview_image(
            post['text_content'],
            post['content_type'],
            client_name,
            post.get('hashtags', ''),
            post.get('call_to_action', '')
        )
        
        if img_buffer is None:
            app.logger.error("Failed to generate image")
            return "Failed to generate image", 404
            
        # Reset buffer position to beginning
        img_buffer.seek(0)
        
        # Return the image with proper headers
        return send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=False,
            download_name='preview.png'
        )
        
    except Exception as e:
        app.logger.error(f"Error in preview_image: {str(e)}")
        return "Error generating preview", 500

@app.route('/delete_project', methods=['POST'])
def delete_project():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = load_data()
        project_name = request.json.get('project_name')
    
        if not project_name:
            return jsonify({"success": False, "error": "Project name is required"}), 400
            
        # Delete from both clients and projects
        if project_name in data['clients']:
            del data['clients'][project_name]
        if project_name in data['projects']:
            del data['projects'][project_name]
            
        save_data(data)
        
        # Return updated project list for frontend
        return jsonify({
            "success": True,
            "projects": list(data['clients'].keys())
        })
        
    except Exception as e:
        app.logger.error(f"Error deleting project: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Set debug mode based on environment
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=debug_mode)
