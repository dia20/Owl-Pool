from app import app
from flask import render_template, redirect, url_for, flash,request,session
from flask_login import login_user, logout_user, login_required, current_user, LoginManager
from app.forms import RegistrationForm,  LoginForm,BanForm,AddAnnouncement, SchedulerForm,ChangePasswordForm,EditProfileForm,FilterForm
from app.email import send_email
from app.token import generate_confirmation_token, confirm_token
from app import db
from sqlalchemy import update, func,or_, and_
from werkzeug.utils import secure_filename
from werkzeug import *
from app.models import User, Major, User_Intrest, Rating, Intrest,Reports,Announcement, Requests, Ride, Ride_Passengers,Messages,Conversations
import sys 
import os
import json
import hashlib
from sqlalchemy_filters import apply_filters
import pdb, pprint
from flask_socketio import SocketIO

@app.route('/', methods=['GET','POST'])
def index():
    if session.get('alert'):
        alert = session['alert']
        session.pop('alert',None)
    else:
        alert = None
    all_ann = db.session.query(Announcement).order_by(Announcement.timestamp.desc()).all()
    form = AddAnnouncement()
    if current_user and not current_user.is_anonymous:
        user = current_user
    else: 
        user = ''
    if is_admin():
         if form.validate_on_submit():
             desc = form.description.data
             flag = form.flag.data
             ann = Announcement(admin_id='1',description= desc, flag = flag)
             db.session.add(ann)
             db.session.commit()
             form.description.data=''
             form.flag.data = ''
             session['alert']= 'Announcement Added!'
             return redirect(url_for('index'))
    return render_template('index.html',user=user, announcements = all_ann, form=form, isAdmin= is_admin(),alert=alert)
    
 
def is_admin():

    if current_user.is_anonymous:
        return False;
        
    elif  current_user.user_type == "admin":
            return True;
    else: 
        return False;



@app.route('/login', methods=['GET', 'POST'])
def login():

    # Authenticated users are redirected to home page.
    if current_user.is_authenticated and current_user.confirmed:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        # Query DB for user by username
        user = db.session.query(User).filter_by(email=form.email.data).first()
        if user is None:
            return render_template('login.html', form=form, user_not_found=True) 
        if user.active:
            if user.check_password(form.password.data):
                if user.confirmed:
                    login_user(user)
                    session['alert']= 'Welcome '+user.first_name
                    if  request.args:
                        if request.args['next']:
                            next_url = request.args['next']
                            return redirect(next_url)
                    return redirect(url_for('index'))
                else:
                    login_user(user)
                    return render_template('unconfirmed.html', user=user)
            else:
                return render_template('login.html', form=form, wrong_pass=True)    
        else:
            return render_template('login.html', form=form, not_active=True) 
    return render_template('login.html', form=form)
    

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/sign_up', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        firstname = form.first_name.data
        lastname = form.last_name.data
        if form.clean_email() == False:
            return render_template('register.html', title='SignUp', form=form, email_format=True)
        else:
            email = form.clean_email()
        address = form.address.data
        gender = form.gender.data
        major_id= form.major_id.data
        filename = False
        confirmed=False
        image = request.files['image']
        if form.password.data != form.password2.data:
            return render_template('register.html', title='SignUp', form=form, invalid_password=True)
        if image.filename != '':
            filename = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                 
        if  form.validate_email(email)== False:
            return render_template('register.html', title='SignUp', form=form, user_exists=True)
        
        # Create a  record to store in the DB
        if filename is not False:
            u = User(first_name=firstname, last_name=lastname,email=email,image=image.filename,address=address,gender=gender,major_id=major_id,active=True,user_type='user' ,confirmed=confirmed)
            u.set_password(form.password.data)
            image.save(filename)
        else:
            u = User(first_name=firstname, last_name=lastname,email=email,image='',address=address,gender=gender,major_id=major_id,active=True,user_type='user',confirmed=False )

            u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()

        SendToken(u.email)
        return redirect(url_for('login'))
    return render_template('register.html', title='SignUp', form=form)


