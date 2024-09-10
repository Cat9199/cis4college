from flask import Flask, request, redirect, url_for, render_template, flash, session, Blueprint , send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Boolean, Column
from datetime import datetime, timedelta
from flask_migrate import Migrate
import os
import random
import string
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')

# Load configurations from environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///registration.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'Password')  # Use environment variable for production
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.permanent_session_lifetime = timedelta(days=90)

# Initialize SQLAlchemy and Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Rename the blueprint to avoid conflict
admin_bp = Blueprint('admin', __name__)

# Define the Registration model
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    english_name = db.Column(db.String(100), nullable=False)
    arabic_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    address = db.Column(db.String(200), nullable=False)
    program = db.Column(db.String(50), nullable=False)
    identity_document = db.Column(db.String(100), nullable=False)
    degree_document = db.Column(db.String(100), nullable=False)
    additional_document = db.Column(db.String(100), nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Helper function to save files
def save_file(file):
    """Save the file to the upload folder and return the filename."""
    if file and file.filename:
        filename = secure_filename(file.filename)  # Ensure filename is safe
        random_filename = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        _, file_extension = os.path.splitext(filename)
        new_filename = random_filename + file_extension
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)
        return new_filename
    return None

@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for('waiting'))
    return redirect(url_for('register'))

# Route for the waiting page
@app.route('/waiting')
def waiting():
    return render_template('waiting.html')

# Route for the registration form
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'email' in session:
        return redirect(url_for('waiting'))
    
    if request.method == 'POST':
        try:
            # Gather form data
            english_name = request.form.get('english_name')
            arabic_name = request.form.get('arabic_name')
            dob_str = request.form.get('dob')
            nationality = request.form.get('nationality')
            phone = request.form.get('phone')
            email = request.form.get('email')
            address = request.form.get('address')
            program = request.form.get('program')

            # Validate form data
            if not all([english_name, arabic_name, dob_str, email, phone, address, program]):
                flash('All fields are required.')
                return redirect(url_for('register'))
            is_valid_email = '@' in email and '.' in email.split('@')[-1]
            if not is_valid_email:
                flash('Invalid email address.')
                return redirect(url_for('register'))
            is_email_exists = Registration.query.filter_by(email=email).first()
            if is_email_exists:
                flash('Email already exists.')
                return redirect(url_for('register'))
            is_phone_exists = Registration.query.filter_by(phone=phone).first()
            if is_phone_exists:
                flash('Phone already exists.')
                return redirect(url_for('register'))
            
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.')
                return redirect(url_for('register'))
            
            identity_document = request.files.get('identity_document')
            degree_document = request.files.get('degree_document')
            additional_document = request.files.get('additional_document')

            if not all([identity_document, degree_document, additional_document]):
                flash('All documents are required.')
                return redirect(url_for('register'))

            # Save files
            identity_document_filename = save_file(identity_document)
            degree_document_filename = save_file(degree_document)
            additional_document_filename = save_file(additional_document)

            if not all([identity_document_filename, degree_document_filename, additional_document_filename]):
                flash('Error saving documents. Please try again.')
                return redirect(url_for('register'))

            # Create new registration
            new_registration = Registration(
                english_name=english_name,
                arabic_name=arabic_name,
                dob=dob,
                nationality=nationality,
                phone=phone,
                email=email,
                address=address,
                program=program,
                identity_document=identity_document_filename,
                degree_document=degree_document_filename,
                additional_document=additional_document_filename
            )
            
            db.session.add(new_registration)
            db.session.commit()
            session['email'] = email
            session['english_name'] = english_name
            return redirect(url_for('waiting'))
        
        except Exception as e:
            flash(f'An error occurred. Please try again.')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('english_name', None)
    return redirect(url_for('register'))
# download
@app.route('/download/<filename>')
def download(filename):
      return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# Admin login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            session['admin'] = 'admin'
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('admin_login'))
    if 'admin' in session:
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/login.html')

# Admin dashboard route within the blueprint
@admin_bp.route('/')
def admin_dashboard():
    if 'admin' in session:
        all_users = Registration.query.all()
        return render_template('admin/index.html', all_users=all_users)
    else:
        pass
# approve
@admin_bp.route('/approve/<int:user_id>')
def approve(user_id):
    if 'admin' in session:
        user = Registration.query.get(user_id)
        user.is_approved = True
        db.session.commit()
        return redirect(url_for('admin.admin_dashboard'))
    else:
        pass
@admin_bp.route('/reject/<int:user_id>')
def reject(user_id):
    if 'admin' in session:
        user = Registration.query.get(user_id)
        user.is_approved = False
        db.session.commit()
        return redirect(url_for('admin.admin_dashboard'))
    else:
        pass
# view_user
@admin_bp.route('/view_user/<int:user_id>')
def view_user(user_id):
    if 'admin' in session:
        user = Registration.query.get(user_id)
        return render_template('admin/view_user.html', user=user)
    else:
        pass
# Register the blueprint
app.register_blueprint(admin_bp, url_prefix='/admin')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
