from flask import Flask, request, session, render_template, redirect, url_for, flash
import pymongo
import json
from bson import ObjectId
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo_url = 'mongodb://localhost:27017'
client = pymongo.MongoClient(mongo_url)
db = client['score']
data_base = db['score_collect']

DATAS = 'user_data.json'
# Helper function to serialize MongoDB ObjectId
def convert_objectid(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
    return data

@app.route('/', methods=['POST', 'GET'])
def home():
    if request.method == 'POST':
        username = request.form.get('user_name')
        password = request.form.get('password')
        # Check if user exists in MongoDB
        existing_user = data_base.find_one({"name": username})
        if existing_user:
            if existing_user['pass'] == password:
                session['logged_in'] = True
                session['user_name'] = username
                return redirect(url_for('result'))
            else:
                return redirect(url_for('home', error="Invalid password,please enter valid password..."))
        else:
            return redirect(url_for('home', error="Invalid username. Please register"))

    return render_template('login.html')

@app.route('/register', methods=['POST', 'GET'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('user_name')
        password = request.form.get('password')
        existing_user = data_base.find_one({"name": username})
        if existing_user:
            return redirect(url_for('home',error="Username already exists. Please login."))
        if not username or not password:
            return render_template('register.html',error="Username and password cannot be empty")
        # Generate a new custom ID for the user
        last_record = data_base.find_one(sort=[('id', -1)])
        new_id = 10001 if last_record is None else last_record['id'] + 1

        values = {
            "id": new_id,
            "name": username,
            "pass": password,
            "score": 500
        }
        data_base.insert_one(values)
        flash("Registration successful. Please login.")
        return redirect(url_for('home'))
    
    return render_template('register.html')

@app.route('/datas', methods=['GET', 'POST'])
def result():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

    username = session.get('user_name')
    user_data = data_base.find_one({"name": username})

    if not user_data:
        return redirect(url_for('home'))
    # Convert ObjectId to string for JSON compatibility
    user_data = convert_objectid(user_data)
    # Update score if the request method is POST
    if request.method == 'POST':
        user_data['score'] *= 2
        
        data_base.update_one({"id": user_data['id']}, {"$set": {"score": user_data['score']}})

        with open(DATAS, 'w') as file:
            json.dump(user_data, file)
    return render_template('score.html', show=user_data)

@app.route('/admin', methods=['POST', 'GET'])
def admin_login():
    admin_base=db['admin_data']
    if request.method == 'POST':
        username = request.form.get('user_name')
        password = request.form.get('password')
        
        existing_admin = admin_base.find_one({"admin_name": username})
        if existing_admin:
            if existing_admin['admin_pass'] == password:
                session['admin_logged_in'] = True
                session['admin_name'] = username
                return redirect(url_for('user_datas'))
            else:
                flash("Invalid password. Please try again.")
        else:
            flash("Invalid username. Please try again or register.")

    return render_template('admin.html')

@app.route('/admin_register', methods=['POST', 'GET'])
def admin_reg():
    admin_base=db['admin_data']
    if request.method == 'POST':
        username = request.form.get('user_name')
        password = request.form.get('password')
    
        existing_admin = admin_base.find_one({"admin_name": username})
        if existing_admin:
            flash("Admin username already exists. Please login.")
            return redirect(url_for('admin_login'))
        if not username or not password:
            return render_template('admin_register.html', error="Username and password cannot be empty")
        # Insert new admin credentials into the database
        admin_data = {
            'admin_name': username,
            'admin_pass': password
        }
        admin_base.insert_one(admin_data)
        flash("Admin registration successful. Please login.")
        return redirect(url_for('admin_login'))

    return render_template('admin_register.html')

@app.route('/database')
def user_datas():
    users = data_base.find()
    return render_template("user_data.html", users=users)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    # Check if the file is part of the request
    if 'pdf_file' not in request.files:
        flash('No file part')
        return redirect(url_for('user_datas'))

    file = request.files['pdf_file']
    # If the user does not select a file, the browser may submit an empty part
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('user_datas'))
    # If a valid file is uploaded, save it
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        flash('File uploaded successfully')
    else:
        flash('Invalid file type. Only PDFs are allowed.')

    return redirect(url_for('user_datas'))


if __name__ =='__main__':
    app.run(debug=True)