@app.route('/dn/<ann_id>')
@login_required
def delete_announcement(ann_id):
    if not is_admin():
        return redirect(url_for('index'))
    ann=Announcement.query.filter_by(announcement_id=ann_id).first()
    db.session.delete(ann)
    db.session.commit()
    session['alert']='Announcement Deleted!'
    return redirect(url_for('index'))
        
@app.route('/Send_Token/<email>')
@login_required
def send_token(email):
    if email is not None:
        SendToken(email)
        return render_template('unconfirmed.html', user=current_user)
    else:
        return redirect(url_for('index'))
    
def Notifications(email,message):
    try:
        html=render_template('Notifications.html',message=message )
        subject= "OWLPOOL NOTIFICATION"
        send_email(email, subject, html)
        session['alert']= "Email Sent"
    except:
        session['alert']= "Email not Sent"
        return False
    return True

@app.route('/uploads/<filename>')
def send_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
        
@app.route('/confirm')
@app.route('/confirm/<token>')
@login_required
def confirm_email(token):
    if token is None:
        return redirect(url_for('logout'))
    try:
        email = confirm_token(token)
    except:
        return redirect(url_for('logout'))
    
    user = db.session.query(User).filter_by(email = email).first()
    user.confirmed = True
    db.session.add(user)
    db.session.commit()
    Notifications(user.email,"Thank You For Signing up to OWLPOOL. We Wish You have a safe Journey.")
    return redirect(url_for('index'))

@app.route('/profile', defaults={'user_id' : None})
@app.route('/profile/<user_id>')
def viewprofile(user_id):
    if user_id is None and current_user.is_anonymous:
        return redirect(url_for('index'))
        
    if user_id is None:
        user_profile=user =db.session.query(User).filter_by(user_id=current_user.user_id).first()

    elif user_id is not None and current_user.is_anonymous:
        user_profile =db.session.query(User).filter_by(user_id=user_id).first()
        if user_profile.active == False:
             return (redirect(url_for('index')))
        user = None
    else:
        user_profile = db.session.query(User).filter_by(user_id=user_id).first()
        if user_profile.active == False:
            return (redirect(url_for('index')))
        user = db.session.query(User).filter_by(user_id=current_user.user_id).first()
        
    if current_user.is_authenticated and user_id is None:
            featuresShow = True
    elif  current_user.is_authenticated and user_id is not None and user_id == current_user.user_id:
            featuresShow = True 
    else:
            featuresShow = False
    if user is not None:
        tmp_interests_ids = db.session.query(User_Intrest.intrest_id).filter_by(user_id=user_id).all()
        interests_ids = []
        for intr in tmp_interests_ids:
                    interests_ids.append(intr.intrest_id)

        interestNames = db.session.query(Intrest.name).filter(Intrest.intrest_id.in_(interests_ids)).all()
        major = db.session.query(Major).filter_by(major_id=user.major_id).first() 
        ratings = db.session.query(Rating).filter_by(reciver_id = user.user_id).all()

        driver_history = db.session.query(Ride).filter_by(driver_id=user.user_id). \
            filter_by(completed = True).all()
        passenger_history = db.session.query(Ride, Ride_Passengers).filter_by(completed = True). \
            join(Ride_Passengers).filter_by(passenger_id=user.user_id).all()
        
        driver_active = db.session.query(Ride).filter_by(driver_id=user.user_id). \
            filter_by(completed = False).all()
        passenger_active = db.session.query(Ride, Ride_Passengers).filter_by(completed = False). \
            join(Ride_Passengers).filter_by(passenger_id=user.user_id).all()
        
                #need to know the number of rows of passengers for a given ride

        ids = db.session.query(Ride.ride_id).filter_by(driver_id=current_user.user_id).all()
        list1 = []
        for x in ids:
            list1.append(x.ride_id)
        request_join = db.session.query(User, Requests, Ride).select_from(User). \
                join(Requests, User.user_id == Requests.requester).join(Ride, Requests.ride_id == Ride.ride_id). \
                    filter(Requests.ride_id.in_(list1)).all()
        
        #request_join = db.session.query(User,Ride,Requests).select_from(User).join(Ride).join(Requests). \
         #   filter(Ride.driver_id == current_user.user_id).all()
        request_sent = db.session.query(User,Ride,Requests).select_from(User).join(Ride).join(Requests). \
            filter(Requests.requester == current_user.user_id).all()

        # query may not be  correct
        total=0
        for rating in ratings:
            total += rating.stars
        if total >0:
            overall = total /len(ratings)
        else:
            overall = "."
        return render_template('profilepage.html',isAdmin = is_admin(),isMyProfile=featuresShow,user=user,user_profile=user_profile,rating=overall,major=major,interests=interestNames, \
            driver_history=driver_history, passenger_history=passenger_history, driver_active=driver_active, passenger_active=passenger_active, \
                request_join=request_join, request_sent=request_sent)
    else:
        return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    if current_user is None:
        return redirect(url_for('login'));  
    if   not current_user.is_authenticated:
        return redirect(url_for('login'));  
    if not is_admin():
        return render_template('login.html');     
    return render_template('admin.html',user=current_user)



