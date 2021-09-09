from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from flask_socketio import SocketIO

# force loading of environment variables
load_dotenv('.flaskenv')

# Get the environment variables from .flaskenv
PASSWORD = os.environ.get('DATABASE_PASSWORD')
USERNAME = os.environ.get('DATABASE_USERNAME')
DB_NAME = os.environ.get('DATABASE_NAME')

app = Flask(__name__)
Bootstrap(app)
login_manager = LoginManager()
app.config['SECRET_KEY'] = 'owlpool'
app.config['SECURITY_PASSWORD_SALT']='my_precious_two'
#app.config['Debug']=False    ###might not need this###
app.config['BCRYPT_LOG_ROUNDS']=13
app.config['WTF_CRSF_ENABLED']=True
app.config['DEBUG_TB_ENABLED']=False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS']=False

# mail Settings
app.config['MAIL_SERVER']='smtp.googlemail.com'
app.config['MAIL_PORT']=465
app.config['MAIL_USE_TLS']=False
app.config['MAIL_USE_SSL']=True

# gmail authentication
app.config['MAIL_USERNAME']='csc330.spring@gmail.com'
app.config['MAIL_PASSWORD']= 'NecroMan93'

#aacount
app.config['MAIL_DEFAULT_SENDER']= 'csc330.spring@gmail.com'

# Add DB config
app.config['SQLALCHEMY_DATABASE_URI'] = ('mysql+pymysql://'
                                        + USERNAME
                                        + ':'
                                        + PASSWORD
                                        + '@sql5.freemysqlhosting.net/'
                                        + DB_NAME)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"]= True
#engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=True)
#if not database_exists(engine.url):
#    create_database(engine.url)

    
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER=os.path.join(APP_ROOT, 'static', 'images')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Create database connection and associate it with the Flask application
db = SQLAlchemy(app)

login = LoginManager(app)
login.login_view ='login'
mail =Mail(app)
from app import routes, models
from app.models import User, Announcement

db.create_all()

admin_check = User.query.filter_by(email='youssef@owl.edu').first()
if admin_check is None:
    admin = User(user_id=1,first_name='Youssef',last_name="Youssef",address='NULL',confirmed=True, user_type='admin',major_id=1,email='youssef@owl.edu',gender='male',active=True)
    admin.set_password('password')
    db.session.add(admin)
    

db.session.commit()
