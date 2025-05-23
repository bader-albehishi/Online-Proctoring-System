from flask import Flask, request, render_template, flash, redirect, url_for,session, logging, send_file, jsonify, Response, render_template_string
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, DateTimeField, BooleanField, IntegerField, DecimalField, HiddenField, SelectField, RadioField
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_mail import Mail, Message
from functools import wraps
from werkzeug.utils import secure_filename
from coolname import generate_slug
from datetime import timedelta, datetime
from objective import ObjectiveTest
from subjective import SubjectiveTest
from deepface import DeepFace
import pandas as pd
import operator
import functools
import math, random 
import csv
import cv2
import numpy as np
import json
import base64
from wtforms_components import TimeField
from wtforms.fields import DateField
from wtforms.validators import ValidationError, NumberRange
from flask_session import Session
from flask_cors import CORS, cross_origin
import camera
import os
import mysql.connector
from pydub import AudioSegment
from pydub.silence import split_on_silence
import time
import speech_recognition as sr
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import join_room, leave_room, send, SocketIO
from string import ascii_uppercase

app = Flask(__name__)
socketio =SocketIO(app)
db = SQLAlchemy(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'quizapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.config["SECRET_KEY"] = "lkajdhsk"
# Mail configs
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = 'vawjazbfnmegjxhz'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['SESSION_COOKIE_SAMESITE'] = "None"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
# Session configs
app.config['SESSION_TYPE'] = 'filesystem'
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SESSION_COOKIE_SECURE']=True




mail = Mail(app)

sess = Session()
sess.init_app(app)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

app.secret_key= 'engageProject'

mysql = MySQL(app)


sender = ''

YOUR_DOMAIN = 'http://localhost:5000'


@app.before_request
def make_session_permanent():
	session.permanent = True

def user_role_professor(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			if session['user_role']=="teacher":
				return f(*args, **kwargs)
			else:
				flash('ليس لديك صلاحية الوصول إلى هذه الصفحة!','danger')
				return render_template("404.html") 
		else:
			flash('غير مصرح ، الرجاء تسجيل الدخول!','danger')
			return redirect(url_for('login'))
	return wrap

def user_role_student(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			if session['user_role']=="student":
				return f(*args, **kwargs)
			else:
				flash('ليس لديك صلاحية الوصول إلى هذه الصفحة!','danger')
				return render_template("404.html") 
		else:
			flash('غير مصرح ، الرجاء تسجيل الدخول !','danger')
			return redirect(url_for('login'))
	return wrap


@app.route('/window_event', methods=['GET','POST'])
@user_role_student
def window_event():
	if request.method == "POST":
		testid = request.form['testid']
		cur = mysql.connection.cursor()
		results = cur.execute('INSERT INTO window_estimation_log (email, test_id, name, window_event, uid) values(%s,%s,%s,%s,%s)', (dict(session)['email'], testid, dict(session)['name'], 1, dict(session)['uid']))
		mysql.connection.commit()
		cur.close()
		if(results > 0):
			return "recorded window"
		else:
			return "error in window"


###########################################################################

rooms = {}

def generate_unique_code(Length):
    while True:
        code = ""
        for _ in range(Length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code

@app.route("/home", methods = ["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error = "Please enter a name.", code = code, name =  name)

        if join != False and not code:
            return render_template("home.html", error = "Please enter a room code.", code = code, name =  name)

        room = code
        if create != False:
            room =  generate_unique_code(4)
            rooms[room] = {"members" : 0, "messages" : []}
        elif code not in rooms:
            return render_template("home.html", error = "Room does not exist.", code = code, name =  name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    room = session.get("room")
    name = session.get("name")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    
    return render_template("room.html", code = room, messages = rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name" : session.get("name"),
        "message" : data["data"]
    }
    send(content, to = room)
    rooms[room]["message"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name" : name, "message": "has entered the room"}, to = room)
    rooms[room]["members"] +=1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -=1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name" : name, "message": "has left the room"}, to = room)
    print(f"{name} has left the room {room}")
        






@app.route('/video_feed', methods=['GET', 'POST'])
@user_role_student
def video_feed():
    if request.method == "POST":		
        imgData = request.form['data[imgData]']
        testid = request.form['data[testid]']
        
        proctorData = camera.get_frame(imgData)
        jpg_as_text = proctorData['jpg_as_text']
        mob_status = proctorData['mob_status']
        person_status = proctorData['person_status']
        user_move1 = proctorData['user_move1']
        user_move2 = proctorData['user_move2']
        eye_movements = proctorData['eye_movements']
        cur = mysql.connection.cursor()
        results = cur.execute('INSERT INTO proctoring_log (email, name, test_id, img_log, user_movements_updown, user_movements_lr, user_movements_eyes, phone_detection, person_status, uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (dict(session)['email'], dict(session)['name'], testid,  jpg_as_text, user_move1, user_move2, eye_movements, mob_status, person_status, dict(session)['uid']))
        mysql.connection.commit()
        cur.close() 
        # Saving to voice_exam table     
        if results > 0:
            return "recorded image of video"
        else:
            return "error in video"
		

@app.route('/video_feeds', methods=['GET', 'POST'])
@user_role_student
def video_feeds():
    if request.method == "POST":		
        imgData = request.form['data[imgData]']
        testid = request.form['data[testid]']
        
        proctorData = camera.get_frame(imgData)
        jpg_as_text = proctorData['jpg_as_text']
        
        person_status = proctorData['person_status']
        
        
        cur = mysql.connection.cursor()
        results = cur.execute('INSERT INTO proctoring_logs (email, name, test_id, img_log, person_status, uid) values(%s,%s,%s,%s,%s,%s)', (dict(session)['email'], dict(session)['name'], testid,  jpg_as_text, person_status, dict(session)['uid']))
        mysql.connection.commit()
        cur.close() 
        # Saving to voice_exam table     
        if results > 0:
            return "recorded image of video"
        else:
            return "error in video"



SUSPICIOUS_WORDS = [
    "الإجابة", 
    "الحل", 
    "شوف", 
    "ساعدني", 
    "ما الجواب", 
    "كيف أحل", 
    "قلي",
    "أنا عالق",
    "عندي صعوبة",
    "ابعتلي",
    "هل هذا صحيح",
    "ماذا أفعل",
    "أعطني",
	"بسرعة",
	"السؤال",
	"ما سمعت",
	" قوي صوتك",
	
    "سريع"
]

def audio_to_text(filepath):
    r = sr.Recognizer()
    with sr.AudioFile(filepath) as source:
        audio_data = r.listen(source)
        try:
            text = r.recognize_google(audio_data, language="ar-SY")
            return text
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the audio")
        except sr.RequestError:
            print("Google Speech Recognition API unavailable")
    return ""

@app.route('/upload', methods=['GET','POST'])
@user_role_student
def upload():
	if request.method == "POST":
		testid = request.form['testid']
		file = request.files['file']
		filename = str(int(time.time())) + '.wav'
		filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
		file.save(filepath)
		
		cur = mysql.connection.cursor()
		cur.execute("INSERT INTO voice_student (email, test_id, name, filename, filepath, uid) VALUES (%s, %s, %s, %s, %s, %s)" ,(dict(session)['email'], testid, dict(session)['name'], filename, 'static/uploads/' + filename, dict(session)['uid']))
		vid = cur.lastrowid
		session['vid'] = vid
		mysql.connection.commit()
		cur.close()
		sound = AudioSegment.from_file(filepath)
		audio_chunks = split_on_silence(sound, min_silence_len=500, silence_thresh=-40)
		
		MIN_CHUNK_LENGTH = 500  # الحد الأدنى لمدة القطعة بالميلي ثانية
		filtered_audio_chunks = [chunk for chunk in audio_chunks if len(chunk) > MIN_CHUNK_LENGTH]

		print(f"Number of audio chunks extracted: {len(filtered_audio_chunks)}")  # طباعة عدد القطع المحصلة

		LOUDNESS_THRESHOLD = -50  # مستوى الصوت الحد الأدنى

		for i, chunk in enumerate(filtered_audio_chunks):
			# فحص مستوى الصوت للقطعة
			if chunk.dBFS < LOUDNESS_THRESHOLD:
				continue
			
			chunk_filename = f"{filename}_chunk{i}.wav"
			chunk_filepath = os.path.join(app.config['UPLOAD_FOLDER'], chunk_filename)
			chunk.export(chunk_filepath, format="wav")
			chunk_text = audio_to_text(chunk_filepath)
			is_important = any(word in chunk_text for word in SUSPICIOUS_WORDS)
			cur = mysql.connection.cursor()
			print(chunk_filename, 'static/uploads/' + chunk_filename, dict(session)['vid'])

			results =cur.execute("INSERT INTO voice_student_short (filename, filepath, vid, is_important) VALUES (%s, %s, %s , %s)" ,(chunk_filename,  'static/uploads/' + chunk_filename,  session['vid'],is_important))
			mysql.connection.commit()
			cur.close()
		if(results > 0):
			return "recorded window"
		else:
			return "error in window"




@app.route("/livemonitoringtid")
@user_role_professor
def livemonitoringtid():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s and proctoring_type = 1', (session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['start']),"%Y-%m-%d %H:%M:%S") <= now and datetime.strptime(str(a['end']),"%Y-%m-%d %H:%M:%S") >= now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("livemonitoringtid.html", cresults = testids)
	else:
		return render_template("livemonitoringtid.html", cresults = None)

@app.route('/live_monitoring', methods=['GET','POST'])
@user_role_professor
def live_monitoring():
	if request.method == 'POST':
		testid = request.form['choosetid']
		return render_template('live_monitoring.html',testid = testid)
	else:
		return render_template('live_monitoring.html',testid = None)	


@app.route('/')
def index():
	return render_template('index.html')

@app.errorhandler(404) 
def not_found(e):
	return render_template("404.html") 

@app.errorhandler(500)
def internal_error(error):
	return render_template("500.html") 

@app.route('/calc')
def calc():
	return render_template('calc.html')

@app.route('/report_professor')
@user_role_professor
def report_professor():
	return render_template('report_professor.html')

@app.route('/student_index')
@user_role_student
def student_index():
	return render_template('student_index.html')

@app.route('/professor_index')
@user_role_professor
def professor_index():
	return render_template('professor_index.html')

@app.route('/faq')
def faq():
	return render_template('faq.html')

@app.route('/report_student')
@user_role_student
def report_student():
	return render_template('report_student.html')

@app.route('/report_professor_email', methods=['GET','POST'])
@user_role_professor
def report_professor_email():
	if request.method == 'POST':
		careEmail = ""
		cname = session['name']
		cemail = session['email']
		ptype = request.form['prob_type']
		cquery = request.form['rquery']
		msg1 = Message('PROBLEM REPORTED', sender = sender, recipients = [careEmail])
		msg1.body = " ".join(["NAME:", cname, "PROBLEM TYPE:", ptype ,"EMAIL:", cemail, "", "QUERY:", cquery]) 
		mail.send(msg1)
		flash('Your Problem has been recorded.', 'success')
	return render_template('report_professor.html')

@app.route('/report_student_email', methods=['GET','POST'])
@user_role_student
def report_student_email():
	if request.method == 'POST':
		careEmail = ""
		cname = session['name']
		cemail = session['email']
		ptype = request.form['prob_type']
		cquery = request.form['rquery']
		msg1 = Message('PROBLEM REPORTED', sender = sender, recipients = [careEmail])
		msg1.body = " ".join(["NAME:", cname, "PROBLEM TYPE:", ptype ,"EMAIL:", cemail, "", "QUERY:", cquery]) 
		mail.send(msg1)
		flash('Your Problem has been recorded.', 'success')
	return render_template('report_student.html')

@app.route('/contact', methods=['GET','POST'])
def contact():
	if request.method == 'POST':
		careEmail = ""
		cname = request.form['cname']
		cemail = request.form['cemail']
		cquery = request.form['cquery']
		msg1 = Message('Hello', sender = sender, recipients = [cemail])
		msg2 = Message('Hello', sender = sender, recipients = [careEmail])
		msg1.body = "YOUR QUERY WILL BE PROCESSED! WITHIN 24 HOURS"
		msg2 = Message('Hello', sender = sender, recipients = [careEmail])
		msg2.body = " ".join(["NAME:", cname, "EMAIL:", cemail, "QUERY:", cquery]) 
		mail.send(msg1)
		mail.send(msg2)
		flash('Your Query has been recorded.', 'success')
	return render_template('contact.html')

@app.route('/lostpassword', methods=['GET','POST'])
def lostpassword():
	if request.method == 'POST':
		lpemail = request.form['lpemail']
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT * from users where email = %s' , [lpemail])
		if results > 0:
			sesOTPfp = generateOTP()
			session['tempOTPfp'] = sesOTPfp
			session['seslpemail'] = lpemail
			msg1 = Message('MyProctor.ai - OTP Verification for Lost Password', sender = sender, recipients = [lpemail])
			msg1.body = "Your OTP Verfication code for reset password is "+sesOTPfp+"."
			mail.send(msg1)
			return redirect(url_for('verifyOTPfp')) 
		else:
			return render_template('lostpassword.html',error="Account not found.")
	return render_template('lostpassword.html')

@app.route('/verifyOTPfp', methods=['GET','POST'])
def verifyOTPfp():
	if request.method == 'POST':
		fpOTP = request.form['fpotp']
		fpsOTP = session['tempOTPfp']
		if(fpOTP == fpsOTP):
			return redirect(url_for('lpnewpwd')) 
	return render_template('verifyOTPfp.html')

@app.route('/lpnewpwd', methods=['GET','POST'])
def lpnewpwd():
	if request.method == 'POST':
		npwd = request.form['npwd']
		cpwd = request.form['cpwd']
		slpemail = session['seslpemail']
		if(npwd == cpwd ):
			cur = mysql.connection.cursor()
			cur.execute('UPDATE users set password = %s where email = %s', (npwd, slpemail))
			mysql.connection.commit()
			cur.close()
			session.clear()
			return render_template('login.html',success="Your password was successfully changed.")
		else:
			return render_template('login.html',error="Password doesn't matched.")
	return render_template('lpnewpwd.html')

@app.route('/generate_test')
@user_role_professor
def generate_test():
	return render_template('generatetest.html')

@app.route('/changepassword_professor')
@user_role_professor
def changepassword_professor():
	return render_template('changepassword_professor.html')

@app.route('/changepassword_student')
@user_role_student
def changepassword_student():
	return render_template('changepassword_student.html')

def generateOTP() : 
    digits = "0123456789"
    OTP = "" 
    for i in range(5) : 
        OTP += digits[math.floor(random.random() * 10)] 
    return OTP 

@app.route('/register', methods=['GET','POST'])
def register():
	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		password = request.form['password']
		user_type = request.form['user_type']
		imgdata = request.form['image_hidden']
		session['tempName'] = name
		session['tempEmail'] = email
		session['tempPassword'] = password
		session['tempUT'] = user_type
		session['tempImage'] = imgdata
		sesOTP = generateOTP()
		session['tempOTP'] = sesOTP
		msg1 = Message('إرسال بريد إلكتروني THE DIGITAL MONITOR - التحقق من OTP', sender = sender, recipients = [email])
		msg1.body = "فتح حساب جديد - رمز التحقق لمرة واحدة (OTP) الخاص بك هو "+sesOTP+"."
		mail.send(msg1)
		return redirect(url_for('verifyEmail')) 
	return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		email = request.form['email']
		password_candidate = request.form['password']
		user_type = request.form['user_type']
		imgdata1 = request.form['image_hidden']
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT uid, name, email, password, user_type, user_image from users where email = %s and user_type = %s and user_login = 0' , (email,user_type))
		if results1 > 0:
			cresults = cur.fetchone()
			imgdata2 = cresults['user_image']
			password = cresults['password']
			name = cresults['name']
			uid = cresults['uid']
			nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8) #فك تشفير الصورة المُرسلة.
			nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
			image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
			image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)
			img_result  = DeepFace.verify(image1, image2, enforce_detection = False)
			if img_result["verified"] == True and password == password_candidate:
				results2 = cur.execute('UPDATE users set user_login = 1 where email = %s' , [email])
				mysql.connection.commit()
				if results2 > 0:
					session['logged_in'] = True
					session['email'] = email
					session['name'] = name
					session['user_role'] = user_type
					session['uid'] = uid
					if user_type == "student":
						return redirect(url_for('student_index'))
					else:
						return redirect(url_for('professor_index'))
				else:
					error = 'Error Occurred!'
					return render_template('login.html', error=error)	
			else:
				error = 'إما أن الصورة لم تتم التحقق منها أو أدخلت كلمة مرور غير صحيحة أو تم تسجيل الدخول بالفعل'
				return render_template('login.html', error=error)
			cur.close()
		else:
			error = 'تم تسجيل الدخول بالفعل أو البريد الإلكتروني لم يتم العثور عليه'
			return render_template('login.html', error=error)
	return render_template('login.html')

@app.route('/verifyEmail', methods=['GET','POST'])
def verifyEmail():
	if request.method == 'POST':
		theOTP = request.form['eotp']
		mOTP = session['tempOTP']
		dbName = session['tempName']
		dbEmail = session['tempEmail']
		dbPassword = session['tempPassword']
		dbUser_type = session['tempUT']
		dbImgdata = session['tempImage']
		if(theOTP == mOTP):
			cur = mysql.connection.cursor()
			ar = cur.execute('INSERT INTO users(name, email, password, user_type, user_image, user_login) values(%s,%s,%s,%s,%s,%s)', (dbName, dbEmail, dbPassword, dbUser_type, dbImgdata,0))
			mysql.connection.commit()
			if ar > 0:
				flash("شكرا  ! تم التحقق منك بنجاح !.")
				return  redirect(url_for('login'))
			else:
				flash("Error Occurred!")
				return  redirect(url_for('login')) 
			cur.close()
			session.clear()
		else:
			return render_template('register.html',error="OTP غير صحيح.")
	return render_template('verifyEmail.html')

@app.route('/changepassword', methods=["GET", "POST"])
def changePassword():
	if request.method == "POST":
		oldPassword = request.form['oldpassword']
		newPassword = request.form['newpassword']
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT * from users where email = %s and uid = %s', (session['email'], session['uid']))
		if results > 0:
			data = cur.fetchone()
			password = data['password']
			usertype = data['user_type']
			if(password == oldPassword):
				cur.execute("UPDATE users SET password = %s WHERE email = %s", (newPassword, session['email']))
				mysql.connection.commit()
				msg="تم التغيير بنجاح"
				flash('Changed successfully.', 'success')
				cur.close()
				if usertype == "student":
					return render_template("student_index.html", success=msg)
				else:
					return render_template("professor_index.html", success=msg)
			else:
				error = "كلمة مرور خاطئة"
				if usertype == "student":
					return render_template("student_index.html", error=error)
				else:
					return render_template("professor_index.html", error=error)
		else:
			return redirect(url_for('/'))

@app.route('/logout', methods=["GET", "POST"])
def logout():
	cur = mysql.connection.cursor()
	lbr = cur.execute('UPDATE users set user_login = 0 where email = %s and uid = %s',(session['email'],session['uid']))
	mysql.connection.commit()
	if lbr > 0:
		session.clear()
		return "success"
	else:
		return "error"

def examcreditscheck():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT examcredits from users where examcredits >= 1 and email = %s and uid = %s', (session['email'], session['uid']))
	if results > 0:
		return True

class QAUploadForm(FlaskForm):
	subject = StringField('الكورس')
	topic = StringField('العنوان')
	doc = FileField('تحميل csv', validators=[FileRequired()])
	start_date = DateField('تاريخ البدء')
	start_time = TimeField('وقت البدء', default=datetime.utcnow()+timedelta(hours=5.5))
	end_date = DateField('تاريخ الانتهاء')
	end_time = TimeField('وقت النهاية', default=datetime.utcnow()+timedelta(hours=5.5))
	duration = IntegerField('المدة (بالدقائق)')
	password = PasswordField('كلمة مرور الاختبار', [validators.Length(min=3, max=6)])
	proctor_type = RadioField('نوع المراقبة', choices=[('0','المراقبة الآلية'),('1','المراقبة المباشرة')])

	def validate_end_date(form, field):
		if field.data < form.start_date.data:
			raise ValidationError("End date must not be earlier than start date.")
	
	def validate_end_time(form, field):
		start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		end_date_time = datetime.strptime(str(form.end_date.data) + " " + str(field.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		if start_date_time >= end_date_time:
			raise ValidationError("End date time must not be earlier/equal than start date time")
	
	def validate_start_date(form, field):
		if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S") < datetime.now():
			raise ValidationError("Start date and time must not be earlier than current")

@app.route('/create_test_lqa', methods = ['GET', 'POST'])
@user_role_professor
def create_test_lqa():
	form = QAUploadForm()
	if request.method == 'POST' and form.validate_on_submit():
		test_id = generate_slug(2)
		filename = secure_filename(form.doc.data.filename)
		filestream = form.doc.data
		filestream.seek(0)
		ef = pd.read_csv(filestream)
		fields = ['qid','q','marks']
		df = pd.DataFrame(ef, columns = fields)
		cur = mysql.connection.cursor()
		ecc = examcreditscheck()
		if ecc:
			for row in df.index:
				cur.execute('INSERT INTO longqa(test_id,qid,q,marks,uid) values(%s,%s,%s,%s,%s)', (test_id, df['qid'][row], df['q'][row], df['marks'][row], session['uid']))
				cur.connection.commit()
				
			start_date = form.start_date.data
			end_date = form.end_date.data
			start_time = form.start_time.data
			end_time = form.end_time.data
			start_date_time = str(start_date) + " " + str(start_time)
			end_date_time = str(end_date) + " " + str(end_time)
			duration = int(form.duration.data)*60
			password = form.password.data
			subject = form.subject.data
			topic = form.topic.data
			proctor_type = form.proctor_type.data
			cur.execute('INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic, calc, proctoring_type, uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
				(dict(session)['email'], test_id, "subjective", start_date_time, end_date_time, duration, 0, password, subject, topic,  0, proctor_type, session['uid']))
			mysql.connection.commit()
			cur.execute('UPDATE users SET examcredits = examcredits-1 where email = %s and uid = %s', (session['email'],session['uid']))
			mysql.connection.commit()
			cur.close()
			flash(f'معرف الاختبار : {test_id}', 'success')
			return redirect(url_for('professor_index'))
		else:
			flash("لقد انتهى رصيدك من نقاط الامتحان يرجى تجديد الباقة")
			return redirect(url_for('professor_index'))
	return render_template('create_test_lqa.html' , form = form)

class UploadForm(FlaskForm):
	subject = StringField('الكورس')
	topic = StringField('العنوان')
	doc = FileField('تحميل csv', validators=[FileRequired()])
	start_date = DateField('تاريخ البدء')
	start_time = TimeField('وقت البدء', default=datetime.utcnow()+timedelta(hours=5.5))
	end_date = DateField('تاريخ الانتهاء')
	end_time = TimeField('وقت الانتهاء', default=datetime.utcnow()+timedelta(hours=5.5))
	calc = BooleanField('السماح بالآلة الحاسبة')
	
	duration = IntegerField('المدة (دقيقة)')
	password = PasswordField('كلمة مرور الاختبار', [validators.Length(min=3, max=6)])
	proctor_type = RadioField('نوع المراقبة', choices=[('0','المراقبة الآلية'),('1','المراقبة المباشرة')])

	def validate_end_date(form, field):
		if field.data < form.start_date.data:
			raise ValidationError("End date must not be earlier than start date.")
	
	def validate_end_time(form, field):
		start_date_time = datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		end_date_time = datetime.strptime(str(form.end_date.data) + " " + str(field.data),"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M")
		if start_date_time >= end_date_time:
			raise ValidationError("End date time must not be earlier/equal than start date time")
	
	def validate_start_date(form, field):
		if datetime.strptime(str(form.start_date.data) + " " + str(form.start_time.data),"%Y-%m-%d %H:%M:%S") < datetime.now():
			raise ValidationError("Start date and time must not be earlier than current")

class TestForm(Form):
	test_id = StringField('معرف الاختبار')
	password = PasswordField('كلمة المرور')
	img_hidden_form = HiddenField(label=(''))

@app.route('/create-test', methods = ['GET', 'POST'])
@user_role_professor
def create_test():
	form = UploadForm()
	if request.method == 'POST' and form.validate_on_submit():
		test_id = generate_slug(2)
		filename = secure_filename(form.doc.data.filename)
		filestream = form.doc.data
		filestream.seek(0)
		ef = pd.read_csv(filestream)
		fields = ['qid','q','a','b','c','d','ans','marks']
		df = pd.DataFrame(ef, columns = fields)
		cur = mysql.connection.cursor()
		ecc = examcreditscheck()
		if ecc:
			for row in df.index:
				cur.execute('INSERT INTO questions(test_id,qid,q,a,b,c,d,ans,marks,uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', (test_id, df['qid'][row], df['q'][row], df['a'][row], df['b'][row], df['c'][row], df['d'][row], df['ans'][row], df['marks'][row], session['uid']))
				cur.connection.commit()

			start_date = form.start_date.data
			end_date = form.end_date.data
			start_time = form.start_time.data
			end_time = form.end_time.data
			start_date_time = str(start_date) + " " + str(start_time)
			end_date_time = str(end_date) + " " + str(end_time)
		
			calc = int(form.calc.data)
			duration = int(form.duration.data)*60
			password = form.password.data
			subject = form.subject.data
			topic = form.topic.data
			proctor_type = form.proctor_type.data
			cur.execute('INSERT INTO teachers (email, test_id, test_type, start, end, duration, show_ans, password, subject, topic,  calc,proctoring_type, uid) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
				(dict(session)['email'], test_id, "objective", start_date_time, end_date_time, duration, 1, password, subject, topic,calc, proctor_type, session['uid']))
			mysql.connection.commit()
			cur.execute('UPDATE users SET examcredits = examcredits-1 where email = %s and uid = %s', (session['email'],session['uid']))
			mysql.connection.commit()
			cur.close()
			flash(f'معرف الاختبار :  {test_id}', 'success')
			return redirect(url_for('professor_index'))
		else:
			flash("لقد انتهى رصيدك من نقاط الامتحان يرجى تجديد الباقة")
			return redirect(url_for('professor_index'))
	return render_template('create_test.html' , form = form)



@app.route('/deltidlist', methods=['GET'])
@user_role_professor
def deltidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['start']),"%Y-%m-%d %H:%M:%S") > now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("deltidlist.html", cresults = testids)
	else:
		return render_template("deltidlist.html", cresults = None)

@app.route('/deldispques', methods=['GET','POST'])
@user_role_professor
def deldispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispques.html", callresults = callresults, tid = tidoption)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("deldispquesLQA.html", callresults = callresults, tid = tidoption)

		else:
			flash("Some Error Occured!")
			return redirect(url_for('/deltidlist'))

@app.route('/delete_questions/<testid>', methods=['GET', 'POST'])
@user_role_professor
def delete_questions(testid):
	et = examtypecheck(testid)
	if et['test_type'] == "objective":
		cur = mysql.connection.cursor()
		msg = '' 
		if request.method == 'POST':
			testqdel = request.json['qids']
			if testqdel:
				if ',' in testqdel:
					testqdel = testqdel.split(',')
					for getid in testqdel:
						cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,getid,session['uid']))
						mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
				else:
					cur.execute('DELETE FROM questions WHERE test_id = %s and qid =%s and uid = %s', (testid,testqdel,session['uid']))
					mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
	elif et['test_type'] == "subjective":
		cur = mysql.connection.cursor()
		msg = '' 
		if request.method == 'POST':
			testqdel = request.json['qids']
			if testqdel:
				if ',' in testqdel:
					testqdel = testqdel.split(',')
					for getid in testqdel:
						cur.execute('DELETE FROM longqa WHERE test_id = %s and qid =%s and uid = %s', (testid,getid,session['uid']))
						mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
				else:
					cur.execute('DELETE FROM longqa WHERE test_id = %s and qid =%s and uid = %s', (testid,testqdel,session['uid']))
					mysql.connection.commit()
					resp = jsonify('<span style=\'color:green;\'>Questions deleted successfully</span>')
					resp.status_code = 200
					return resp
	else:
		flash("Some Error Occured!")
		return redirect(url_for('/deltidlist'))

@app.route('/<testid>/<qid>')
@user_role_professor
def del_qid(testid, qid):
	cur = mysql.connection.cursor()
	results = cur.execute('DELETE FROM questions where test_id = %s and qid = %s and uid = %s', (testid,qid,session['uid']))
	mysql.connection.commit()
	if results>0:
		msg="Deleted successfully"
		flash('Deleted successfully.', 'success')
		cur.close()
		return render_template("deldispques.html", success=msg)
	else:
		return redirect(url_for('/deldispques'))

@app.route('/updatetidlist', methods=['GET'])
@user_role_professor
def updatetidlist():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where email = %s and uid = %s', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['start']),"%Y-%m-%d %H:%M:%S") > now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("updatetidlist.html", cresults = testids)
	else:
		return render_template("updatetidlist.html", cresults = None)

@app.route('/updatedispques', methods=['GET','POST'])
@user_role_professor
def updatedispques():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("updatedispques.html", callresults = callresults)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("updatedispquesLQA.html", callresults = callresults)
		elif et['test_type'] == "practical":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from practicalqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("updatedispquesPQA.html", callresults = callresults)
		else:
			flash('Error Occured!')
			return redirect(url_for('updatetidlist'))

@app.route('/update/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_quiz(testid, qid):
	if request.method == 'GET':
		cur = mysql.connection.cursor()
		cur.execute('SELECT * FROM questions where test_id = %s and qid =%s and uid = %s', (testid,qid,session['uid']))
		uresults = cur.fetchall()
		mysql.connection.commit()
		return render_template("updateQuestions.html", uresults=uresults)
	if request.method == 'POST':
		ques = request.form['ques']
		ao = request.form['ao']
		bo = request.form['bo']
		co = request.form['co']
		do = request.form['do']
		anso = request.form['anso']
		markso = request.form['mko']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE questions SET q = %s, a = %s, b = %s, c = %s, d = %s, ans = %s, marks = %s where test_id = %s and qid = %s and uid = %s', (ques,ao,bo,co,do,anso,markso,testid,qid,session['uid']))
		cur.connection.commit()
		flash('Updated successfully.', 'success')
		cur.close()
		return redirect(url_for('updatetidlist'))
	else:
		flash('ERROR  OCCURED.', 'error')
		return redirect(url_for('updatetidlist'))

@app.route('/updateLQA/<testid>/<qid>', methods=['GET','POST'])
@user_role_professor
def update_lqa(testid, qid):
	if request.method == 'GET':
		cur = mysql.connection.cursor()
		cur.execute('SELECT * FROM longqa where test_id = %s and qid =%s and uid = %s', (testid,qid,session['uid']))
		uresults = cur.fetchall()
		mysql.connection.commit()
		return render_template("updateQuestionsLQA.html", uresults=uresults)
	if request.method == 'POST':
		ques = request.form['ques']
		markso = request.form['mko']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE longqa SET q = %s, marks = %s where test_id = %s and qid = %s and uid = %s', (ques,markso,testid,qid,session['uid']))
		cur.connection.commit()
		flash('Updated successfully.', 'success')
		cur.close()
		return redirect(url_for('updatetidlist'))
	else:
		flash('ERROR  OCCURED.', 'error')
		return redirect(url_for('updatetidlist'))


@app.route('/viewquestions', methods=['GET'])
@user_role_professor
def viewquestions():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("viewquestions.html", cresults = cresults)
	else:
		return render_template("viewquestions.html", cresults = None)

def examtypecheck(tidoption):
	cur = mysql.connection.cursor()
	cur.execute('SELECT test_type from teachers where test_id = %s and email = %s and uid = %s', (tidoption,session['email'],session['uid']))
	callresults = cur.fetchone()
	cur.close()
	return callresults

@app.route('/displayquestions', methods=['GET','POST'])
@user_role_professor
def displayquestions():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "objective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from questions where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			return render_template("displayquestions.html", callresults = callresults)
		elif et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT * from longqa where test_id = %s and uid = %s', (tidoption,session['uid']))
			callresults = cur.fetchall()
			cur.close()
			
			return render_template("displayquestionslong.html", callresults = callresults)
		
		
@app.route('/test_status', methods=[ 'GET'])
@user_role_professor
def test_status():
    
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s', (session['email'],session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("test_status.html", cresults = cresults)
	else:
		return render_template("test_status.html", cresults = None)

	
@app.route('/displayquestionssssss', methods=['GET','POST'])
@user_role_professor
def displayquestionssssss():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		
		
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT test_id, time_left ,completed,email FROM studenttestinfo WHERE test_id = %s', (tidoption,))

		callresults = cur.fetchall()
		cur.close()
		print(callresults,"vffdvfdvfdvdfvfdvfdvdfvdfvfdvfdv")
		return render_template("displayquestionssssss.html", callresults = callresults)
			
	

	
@app.route('/viewstudentslogs', methods=['GET'])
@user_role_professor
def viewstudentslogs():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT test_id from teachers where email = %s and uid = %s and proctoring_type = 0', (session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		cur.close()
		return render_template("viewstudentslogs.html", cresults = cresults)
	else:
		return render_template("viewstudentslogs.html", cresults = None)

@app.route('/insertmarkstid', methods=['GET'])
@user_role_professor
def insertmarkstid():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where show_ans = 0 and email = %s and uid = %s and (test_type = %s or test_type = %s)', (session['email'], session['uid'],"subjective","practical"))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['end']),"%Y-%m-%d %H:%M:%S") < now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("insertmarkstid.html", cresults = testids)
	else:
		return render_template("insertmarkstid.html", cresults = None)

@app.route('/displaystudentsdetails', methods=['GET','POST'])
@user_role_professor
def displaystudentsdetails():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT DISTINCT email,test_id from proctoring_log where test_id = %s', [tidoption])
		callresults = cur.fetchall()
		cur.close()
		return render_template("displaystudentsdetails.html", callresults = callresults)

@app.route('/insertmarksdetails', methods=['GET','POST'])
@user_role_professor
def insertmarksdetails():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT DISTINCT email,test_id from longtest where test_id = %s', [tidoption])
			callresults = cur.fetchall()
			cur.close()
			return render_template("subdispstudentsdetails.html", callresults = callresults)
		else:
			flash("Some Error was occured!",'error')
			return redirect(url_for('insertmarkstid'))

@app.route('/insertsubmarks/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def insertsubmarks(testid,email):
	if request.method == "GET":
		cur = mysql.connection.cursor()
		cur.execute('SELECT l.email as email, l.marks as inputmarks, l.test_id as test_id, l.qid as qid, l.ans as ans, lqa.marks as marks, l.uid as uid, lqa.q as q  from longtest l, longqa lqa where l.test_id = %s and l.email = %s and l.test_id = lqa.test_id and l.qid = lqa.qid ORDER BY qid ASC', (testid, email))
		callresults = cur.fetchall()
		cur.close()
		return render_template("insertsubmarks.html", callresults = callresults)
	if request.method == "POST":
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT COUNT(qid) from longtest where test_id = %s and email = %s',(testid, email))
		results1 = cur.fetchone()
		cur.close()
		for sa in range(1,results1['COUNT(qid)']+1):
			marksByProfessor = request.form[str(sa)]
			cur = mysql.connection.cursor()
			cur.execute('UPDATE longtest SET marks = %s WHERE test_id = %s and email = %s and qid = %s', (marksByProfessor, testid, email, sa))
			mysql.connection.commit()
		cur.close()
		flash('تم ادخال العلامات بنجاح!', 'success')
		return redirect(url_for('insertmarkstid'))

@app.route('/insertpracmarks/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def insertpracmarks(testid,email):
	if request.method == "GET":
		cur = mysql.connection.cursor()
		cur.execute('SELECT l.email as email, l.marks as inputmarks, l.test_id as test_id, l.qid as qid, l.code as code, l.input as input, l.executed as executed, lqa.marks as marks, l.uid as uid, lqa.q as q  from practicaltest l, practicalqa lqa where l.test_id = %s and l.email = %s and l.test_id = lqa.test_id and l.qid = lqa.qid ORDER BY qid ASC', (testid, email))
		callresults = cur.fetchall()
		cur.close()
		return render_template("insertpracmarks.html", callresults = callresults)
	if request.method == "POST":
		cur = mysql.connection.cursor()
		results1 = cur.execute('SELECT COUNT(qid) from practicaltest where test_id = %s and email = %s',(testid, email))
		results1 = cur.fetchone()
		cur.close()
		for sa in range(1,results1['COUNT(qid)']+1):
			marksByProfessor = request.form[str(sa)]
			cur = mysql.connection.cursor()
			cur.execute('UPDATE practicaltest SET marks = %s WHERE test_id = %s and email = %s and qid = %s', (marksByProfessor, testid, email, sa))
			mysql.connection.commit()
		cur.close()
		flash('Marks Entered Sucessfully!', 'success')
		return redirect(url_for('insertmarkstid'))

def displaywinstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return callresults

@app.route("/window_log1")
@user_role_professor
def window_log1():
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM window_log')
    callresults = cursor.fetchall()
    cursor.close()

    return render_template('window_log1.html', callresults=callresults)

def countwinstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as wincount from window_estimation_log where test_id = %s and email = %s and window_event = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	winc = [i['wincount'] for i in callresults]
	return winc

def countMobStudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as mobcount from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	mobc = [i['mobcount'] for i in callresults]
	return mobc

def countMTOPstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as percount from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	perc = [i['percount'] for i in callresults]
	return perc

def countMTOPstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as percount from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	perc = [i['percount'] for i in callresults]
	return perc

def countTotalstudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT COUNT(*) as total from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	tot = [i['total'] for i in callresults]
	return tot

@app.route('/studentmonitoringstats/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def studentmonitoringstats(testid,email):
	return render_template("stat_student_monitoring.html", testid = testid, email = email)



@app.route('/ajaxstudentmonitoringstats/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def ajaxstudentmonitoringstats(testid,email):
	win = countwinstudentslogs(testid,email)
	mob = countMobStudentslogs(testid,email)
	per = countMTOPstudentslogs(testid,email)
	tot = countTotalstudentslogs(testid,email)
	return jsonify({"win":win,"mob":mob,"per":per,"tot":tot})


@app.route('/displaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def displaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("displaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/mobdisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def mobdisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s and phone_detection = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("mobdisplaystudentslogs.html", testid = testid, email = email, callresults = callresults)

@app.route('/persondisplaystudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def persondisplaystudentslogs(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_log where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("persondisplaystudentslogs.html",testid = testid, email = email, callresults = callresults)

@app.route('/persondisplaystudentslogsroom/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def persondisplaystudentslogsroom(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from proctoring_logs where test_id = %s and email = %s and person_status = 1', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("persondisplaystudentslogsroom.html",testid = testid, email = email, callresults = callresults)


@app.route('/audiodisplaystudentslogs/<testid>/<email>', methods=['GET', 'POST'])
@user_role_professor
def audiodisplaystudentslogs(testid, email):
    cur = mysql.connection.cursor()
    
    query = """
    SELECT vss.filename, vss.filepath , vss.is_important, vs.email, vs.test_id 
    FROM voice_student_short vss
    JOIN voice_student vs ON vss.vid = vs.vid
    WHERE vs.test_id = %s AND vs.email = %s
    """
    
    cur.execute(query, (testid, email))
    callresults = cur.fetchall()
    cur.close()
    
    return render_template("audiodisplaystudentslogs.html", testid=testid, email=email, callresults=callresults)




@app.route('/wineventstudentslogs/<testid>/<email>', methods=['GET','POST'])
@user_role_professor
def wineventstudentslogs(testid,email):
    callresults = displaywinstudentslogs(testid,email)

    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM window_log')
    window_log_results = cursor.fetchall()
    cursor.close()

    # قائمة لتخزين البيانات المعدلة
    modified_window_log_results = []

    for row in window_log_results:
    # تحقق من وجود الفاصلة قبل القيام بالتقسيم
     if '-' in row['window_name']:
        # تقسيم قيمة العمود "WINDOW NAME" باستخدام الفاصلة "-"
        values = row['window_name'].split('-', 1)

        # القيمة الأولى
        value1 = values[0]

        # القيمة الثانية
        value2 = values[1]

        # إنشاء قاموس يحتوي على القيم المعدلة
        modified_row = {
            'value1': value1,
            'value2': value2,
            'copied_text': row['copied_text'],
            'event_date': row['event_date'] 
        }

        modified_window_log_results.append(modified_row)
    else:
        # في حالة عدم وجود فاصلة في القيمة
        # يمكنك اتخاذ إجراء مناسب هنا
        pass

        # تقسيم قيمة العامود "WINDOW NAME" باستخدام الفاصلة "-"
        values = row['window_name'].split('-')

        # القيمة الأولى
        value1 = values[0]

        # القيمة الثانية
        value2 = values[1]

        # إنشاء قاموس يحتوي على القيم المعدلة
        modified_row = {
            'value1': value1,
            'value2': value2,
            'copied_text': row['copied_text']  # يمكنك إضافة المزيد من العواميد إذا كان لديك
        }

        modified_window_log_results.append(modified_row)

    return render_template("wineventstudentlog.html", window_log_results=modified_window_log_results, testid=testid, email=email, callresults=callresults)






@app.route('/<email>/<testid>/share_details', methods=['GET','POST'])
@user_role_professor
def share_details(testid,email):
	cur = mysql.connection.cursor()
	cur.execute('SELECT * from teachers where test_id = %s and email = %s', (testid, email))
	callresults = cur.fetchall()
	cur.close()
	return render_template("share_details.html", callresults = callresults)

@app.route('/share_details_emails', methods=['GET','POST'])
@user_role_professor
def share_details_emails():
	if request.method == 'POST':
		tid = request.form['tid']
		subject = request.form['subject']
		topic = request.form['topic']
		duration = request.form['duration']
		start = request.form['start']
		end = request.form['end']
		password = request.form['password']
		
		calc = request.form['calc']
		emailssharelist = request.form['emailssharelist']
		msg1 = Message('EXAM DETAILS - MyProctor.ai', sender = sender, recipients = [emailssharelist])
		msg1.body = " ".join(["EXAM-ID:", tid, "SUBJECT:", subject, "TOPIC:", topic, "DURATION:", duration, "START", start, "END", end, "PASSWORD", password, "CALCULATOR ALLOWED:",calc ]) 
		mail.send(msg1)
		flash('Emails sended sucessfully!', 'success')
	return render_template('share_details.html')

@app.route("/publish-results-testid", methods=['GET','POST'])
@user_role_professor
def publish_results_testid():
	cur = mysql.connection.cursor()
	results = cur.execute('SELECT * from teachers where test_type != %s AND show_ans = 0 AND email = %s AND uid = %s', ("objectve", session['email'], session['uid']))
	if results > 0:
		cresults = cur.fetchall()
		now = datetime.now()
		now = now.strftime("%Y-%m-%d %H:%M:%S")
		now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
		testids = []
		for a in cresults:
			if datetime.strptime(str(a['end']),"%Y-%m-%d %H:%M:%S") < now:
				testids.append(a['test_id'])
		cur.close()
		return render_template("publish_results_testid.html", cresults = testids)
	else:
		return render_template("publish_results_testid.html", cresults = None)

@app.route('/viewresults', methods=['GET','POST'])
@user_role_professor
def viewresults():
	if request.method == 'POST':
		tidoption = request.form['choosetid']
		et = examtypecheck(tidoption)
		if et['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			cur.execute('SELECT SUM(marks) as marks, email from longtest where test_id = %s group by email', ([tidoption]))
			callresults = cur.fetchall()
			cur.close()
			return render_template("publish_viewresults.html", callresults = callresults, tid = tidoption)

		else:
			flash("Some Error Occured!")
			return redirect(url_for('publish-results-testid'))

@app.route('/publish_results', methods=['GET','POST'])
@user_role_professor
def publish_results():
	if request.method == 'POST':
		tidoption = request.form['testidsp']
		cur = mysql.connection.cursor()
		cur.execute('UPDATE teachers set show_ans = 1 where test_id = %s', ([tidoption]))
		mysql.connection.commit()
		cur.close()
		flash("Results published sucessfully!")
		return redirect(url_for('professor_index'))

@app.route('/test_update_time', methods=['GET','POST'])
@user_role_student
def test_update_time():
	if request.method == 'POST':
		cur = mysql.connection.cursor()
		time_left = request.form['time']
		testid = request.form['testid']
		cur.execute('UPDATE studentTestInfo set time_left=SEC_TO_TIME(%s) where test_id = %s and email = %s and uid = %s and completed=0', (time_left, testid, session['email'], session['uid']))
		mysql.connection.commit()
		t1 = cur.rowcount
		cur.close()
		if t1 > 0:
			return "time recorded updated"
		else:
			cur = mysql.connection.cursor()
			cur.execute('INSERT into studentTestInfo (email, test_id,time_left,uid) values(%s,%s,SEC_TO_TIME(%s),%s)', (session['email'], testid, time_left, session['uid']))
			t2 = mysql.connection.commit()
			t2 = cur.rowcount
			cur.close()
			if t2 > 0:
				return "time recorded inserted"
			else:
				return "time error"

@app.route("/give-test", methods = ['GET', 'POST'])
@user_role_student
def give_test():
	global duration, marked_ans, calc, subject, topic, proctortype
	form = TestForm(request.form)
	if request.method == 'POST' and form.validate():
		test_id = form.test_id.data
		password_candidate = form.password.data
		imgdata1 = form.img_hidden_form.data
		cur1 = mysql.connection.cursor()
		results1 = cur1.execute('SELECT user_image from users where email = %s and user_type = %s ', (session['email'],'student'))
		if results1 > 0:
			cresults = cur1.fetchone()
			imgdata2 = cresults['user_image']
			cur1.close()
			nparr1 = np.frombuffer(base64.b64decode(imgdata1), np.uint8)
			nparr2 = np.frombuffer(base64.b64decode(imgdata2), np.uint8)
			image1 = cv2.imdecode(nparr1, cv2.COLOR_BGR2GRAY)
			image2 = cv2.imdecode(nparr2, cv2.COLOR_BGR2GRAY)
			img_result  = DeepFace.verify(image1, image2, enforce_detection = False)
			if img_result["verified"] == True:
				cur = mysql.connection.cursor()
				results = cur.execute('SELECT * from teachers where test_id = %s', [test_id])
				if results > 0:
					data = cur.fetchone()
					password = data['password']
					duration = data['duration']
					calc = data['calc']
					subject = data['subject']
					topic = data['topic']
					start = data['start']
					start = str(start)
					end = data['end']
					end = str(end)
					proctortype = data['proctoring_type']
					if password == password_candidate:
						now = datetime.now()
						now = now.strftime("%Y-%m-%d %H:%M:%S")
						now = datetime.strptime(now,"%Y-%m-%d %H:%M:%S")
						if datetime.strptime(start,"%Y-%m-%d %H:%M:%S") < now and datetime.strptime(end,"%Y-%m-%d %H:%M:%S") > now:
							results = cur.execute('SELECT time_to_sec(time_left) as time_left,completed from studentTestInfo where email = %s and test_id = %s', (session['email'], test_id))
							if results > 0:
								results = cur.fetchone()
								is_completed = results['completed']
								if is_completed == 0:
									time_left = results['time_left']
									if time_left <= duration:
										duration = time_left
										results = cur.execute('SELECT qid , ans from students where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
										marked_ans = {}
										if results > 0:
											results = cur.fetchall()
											for row in results:
												print(row['qid'])
												qiddb = ""+row['qid']
												print(qiddb)
												marked_ans[qiddb] = row['ans']
												marked_ans = json.dumps(marked_ans)
								else:
									flash('Exam already given', 'success')
									return redirect(url_for('give_test'))
							else:
								cur.execute('INSERT into studentTestInfo (email, test_id,time_left,uid) values(%s,%s,SEC_TO_TIME(%s),%s)', (session['email'], test_id, duration, session['uid']))
								mysql.connection.commit()
								results = cur.execute('SELECT time_to_sec(time_left) as time_left,completed from studentTestInfo where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
								if results > 0:
									results = cur.fetchone()
									is_completed = results['completed']
									if is_completed == 0:
										time_left = results['time_left']
										if time_left <= duration:
											duration = time_left
											results = cur.execute('SELECT * from students where email = %s and test_id = %s and uid = %s', (session['email'], test_id, session['uid']))
											marked_ans = {}
											if results > 0:
												results = cur.fetchall()
												for row in results:
													marked_ans[row['qid']] = row['ans']
												marked_ans = json.dumps(marked_ans)
						else:
							if datetime.strptime(start,"%Y-%m-%d %H:%M:%S") > now:
								flash(f'Exam start time is {start}', 'danger')
							else:
								flash(f'Exam has ended', 'danger')
							return redirect(url_for('give_test'))
						return redirect(url_for('test' , testid = test_id))
					else:
						flash('Invalid password', 'danger')
						return redirect(url_for('give_test'))
				flash('معرف اختبار غير صالح', 'danger')
				return redirect(url_for('give_test'))
				cur.close()
			else:
				flash('لم يتم التحقق من الصورة', 'danger')
				return redirect(url_for('give_test'))
	return render_template('give_test.html', form = form)
is_tracking = False
@app.route('/give-test/<testid>', methods=['GET','POST'])
@user_role_student
def test(testid):
	cur = mysql.connection.cursor()
	cur.execute('SELECT test_type from teachers where test_id = %s ', [testid])
	callresults = cur.fetchone()
	session['test_id'] = testid
	cur.close()
	if callresults['test_type'] == "objective":
		global duration, marked_ans, calc, subject, topic, proctortype
		if request.method == 'GET':
			try:
				data = {'duration': duration, 'marks': '', 'q': '', 'a': '', 'b':'','c':'','d':'' }
				
				# هنا نضيف جزء الكود المتعلق بالتتبع
				global is_tracking
				is_tracking = True
				tracking_script = '''
				<script>
					window.addEventListener('beforeunload', function(event) {
						fetch('/stop_tracking', {
							method: 'POST',
							headers: {
								'Accept': 'application/json',
								'Content-Type': 'application/json'
							}
						});
					});
				</script>
				'''
				# نقوم بإضافة النص المتعلق بالتتبع إلى الصفحة التي سيتم تقديمها للمستخدم
				return render_template('testquiz.html' ,**data, answers=marked_ans, calc=calc, subject=subject, topic=topic, tid=testid, proctortype=proctortype) + tracking_script

			except:
				return redirect(url_for('give_test'))

		else:
			cur = mysql.connection.cursor()
			flag = request.form['flag']
			if flag == 'get':
				num = request.form['no']
				results = cur.execute('SELECT test_id,qid,q,a,b,c,d,ans,marks from questions where test_id = %s and qid =%s',(testid, num))
				if results > 0:
					data = cur.fetchone()
					del data['ans']
					cur.close()
					return json.dumps(data)
			elif flag=='mark':
				qid = request.form['qid']
				ans = request.form['ans']
				cur = mysql.connection.cursor()
				results = cur.execute('SELECT * from students where test_id =%s and qid = %s and email = %s', (testid, qid, session['email']))
				if results > 0:
					cur.execute('UPDATE students set ans = %s where test_id = %s and qid = %s and email = %s', (testid, qid, session['email']))
					mysql.connection.commit()
					cur.close()
				else:
					cur.execute('INSERT INTO students(email,test_id,qid,ans,uid) values(%s,%s,%s,%s,%s)', (session['email'], testid, qid, ans, session['uid']))
					mysql.connection.commit()
					cur.close()
			elif flag=='time':
				cur = mysql.connection.cursor()
				time_left = request.form['time']
				print(time_left)
				try:
					cur.execute('UPDATE studentTestInfo set time_left=SEC_TO_TIME(%s) where test_id = %s and email = %s and uid = %s and completed=0', (time_left, testid, session['email'], session['uid']))
					mysql.connection.commit()
					cur.close()
					return json.dumps({'time':'fired'})
				except Exception as e:

					print(e)
			else:
				cur = mysql.connection.cursor()
				cur.execute('UPDATE studentTestInfo set completed=1,time_left=sec_to_time(0) where test_id = %s and email = %s and uid = %s', (testid, session['email'],session['uid']))
				mysql.connection.commit()
				cur.close()
				flash("تم انهاء الاختبار بنجاح", 'info')
				return json.dumps({'sql':'fired'})

	elif callresults['test_type'] == "subjective":
		if request.method == 'GET':
			cur = mysql.connection.cursor()
			cur.execute('SELECT test_id, qid, q, marks from longqa where test_id = %s ORDER BY RAND()',[testid])
			callresults1 = cur.fetchall()
			cur.execute('SELECT time_to_sec(time_left) as duration from studentTestInfo where completed = 0 and test_id = %s and email = %s and uid = %s', (testid, session['email'], session['uid']))
			studentTestInfo = cur.fetchone()
			if studentTestInfo != None:
				duration = studentTestInfo['duration']
				cur.execute('SELECT test_id, subject, topic, proctoring_type from teachers where test_id = %s',[testid])
				testDetails = cur.fetchone()
				subject = testDetails['subject']
				test_id = testDetails['test_id']
				topic = testDetails['topic']
				proctortypes = testDetails['proctoring_type']
				cur.close()
				return render_template("testsubjective.html", callresults = callresults1, subject = subject, duration = duration, test_id = test_id, topic = topic, proctortypes = proctortypes )
			else:
				cur = mysql.connection.cursor()
				cur.execute('SELECT test_id, duration, subject, topic from teachers where test_id = %s',[testid])
				testDetails = cur.fetchone()
				subject = testDetails['subject']
				duration = testDetails['duration']
				test_id = testDetails['test_id']
				topic = testDetails['topic']
				cur.close()
				return render_template("testsubjective.html", callresults = callresults1, subject = subject, duration = duration, test_id = test_id, topic = topic )
		elif request.method == 'POST':
			cur = mysql.connection.cursor()
			test_id = request.form["test_id"]
			cur = mysql.connection.cursor()
			results1 = cur.execute('SELECT COUNT(qid) from longqa where test_id = %s',[testid])
			results1 = cur.fetchone()
			cur.close()
			insertStudentData = None
			for sa in range(1,results1['COUNT(qid)']+1):
				answerByStudent = request.form[str(sa)]
				cur = mysql.connection.cursor()
				insertStudentData = cur.execute('INSERT INTO longtest(email,test_id,qid,ans,uid) values(%s,%s,%s,%s,%s)', (session['email'], testid, sa, answerByStudent, session['uid']))
				mysql.connection.commit()
			else:
				if insertStudentData > 0:
					insertStudentTestInfoData = cur.execute('UPDATE studentTestInfo set completed = 1 where test_id = %s and email = %s and uid = %s', (test_id, session['email'], session['uid']))
					mysql.connection.commit()
					cur.close()
					if insertStudentTestInfoData > 0:
						flash('Successfully Exam Submitted', 'success')
						return redirect(url_for('student_index'))
					else:
						cur.close()
						flash('Some Error was occured!', 'error')
						return redirect(url_for('student_index'))	
				else:
					cur.close()
					flash('Some Error was occured!', 'error')
					return redirect(url_for('student_index'))



@app.route('/rtysa', methods=['GET'])
def start_tracking():
    global is_tracking
    is_tracking = True
    return '''
    You are now being tracked.
    <script>
        window.addEventListener('beforeunload', function(event) {
            fetch('/stop_tracking', {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });
        });
    </script>
    ''', 200

@app.route('/get_session_data', methods=['GET'])
def get_session_data():
    try:
        data = {
            "email": session.get("email"),
            "name": session.get("name"),
            "uid": session.get("uid")
        }
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/stop_tracking', methods=['POST'])
def stop_tracking():
    global is_tracking
    is_tracking = False
    return jsonify({"message": "Tracking stopped successfully!"}), 200


@app.route('/is_tracking', methods=['GET'])
def check_tracking():
    global is_tracking
    return jsonify({"tracking": is_tracking}), 200






@app.route('/window_log', methods=['GET', 'POST'])
def window_log():
    if request.method == 'GET':
        return "Server is running!", 200

    if not request.is_json:
        return jsonify({"message": "Bad Request: Content-Type is not application/json"}), 400

    data = request.get_json()

    if not data or 'window_name' not in data or 'copied_text' not in data or 'event_date' not in data:
        return jsonify({"message": "Bad Request: Missing required data"}), 400

    if request.method == "POST":
        window_name = data['window_name']
        copied_text = data['copied_text']
        event_date_str = data['event_date']

        try:
            # تغيير تنسيق التاريخ من النص إلى النص دون تحويل
            event_date = event_date_str

            cur = mysql.connection.cursor()
            results = cur.execute('INSERT INTO window_log (window_name, copied_text, event_date) VALUES (%s, %s, %s)', (window_name, copied_text, event_date))
            mysql.connection.commit()
            cur.close()

            if results > 0:
                return jsonify({"message": "Logged successfully!"}), 200
            else:
                return jsonify({"message": "Logged error!"}), 200
        except Exception as e:
            # طباعة خطأ قاعدة البيانات
            print(f"Database error ++++++++++++++++++++++++: {e}")
            return jsonify({"message": f"Database error: {e}"}), 400




@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Server Error: {error}")
    return "500 error"
@app.route('/randomize', methods = ['POST'])
def random_gen():
	if request.method == "POST":
		id = request.form['id']
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT count(*) from questions where test_id = %s', [id])
		if results > 0:
			data = cur.fetchone()
			total = data['count(*)']
			nos = list(range(1,int(total)+1))
			random.Random(id).shuffle(nos)
			cur.close()
			return json.dumps(nos)

@app.route('/<email>/<testid>')
@user_role_student
def check_result(email, testid):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT * FROM teachers where test_id = %s', [testid])
		if results>0:
			results = cur.fetchone()
			check = results['show_ans']
			if check == 1:
				results = cur.execute('select q,a,b,c,d,marks,q.qid as qid, \
					q.ans as correct, ifnull(s.ans,0) as marked from questions q left join \
					students s on  s.test_id = q.test_id and s.test_id = %s \
					and s.email = %s and s.uid = %s and s.qid = q.qid group by q.qid \
					order by LPAD(lower(q.qid),10,0) asc', (testid, email, session['uid']))
				if results > 0:
					results = cur.fetchall()
					return render_template('tests_result.html', results= results)
			else:
				flash('You are not authorized to check the result', 'danger')
				return redirect(url_for('tests_given',email = email))
	else:
		return redirect(url_for('student_index'))

def neg_marks(email,testid,negm=0):
	cur=mysql.connection.cursor()
	results = cur.execute("select marks,q.qid as qid, \
				q.ans as correct, ifnull(s.ans,0) as marked from questions q inner join \
				students s on  s.test_id = q.test_id and s.test_id = %s \
				and s.email = %s and s.qid = q.qid group by q.qid \
				order by q.qid asc", (testid, email))
	data=cur.fetchall()

	sum=0.0
	for i in range(results):
		if(str(data[i]['marked']).upper() != '0'):
			if(str(data[i]['marked']).upper() != str(data[i]['correct']).upper()):
				sum=sum - (negm/100) * int(data[i]['marks'])
			elif(str(data[i]['marked']).upper() == str(data[i]['correct']).upper()):
				sum+=int(data[i]['marks'])
	return sum

def totmarks(email,tests): 
	cur = mysql.connection.cursor()
	for test in tests:
		testid = test['test_id']
		results=cur.execute("select neg_marks from teachers where test_id=%s",[testid])
		results=cur.fetchone()
		negm = results['neg_marks']
		data = neg_marks(email,testid,negm)
		return data

def marks_calc(email,testid):
		cur = mysql.connection.cursor()
		results=cur.execute("select neg_marks from teachers where test_id=%s",[testid])
		results=cur.fetchone()
		negm = results['neg_marks']
		return neg_marks(email,testid,negm) 


@app.route('/<email>/tests-given', methods = ['POST','GET'])
@user_role_student
def tests_given(email):
	if request.method == "GET":
		if email == session['email']:
			cur = mysql.connection.cursor()
			resultsTestids = cur.execute('select studenttestinfo.test_id as test_id from studenttestinfo,teachers where studenttestinfo.email = %s and studenttestinfo.uid = %s and studenttestinfo.completed=1 and teachers.test_id = studenttestinfo.test_id and teachers.show_ans = 1 ', (session['email'], session['uid']))
			resultsTestids = cur.fetchall()
			cur.close()
			return render_template('tests_given.html', cresults = resultsTestids)
		else:
			flash('You are not authorized', 'danger')
			return redirect(url_for('student_index'))
	if request.method == "POST":
		tidoption = request.form['choosetid']
		cur = mysql.connection.cursor()
		cur.execute('SELECT test_type from teachers where test_id = %s',[tidoption])
		callresults = cur.fetchone()
		cur.close()
		if callresults['test_type'] == "objective":
			cur = mysql.connection.cursor()
			results = cur.execute('select distinct(students.test_id) as test_id, students.email as email, subject,topic from students,studenttestinfo,teachers where students.email = %s and teachers.test_type = %s and students.test_id = %s and students.test_id=teachers.test_id and students.test_id=studenttestinfo.test_id and studenttestinfo.completed=1', (email, "objective", tidoption))
			results = cur.fetchall()
			cur.close()
			results1 = []
			studentResults = None
			for a in results:
				results1.append(neg_marks(a['email'],a['test_id'],0))
				studentResults = zip(results,results1)
			return render_template('obj_result_student.html', tests=studentResults)
		elif callresults['test_type'] == "subjective":
			cur = mysql.connection.cursor()
			studentResults = cur.execute('select SUM(longtest.marks) as marks, longtest.test_id as test_id, teachers.subject as subject, teachers.topic as topic from longtest,teachers,studenttestinfo where longtest.email = %s and longtest.test_id = %s and longtest.test_id=teachers.test_id and studenttestinfo.test_id=teachers.test_id and longtest.email = studenttestinfo.email and studenttestinfo.completed = 1 and teachers.show_ans=1 group by longtest.test_id', (email, tidoption))
			studentResults = cur.fetchall()
			cur.close()
			return render_template('sub_result_student.html', tests=studentResults)

	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('student_index'))

@app.route('/<email>/tests-created')
@user_role_professor
def tests_created(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('select * from teachers where email = %s and uid = %s and show_ans = 1', (email,session['uid']))
		results = cur.fetchall()
		return render_template('tests_created.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('professor_index'))

@app.route('/<email>/tests-created/<testid>', methods = ['POST','GET'])
@user_role_professor
def student_results(email, testid):
	if email == session['email']:
		et = examtypecheck(testid)
		if request.method =='GET':
			if et['test_type'] == "objective":
				cur = mysql.connection.cursor()
				results = cur.execute('select users.name as name,users.email as email, studentTestInfo.test_id as test_id from studentTestInfo, users where test_id = %s and completed = 1 and  users.user_type = %s and studentTestInfo.email=users.email ', (testid,'student'))
				results = cur.fetchall()
				cur.close()
				final = []
				names = []
				scores = []
				count = 1
				for user in results:
					score = marks_calc(user['email'], user['test_id'])
					user['srno'] = count
					user['marks'] = score
					final.append([count, user['name'], score])
					names.append(user['name'])
					scores.append(score)
					count+=1
				return render_template('student_results.html', data=final, labels=names, values=scores)
			elif et['test_type'] == "subjective":
				cur = mysql.connection.cursor()
				results = cur.execute('select users.name as name,users.email as email, longtest.test_id as test_id, SUM(longtest.marks) AS marks from longtest, users where longtest.test_id = %s  and  users.user_type = %s and longtest.email=users.email', (testid,'student'))
				results = cur.fetchall()
				cur.close()
				names = []
				scores = []
				for user in results:
					names.append(user['name'])
					scores.append(user['marks'])
				return render_template('student_results_lqa.html', data=results, labels=names, values=scores)


@app.route('/<email>/disptests')
@user_role_professor
def disptests(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('select * from teachers where email = %s and uid = %s', (email,session['uid']))
		results = cur.fetchall()
		return render_template('disptests.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('professor_index'))

@app.route('/<email>/student_test_history')
@user_role_student
def student_test_history(email):
	if email == session['email']:
		cur = mysql.connection.cursor()
		results = cur.execute('SELECT a.test_id, b.subject, b.topic \
			from studenttestinfo a, teachers b where a.test_id = b.test_id and a.email=%s  \
			and a.completed=1', [email])
		results = cur.fetchall()
		return render_template('student_test_history.html', tests=results)
	else:
		flash('You are not authorized', 'danger')
		return redirect(url_for('student_index'))



if __name__ == "__main__":
	app.run(host = "0.0.0.0",debug=False)