@app.route('/scheduler', methods=['GET','POST'])
@login_required 
def scheduler():
    if current_user.is_anonymous:
        return redirect(url_for('login'))
        
    form = SchedulerForm()
    time_error =  date_error = False
    if  form.validate_on_submit():
        from_location = form.from_location.data
        to_location = form.to_location.data
        start_time = form.start_time.data.strftime('%H:%M:%S')
        end_time = form.end_time.data.strftime('%H:%M:%S')
        start_date = form.start_date.data
        end_date = form.end_date.data
        max_passengers = form.max_passengers.data
        if start_date == end_date :
            if start_time >  end_time :
                 time_error = True
        if start_date > end_date :
           date_error = True

        if time_error or date_error:
             return render_template ('scheduler.html' ,form=form, time_error=time_error, date_error=date_error)
        ride = Ride(driver_id=current_user.user_id,from_location=from_location,to_location=to_location,start_time=start_time,end_time=end_time, start_date=start_date, end_date=end_date, max_passengers=max_passengers)
        db.session.add(ride)
        db.session.commit()
        Notifications(current_user.email,"Your Ride has been scheduled. We Wish You have a safe Journey.") 
        return redirect(url_for('index'))
    return render_template ('scheduler.html' ,form=form, time_error=time_error, date_error=date_error)

@app.route('/reports')
@login_required
def reports():
    records = db.session.query(Reports).filter_by(status=1).all()
        
    return render_template('reports.html',isAdmin = is_admin(),user=current_user, reports=records)


@app.route('/banuser/<reported_id>', methods=['GET','POST'])
@login_required
def ban(reported_id):
    if reported_id is not None: 
        stmt =update(User).values(active=(False)).where(User.user_id == reported_id)
        stmt1= Reports.__table__.delete().where(Reports.reported_id==reported_id)
        db.session.execute(stmt)
        db.session.execute(stmt1)
        db.session.commit()
        return redirect(url_for('reports'))
    return redirect(url_for('banwithid'))      


@app.route('/banuser',methods=['GET','POST'])
@login_required
def banwithid():
        form = BanForm()
        if form.validate_on_submit():
            user_to_ban = db.session.query(User).filter_by(user_id = form.user_id.data).first()
            if user_to_ban:
                stmt =update(User).values(active=(False)).where(User.user_id == form.user_id.data)
                db.session.execute(stmt)
                db.session.commit()
                Notifications(user_to_ban.email,"Your Account has been BANNED. Please Speak with an administrator.")
                form.user_id.data=''
                return redirect(url_for('banwithid'))
            else:
                return render_template('ban.html',isAdmin = is_admin(),user=current_user,form = form, notFound=True)
        return render_template('ban.html',isAdmin = is_admin(),user=current_user, form = form)

