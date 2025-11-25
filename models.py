from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='user', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(10), nullable=False)  # 'docx' or 'pptx'
    topic = db.Column(db.Text, nullable=False)
    outline = db.Column(db.Text)  # JSON stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contents = db.relationship('Content', backref='project', lazy=True)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    section_id = db.Column(db.String(50), nullable=False)
    section_title = db.Column(db.String(255), nullable=False)
    content_text = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RefinementHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    section_id = db.Column(db.String(50), nullable=False)
    prompt = db.Column(db.Text)
    old_content = db.Column(db.Text)
    new_content = db.Column(db.Text)
    user_feedback = db.Column(db.String(10))  # 'like' or 'dislike'
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)