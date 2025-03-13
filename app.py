from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
import json
from datetime import datetime
import calendar
from dateutil.relativedelta import relativedelta
import os
import secrets

app = Flask(__name__)

# Production configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=1800,  # 30 minutes session timeout
)

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
            response = make_response(redirect(url_for('index')))
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
            return response
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
            return json.load(f)
    except FileNotFoundError:
        return {"projects": {}}

def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/')
def index():
    if not check_auth():
        return redirect(url_for('login'))
    data = load_data()
    return render_template('index.html', projects=list(data['projects'].keys()))

@app.route('/get_calendar_data/<project>')
def get_calendar_data(project):
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    if project in data['projects']:
        return jsonify(data['projects'][project])
    return jsonify({"calendar_entries": []})

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

@app.route('/add_project', methods=['POST'])
def add_project():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    project_name = request.json.get('project_name')
    
    if project_name and project_name not in data['projects']:
        data['projects'][project_name] = {"calendar_entries": []}
        save_data(data)
        return jsonify({"success": True, "projects": list(data['projects'].keys())})
    
    return jsonify({"success": False, "error": "Project already exists or invalid name"})

@app.route('/delete_project', methods=['POST'])
def delete_project():
    if not check_auth():
        return jsonify({"error": "Unauthorized"}), 401
    data = load_data()
    project_name = request.json.get('project_name')
    
    if project_name and project_name in data['projects']:
        del data['projects'][project_name]
        save_data(data)
        return jsonify({"success": True, "projects": list(data['projects'].keys())})
    
    return jsonify({"success": False, "error": "Project not found"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