@app.route('/rides', methods=["GET","POST"])
@login_required
def ridebrowser():
    if not current_user.is_anonymous:
        user = current_user
    else:
        redirect(url_for('login'))
    # we need rides list called : rides 
    # we need number of reuests each ride has: num_of_requests
    # we need first and last name and image of each the driver as a list: drivers
    form = FilterForm()
    filled=[]
    if request.method=="POST":
        for val in request.form :
            if val == "major_id" and request.form.get(val) is None:
                break
            elif request.form.get(val) != '':
                filled.append(val)
                
    print(filled, file=sys.stderr)
    rides = db.session.query(Ride,User,Major)\
                            .select_from(Ride).join(User).join(Major).filter(Ride.driver_id != user.user_id).\
                                filter(Ride.completed==False).order_by(Ride.start_date.desc())   
   
    filter_spec =[]
    if filled:
        del filled[0]
        del filled[len(filled)-1]
        for att in filled:
            if att == "major_id":
                filter_spec.append({'model':'Major','field':att,'op':'==','value':request.form.get(att)}) 
            else:       
                filter_spec.append({'model':'Ride','field':att,'op':'==','value':request.form.get(att)})    
        rides = apply_filters(rides,filter_spec)

    rides = rides.all()
    
    num_of_passengers = db.session.query(Ride_Passengers.ride_id, func.count(Ride_Passengers.ride_id).label('count')).group_by(Ride_Passengers.ride_id).all()


  #  drivers_ids =[]
  #  for ride in rides:
  #      drivers_ids.append(ride.driver_id)
  #  drivers = db.session.query(User.user_id,User.first_name, User.last_name, User.image,Major.major_name).join(Major).filter(User.user_id.in_(drivers_ids))
  #  if filter_spec1:
  #      drivers= apply_filters(drivers,filter_spec1).all()
  #  else:
  #      drivers= drivers.all() 
    
    return render_template('rides.html',form=form,user=user, rides = rides, num_of_passengers = num_of_passengers)

@app.route('/join/<ride_id>', methods=['GET','POST'])
@login_required
def joinride(ride_id):
    if ride_id is None or ride_id=='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))
        
    request = Requests(ride_id=ride_id, requester=current_user.user_id)
    db.session.add(request)
    db.session.commit()

    # Notifications([0],"You have a ride Request.")
    return redirect(url_for('viewprofile'))

@app.route('/edit_profile',methods=['GET', 'POST'])
@login_required
def editprofile():
    user = current_user
    form=EditProfileForm(major_id=user.major_id)
    if form.validate_on_submit():
        address = form.address.data
        major_id= form.major_id.data
        filename = False
        image = request.files['image']
        if image.filename != '':
            filename= os.path.join(app.config['UPLOAD_FOLDER'],image.filename)
        if filename is not False: 
            user.image = image.filename
            image.save(filename)
        user.major_id = major_id 
        user.address = address
        db.session.commit()
        session['alert']="Profile Updated!"
        return redirect(url_for('viewprofile'))
    return render_template('editprofile.html', form=form, user=user,user_profile=user)


@app.route('/change_password',methods=['GET', 'POST'])
@login_required
def change_password():
    user=current_user
    form= ChangePasswordForm()
    if form.validate_on_submit():
        old_password = form.current_password.data
        new_password = form.password.data
        confirm_password = form.password2.data
        if user.check_password(old_password):
            if new_password == confirm_password:
                user.set_password(new_password)
                db.session.commit()
                Notifications(user.email,"Your password has beenc changed. If this was not you please contact our administrators immediately.")
                session['alert']="Password Changed!"
                return redirect(url_for('index'))
            else:
               return render_template('changepassword.html', form=form, pass_not_match=True, user=user) 
        else:
            return render_template('changepassword.html', form=form, invalid_pass=True, user=user) 

    return render_template('changepassword.html', form=form, user=user) 


