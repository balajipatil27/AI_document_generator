from flask import Flask, request, jsonify, send_file, session, render_template
from flask_cors import CORS
from models import db, User, Project, Content, RefinementHistory
from gemini_client import GeminiClient
from document_generator import DocumentGenerator
import io
import json
import bcrypt
import os

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = 'your-flask-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///documents.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
CORS(app, supports_credentials=True)

# Gemini API configuration
gemini_client = GeminiClient(GEMINI_API_KEY)

# Password hashing functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Authentication middleware
def get_user_id_from_session():
    return session.get('user_id')

# Frontend Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/editor')
def editor_page():
    return render_template('editor.html')

# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already exists'}), 400
    
    try:
        new_user = User(
            email=email,
            password_hash=hash_password(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        session['user_id'] = new_user.id
        session['email'] = new_user.email
        
        return jsonify({'message': 'Registration successful', 'user_id': new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and verify_password(password, user.password_hash):
        session['user_id'] = user.id
        session['email'] = user.email
        return jsonify({'message': 'Login successful', 'user_id': user.id})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    user_id = get_user_id_from_session()
    if user_id:
        user = User.query.get(user_id)
        return jsonify({'authenticated': True, 'user_id': user_id, 'email': user.email})
    return jsonify({'authenticated': False}), 401

@app.route('/api/projects', methods=['GET'])
def get_projects():
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    projects = Project.query.filter_by(user_id=user_id).order_by(Project.created_at.desc()).all()
    
    projects_list = []
    for project in projects:
        project_dict = {
            'id': project.id,
            'title': project.title,
            'document_type': project.document_type,
            'topic': project.topic,
            'outline': json.loads(project.outline) if project.outline else [],
            'created_at': project.created_at.isoformat()
        }
        projects_list.append(project_dict)
    
    return jsonify(projects_list)

@app.route('/api/projects', methods=['POST'])
def create_project():
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    
    try:
        new_project = Project(
            user_id=user_id,
            title=data['title'],
            document_type=data['document_type'],
            topic=data['topic'],
            outline=json.dumps(data.get('outline', []))
        )
        db.session.add(new_project)
        db.session.commit()
        
        return jsonify({'project_id': new_project.id, 'message': 'Project created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create project'}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    contents = Content.query.filter_by(project_id=project_id).order_by(Content.section_id).all()
    
    project_dict = {
        'id': project.id,
        'title': project.title,
        'document_type': project.document_type,
        'topic': project.topic,
        'outline': json.loads(project.outline) if project.outline else [],
        'created_at': project.created_at.isoformat(),
        'contents': [{
            'id': content.id,
            'section_id': content.section_id,
            'section_title': content.section_title,
            'content_text': content.content_text,
            'version': content.version
        } for content in contents]
    }
    
    return jsonify(project_dict)

# ADD THIS DELETE ENDPOINT
@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    try:
        # Delete related content and refinement history first
        Content.query.filter_by(project_id=project_id).delete()
        RefinementHistory.query.filter_by(project_id=project_id).delete()
        
        # Delete the project
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({'message': 'Project deleted successfully'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting project: {e}")
        return jsonify({'error': 'Failed to delete project'}), 500

@app.route('/api/projects/<int:project_id>/generate', methods=['POST'])
def generate_content(project_id):
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    outline = json.loads(project.outline) if project.outline else []
    
    generated_count = 0
    for section in outline:
        prompt = f"Write concise, focused content for the section: '{section['title']}' about: {project.topic}. Keep it brief and to the point - maximum 150-200 words suitable for one page/slide."
        
        content = gemini_client.generate_content(prompt, project.topic)
        
        if content:
            new_content = Content(
                project_id=project_id,
                section_id=section['id'],
                section_title=section['title'],
                content_text=content
            )
            db.session.add(new_content)
            generated_count += 1
    
    db.session.commit()
    return jsonify({'message': f'Content generated successfully for {generated_count} sections'})

@app.route('/api/projects/<int:project_id>/refine', methods=['POST'])
def refine_content(project_id):
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    section_id = data.get('section_id')
    refinement_prompt = data.get('prompt')
    
    content = Content.query.filter_by(
        project_id=project_id, 
        section_id=section_id
    ).order_by(Content.version.desc()).first()
    
    if not content:
        return jsonify({'error': 'Content not found'}), 404
    
    refined_content = gemini_client.refine_content(content.content_text, refinement_prompt)
    
    if refined_content:
        refinement_history = RefinementHistory(
            project_id=project_id,
            section_id=section_id,
            prompt=refinement_prompt,
            old_content=content.content_text,
            new_content=refined_content
        )
        db.session.add(refinement_history)
        
        new_content = Content(
            project_id=project_id,
            section_id=section_id,
            section_title=content.section_title,
            content_text=refined_content,
            version=content.version + 1
        )
        db.session.add(new_content)
        
        db.session.commit()
        return jsonify({'refined_content': refined_content})
    
    return jsonify({'error': 'Failed to refine content'}), 500

@app.route('/api/generate-outline', methods=['POST'])
def generate_outline():
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    topic = data.get('topic')
    doc_type = data.get('document_type')
    
    outline_text = gemini_client.generate_outline(topic, doc_type)
    
    try:
        outline_data = json.loads(outline_text)
        if doc_type == 'docx':
            sections = [{'id': f'section_{i}', 'title': title} for i, title in enumerate(outline_data)]
            return jsonify({'outline': sections})
        else:
            slides = [{'id': f'slide_{i}', 'title': title} for i, title in enumerate(outline_data)]
            return jsonify({'outline': slides})
    except json.JSONDecodeError:
        if doc_type == 'docx':
            sections = [
                {'id': 'section_0', 'title': 'Introduction'},
                {'id': 'section_1', 'title': 'Background'},
                {'id': 'section_2', 'title': 'Main Content'},
                {'id': 'section_3', 'title': 'Conclusion'}
            ]
            return jsonify({'outline': sections})
        else:
            slides = [
                {'id': 'slide_0', 'title': 'Title Slide'},
                {'id': 'slide_1', 'title': 'Introduction'},
                {'id': 'slide_2', 'title': 'Main Points'},
                {'id': 'slide_3', 'title': 'Conclusion'}
            ]
            return jsonify({'outline': slides})

@app.route('/api/projects/<int:project_id>/export', methods=['GET'])
def export_document(project_id):
    user_id = get_user_id_from_session()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    project = Project.query.filter_by(id=project_id, user_id=user_id).first()
    
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    contents = Content.query.filter_by(project_id=project_id).all()
    
    project_dict = {
        'title': project.title,
        'document_type': project.document_type,
        'topic': project.topic,
        'outline': json.loads(project.outline) if project.outline else []
    }
    
    contents_list = [{
        'section_id': content.section_id,
        'section_title': content.section_title,
        'content_text': content.content_text
    } for content in contents]
    
    if project_dict['document_type'] == 'docx':
        doc = DocumentGenerator.generate_docx(project_dict, contents_list)
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"{project_dict['title']}.docx", mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    else:
        prs = DocumentGenerator.generate_pptx(project_dict, contents_list)
        buffer = io.BytesIO()
        prs.save(buffer)
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"{project_dict['title']}.pptx", mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting AI Document Generator on port {port}")
    print("Note: Using mock AI functions - no external API required")
    app.run(debug=False, host='0.0.0.0', port=port)