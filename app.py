import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from utils.file_converter import convert_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for  # Ensure this is imported
from sqlalchemy.orm import joinedload

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'txt'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Required for Flask-Login
    @property
    def is_active(self):
        return True

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

# Login manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user) 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    sent_to = db.session.query(User).join(Message, User.id == Message.recipient_id)\
              .filter(Message.sender_id == current_user.id)\
              .distinct().all()
              
    received_from = db.session.query(User).join(Message, User.id == Message.sender_id)\
                   .filter(Message.recipient_id == current_user.id)\
                   .distinct().all()
    
    contacts = list(set(sent_to + received_from))
    return render_template('dashboard.html', contacts=contacts)

@app.route('/chat/<email>', methods=['GET', 'POST'])
@login_required
def chat(email):
    recipient = User.query.filter_by(email=email).first()
    if not recipient:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        content = request.form.get('message')
        file = request.files.get('file')
        
        if not content and not file:
            return jsonify({'status': 'error', 'message': 'Empty message'}), 400
        
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            content=content,
            timestamp=datetime.utcnow()
        )
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if content and 'convert to' in content.lower():
                target_format = content.lower().split('convert to')[-1].strip().split()[0]
                output_path, output_filename = convert_file(filepath, target_format)
                if output_path:
                    message.file_path = output_path
                    message.file_name = output_filename
                    os.remove(filepath)
                else:
                    message.file_path = filepath
                    message.file_name = filename
            else:
                message.file_path = filepath
                message.file_name = filename
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message_id': message.id,
            'timestamp': message.timestamp.isoformat(),
            'file_url': url_for('download_file', filename=message.file_name) if message.file_path else None
        })
    
    messages = Message.query.options(
        joinedload(Message.sender),
        joinedload(Message.recipient)
    ).filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient.id)) |
        ((Message.sender_id == recipient.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('chat.html', 
                         recipient=recipient, 
                         messages=messages,
                         current_user=current_user)

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/api/messages/<int:recipient_id>')
@login_required
def get_messages(recipient_id):
    since = request.args.get('since', 0, type=int)
    
    messages = Message.query.filter(
        Message.id > since,
        ((Message.sender_id == current_user.id) & (Message.recipient_id == recipient_id)) |
        ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'sender_id': msg.sender_id,
        'file_url': url_for('download_file', filename=msg.file_name) if msg.file_path else None,
        'file_name': msg.file_name
    } for msg in messages]
    
    return jsonify(messages_data)

if __name__ == '__main__':
    app.run(debug=True)