def SendToken(email):
    try:
        token = generate_confirmation_token(email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html = render_template('confirmationtest.html', confirm_url=confirm_url)
        subject = "Please confirm your email"
        send_email(email, subject, html)
        session['alert']= "Confirmation Email Sent. Check your email."
        return True
    except:
        session['alert']= "Confirmation Email NOT Sent. Check with your administrator."
        return False

@app.route('/accept_request/<ride_id>/<requester>', methods=['GET', 'POST']) # delete field in requests table, add to passenger table
@login_required
def acceptride(ride_id, requester):
    if ride_id is None or ride_id=='':
        if requester is None or requester=='':
            return redirect(url_for('index'))
    elif ride_id is not None and requester is None or requester =='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))

    request_delete = db.session.query(Requests).filter_by(ride_id=ride_id).filter_by(requester=requester).first()

    if request_delete:
        db.session.delete(request_delete)
        db.session.commit()

        new = Ride_Passengers(ride_id=ride_id, passenger_id=requester)
        db.session.add(new)
        db.session.commit()
        requestermail = db.session.query(User.email).filter_by(user_id=requester).first()
        Notifications(requestermail[0],"Your Ride request has been accepted.")

    else:
        return redirect(url_for('viewprofile'))
    return redirect('profilepage.html#Requests')

@app.route('/reject_request/<ride_id>/<requester>', methods=['GET', 'POST']) # delete field in requests table only
@login_required
def rejectride(ride_id, requester):
    if ride_id is None or ride_id=='':
        if requester is None or requester=='':
            return redirect(url_for('index'))
    elif ride_id is not None and requester is None or requester =='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))

    request_delete = db.session.query(Requests).filter_by(ride_id=ride_id).filter_by(requester=requester).first()

    if request_delete:
        db.session.delete(request_delete)
        db.session.commit()
        requestermail = db.session.query(User.email).filter_by(user_id=requester).first()
        Notifications(requestermail[0],"Your Ride request has been rejected.")

    else:
        return redirect(url_for('viewprofile'))
    return redirect('profilepage.html#Requests')   



    
@app.route('/cancel_driver/<ride_id>', methods=['GET', 'POST'])
@login_required
def cancelride(ride_id): # may need another field in ride called "canceled"
    if ride_id is None or ride_id=='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))
        
    selected_ride = db.session.query(Ride).filter_by(ride_id=ride_id). \
        filter_by(driver_id=current_user.user_id).first() #checks if being called by driver of ride
    
    if selected_ride:

        del_pas = db.session.query(Ride_Passengers).filter_by(ride_id=ride_id).all()
        del_requests = db.session.query(Requests).filter_by(ride_id=ride_id).all()
        if del_pas:
            for p in del_pas:
                db.session.delete(p)
                db.session.commit() # deletes all records of passengers for ride.
            
        if del_requests:
            for r in del_requests:
                db.session.delete(r)
                db.session.commit()
        
        db.session.delete(selected_ride)
        db.session.commit() # delete all records of requests for ride.
        passenger= db.session.query(Ride_Passengers.passenger_id).filter_by(ride_id=ride_id).first()
        passengermail = db.session.query(User.email).filter_by(user_id=passenger).first()
        Notifications(passengermail,"This Ride has been canceled")

        
        

    else:
        return redirect(url_for('viewprofile')) # user cant del record if not driver
    return redirect('profilepage.html#Rides')

@app.route('/cancel_passenger/<ride_id>')
@login_required
def cancelride2(ride_id):
    if ride_id is None or ride_id=='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))
        
    selected_ride = db.session.query(Ride_Passengers).filter_by(ride_id=ride_id). \
        filter_by(passenger_id=current_user.user_id).first()

    if selected_ride:
    
        db.session.delete(selected_ride)
        db.session.commit()
        driver = db.session.query(Ride.driver_id).filter_by(ride_id=ride_id).first()
        drivermail = db.session.query(User.email).filter_by(user_id=driver[0]).first()
        Notifications(drivermail[0],print(current_user.email) +" "+ " has canceled their ride.")

    else:
        return redirect(url_for('viewprofile')) # user cant del record if not a passenger
    return redirect('profilepage.html#Rides')

@app.route('/change_status/<ride_id>', methods=['GET', 'POST'])
@login_required
def changestatus(ride_id):
    if ride_id is None or ride_id=='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))    

    selected_ride = db.session.query(Ride).filter_by(ride_id=ride_id). \
        filter_by(driver_id=current_user.user_id).first()
    del_requests = db.session.query(Requests).filter_by(ride_id=ride_id).all()

    if selected_ride:
        selected_ride.completed = True
        db.session.commit()

        if del_requests:
            for r in del_requests:
                db.session.delete(r)
                db.session.commit()

    else:
        return redirect(url_for('viewprofile'))
    return redirect('profilepage.html#Rides')

socketio = SocketIO(app)

@app.route('/launch/<peer_id>')
@login_required
def launch_session(peer_id):
    if peer_id is None or peer_id=='':
        return redirect(url_for('viewprofile'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))
    conv_id = get_or_add_conversation(str(current_user.user_id),peer_id)
    socketio.run(app, debug=True)
    return redirect(url_for('sessions',conversation_id=conv_id))

@app.route('/launch/')
@app.route('/inbox/')
@login_required
def returntohome():
    return redirect(url_for('index'))
                
@app.route('/inbox/<conversation_id>', methods=['POST','GET'])
@login_required
def sessions(conversation_id):
    if conversation_id is None or conversation_id =='':
            return redirect(url_for('viewprofile'))
    elif current_user.is_anonymous:
            return redirect(url_for('login'))
    check_conv = db.session.query(Conversations).filter_by(conversation_id=conversation_id).first()
    if(check_conv is None):
            return redirect(url_for('viewprofile'))
    else:
        sender_id = ''
        
        if check_conv.first_peer == current_user.user_id:
            sender_id = check_conv.second_peer
        else: 
            sender_id = check_conv.first_peer
        print(sender_id, file=sys.stderr)  
        sender = db.session.query(User.first_name, User.image).filter_by(user_id = sender_id).first()
    prev_msgs = db.session.query(User.first_name.label('sender'),\
                                 Messages.message,Messages.timestamp,Messages.sender_id).select_from(Messages).\
                                 join(User).filter(Messages.conversation_id==conversation_id).\
                                 order_by(Messages.timestamp.asc()).all()
    print("sender:", file=sys.stderr)  
    print(sender.first_name, file=sys.stderr)  

    return render_template('session.html', user=current_user,peer=sender, prev_msgs = prev_msgs,conversation_id=conversation_id)

@socketio.on('my event')
def handle_my_custom_event(Myjson, methods=['GET', 'POST']):   
    new_message = Messages(conversation_id = Myjson['conv_id'],\
                             sender_id = Myjson['sender'] ,\
                             message= Myjson['message'] ,\
                             timestamp=Myjson['msg_time'])
    db.session.add(new_message)
    db.session.commit()
    socketio.emit('my response', Myjson)



def get_or_add_conversation(sender,receiver):
    conv_id = db.session.query(Conversations.conversation_id).\
                filter(or_(and_(Conversations.first_peer == receiver, Conversations.second_peer == sender),\
                 and_(Conversations.first_peer == sender, Conversations.second_peer == receiver))).first()
    if conv_id is None:
        conv_id = generate_conversation_id(sender,receiver)
        new_conv = Conversations(conv_id,sender,receiver)
        db.session.add(new_conv)
        db.session.commit()
        return conv_id
    else:
        return conv_id[0]             



def generate_conversation_id(sender,receiver):
    m = hashlib.sha256()
    combination = sender + receiver
    m.update(str.encode(combination))
    return str(m.hexdigest())


@app.route('/rate/<driver_id>/<stars>', methods=['GET', 'POST'])
@login_required
def rate(driver_id,stars):
    if driver_id is None or driver_id=='':
        return redirect(url_for('index'))
    elif current_user.is_anonymous:
        return redirect(url_for('login'))

    driver_to_be_rated = db.session.query(User.user_id).filter_by(user_id = driver_id).first()
    if driver_to_be_rated is not None: 
        rating = Rating(writer_id = current_user.user_id, reciver_id=driver_id , description= '',stars=stars)
        db.session.add(rating)
        db.session.commit()
        session['alert']='Thanks for rating your driver!'
        return redirect(url_for('index'))
    else:   
        return redirect(url_for('index'))


      
