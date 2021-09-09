from app import db,login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlalchemy

class User (UserMixin, db.Model):
    __tablename__='user'
    user_id = db.Column(db.Integer , primary_key=True)
    first_name =db.Column (db.String (100))
    last_name = db.Column (db.String (100))
    user_type = db.Column (db.String (5),default="user")
    address = db.Column (db.String (150),nullable=True)
    active = db.Column (db.Boolean, default='1')
    email = db.Column (db.String(100), unique=True)
    major_id = db.Column (db.Integer, sqlalchemy.ForeignKey('major.major_id'))
    gender = db.Column (db.String (10))
    confirmed = db.Column(db.Boolean, nullable=False, default=False)
    image = db.Column (db.String (200), nullable=True,default='NULL')
    password_hash = db.Column(db.String(256))
 
    def get_id(self):
        return (self.user_id)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password (self, password):
        return check_password_hash(self.password_hash,password)
   

@login.user_loader
def loader_user(user_id):
        return db.session.query(User).get(int(user_id))

class Ride(db.Model):
    __tablename__='ride'
    ride_id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer,sqlalchemy.ForeignKey('user.user_id'), nullable=False)
    from_location = db.Column(db.String (100))
    to_location = db.Column(db.String (100))
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date= db.Column(db.Date, nullable=False)
    max_passengers= db.Column(db.Integer, nullable=False)
    full = db.Column(db.Boolean, nullable=False,default=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    def validate_passengers(self):
        CurrentNumOfPassengers= db.session.query(Ride_passengers).filter_by(ride_id=self.ride_id).count()
        if self.full:
            return False
        if CurrentNumOfPassengers+1 < self.max_passengers:
            return True
        elif  CurrentNumOfPassengers+1 == self.max_passengers:
            self.full = True
            return True        
                
class Ride_Passengers(db.Model):
    __tablename__='ride_passengers'
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer,sqlalchemy.ForeignKey('ride.ride_id'), nullable=False)
    passenger_id = db.Column(db.Integer,sqlalchemy.ForeignKey('user.user_id'), nullable=False)

class Requests(db.Model):
    __tablename__='requests'
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer,sqlalchemy.ForeignKey('ride.ride_id'), nullable=False)
    requester = db.Column(db.Integer,sqlalchemy.ForeignKey('user.user_id'), nullable=False)

        
class Announcement(db.Model):
    __tablename__='announcement'
    announcement_id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column (db.Integer, sqlalchemy.ForeignKey('user.user_id'))
    description = db.Column (db.String (100))
    flag = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime,nullable=False,default=datetime.now())

class Rating(db.Model):
    __tablename__='rating'
    rating_id = db.Column(db.Integer, primary_key=True)
    writer_id = db.Column (db.Integer, sqlalchemy.ForeignKey('user.user_id'),nullable=False)
    reciver_id = db.Column (db.Integer, sqlalchemy.ForeignKey('user.user_id'),nullable=False)
    description = db.Column(db.String (100))
    stars = db.Column(db.Integer)

class Member(db.Model):
    __tablename__='member'
    group_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, primary_key=True)

class Major (db.Model):

    __tablename__='major'
    major_id = db.Column(db.Integer, primary_key=True)
    major_name = db.Column(db.String (100), unique=True)

class User_Intrest(db.Model):
    __tablename__='user_intrest'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer ,sqlalchemy.ForeignKey('user.user_id'))
    intrest_id = db.Column(db.Integer, sqlalchemy.ForeignKey('intrest.intrest_id'))

class Intrest (db.Model):
    __tablename__='intrest'
    intrest_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

class IntrestGroup(db.Model):
    __tablename__='intrestgroup'
    group_id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(100), unique=True)
    group_name = db.Column(db.String(100), unique=True)

class Post(db.Model):
    __tablename__='post'
    post_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column (db.Integer, sqlalchemy.ForeignKey ('user.user_id'), nullable=False)
    group_id = db.Column(db.Integer, sqlalchemy.ForeignKey ('intrestgroup.group_id'), nullable=False)
    content = db.Column(db.String(100), unique=True)
    timestamp = db.Column(db.DateTime,nullable=False,default=datetime.now())

class Reports (db.Model):
    __tablename__='reports'
    report_id = db.Column(db.Integer, primary_key=True)
    reported_id = db.Column(db.Integer ,sqlalchemy.ForeignKey('user.user_id'))
    reporter_id = db.Column(db.Integer ,sqlalchemy.ForeignKey('user.user_id'))
    description = db.Column(db.String(100))
    status = db.Column(db.Integer)

class Conversations(db.Model):
    __tablename__='conversations'
    conversation_id = db.Column(db.String(100), primary_key=True)
    first_peer = db.Column (db.Integer, sqlalchemy.ForeignKey ('user.user_id'), nullable=False)
    second_peer= db.Column (db.Integer, sqlalchemy.ForeignKey ('user.user_id'), nullable=False)
    def __init__(self, conversation_id, first_peer, second_peer):
        self.conversation_id = conversation_id
        self.first_peer = first_peer
        self.second_peer = second_peer

class Messages(db.Model):
    __tablename__='messages'
    message_id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.String(100),sqlalchemy.ForeignKey('conversations.conversation_id'))
    sender_id = db.Column (db.Integer, sqlalchemy.ForeignKey ('user.user_id'), nullable=False)
    message = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime,nullable=False,default=datetime.now())
    
