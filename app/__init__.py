import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
from flask_mail import Mail, Message
from celery import Celery
from app.recognition import *


app = Flask(__name__)
app.config['SECRET_KEY'] = 'WR#&f&+%78er0we=%799eww+#7^90-;s'
login = LoginManager(app)
login.login_view = 'login'


basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'data', 'uploads')
#sets max bytes for file upload
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 1024  

app.config['MAIL_SERVER'] = 'smtp.outlook.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME']=os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD']=os.environ.get('EMAIL_PASS')
mail = Mail(app)



# config for file upload directory
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/images')
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
    
app.config['AUGMENTED_FOLDER'] = os.path.join(app.root_path, 'static/augmented_images')
if not os.path.exists(app.config['AUGMENTED_FOLDER']):
    os.makedirs(app.config['AUGMENTED_FOLDER'])
    

# images_directory = app.config['AUGMENTED_FOLDER']
# if not model_files_exist():
#     train_model(images_directory)
# model, label_encoder = load_trained_model()





from app import views
from app.models import *

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Teacher=Teacher, Student=Student, LoginManager=LoginManager)