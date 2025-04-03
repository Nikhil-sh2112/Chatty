from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import joinedload 

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
     # Required properties for Flask-Login
    @property
    def is_active(self):
        return True  # All users are active by default

    @property
    def is_authenticated(self):
        return True  # Return True if user is authenticated

    @property
    def is_anonymous(self):
        return False  # False for regular users
    
    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref=db.backref('sender', lazy='joined'),lazy=True)
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref=db.backref('recipient', lazy='joined'), lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))