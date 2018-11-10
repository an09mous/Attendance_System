import base64,cv2,scipy.misc
import numpy as np
from sklearn.externals import joblib
from sklearn.neighbors import KNeighborsClassifier
import hashlib, os, time
from flask import Flask, render_template, url_for, request, redirect, session, make_response
from flask_sqlalchemy import SQLAlchemy

app=Flask(__name__)

app.config['SECRET_KEY']='9a25e614db5a2dbf190d7bed2dada010'

#<-----General Database----->
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///General.sqlite3'
app.config['SQLALCHEMY_BINDS']={'Members':'sqlite:///Members.sqlite3','Entries':'sqlite:///Entries.sqlite3'}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db = SQLAlchemy(app)
class General(db.Model):
	__abstract__=1
	student_id=db.Column(db.Integer, primary_key=True)
	student_no=db.Column(db.Integer,unique=True,nullable=False)
	username=db.Column(db.String(100),unique=True,nullable=False)
	name=db.Column(db.String(100),nullable=False)
	branch=db.Column(db.String(3),nullable=False)
	year=db.Column(db.Integer,nullable=False)
	def __init__(self, student_no, username, name, branch, year):
		self.student_no=student_no
		self.username=username
		self.name=name
		self.branch=branch
		self.year=year
#<-----general Database ends ----->

#<-----Members Database----->
class Members(General):
	__bind_key__ = "Members"
	password=db.Column(db.String(100),nullable=False)
	def __init__(self,student_no, username, name, branch, year, password):
		self.student_no=student_no
		self.username=username
		self.name=name
		self.branch=branch
		self.year=year
		self.password=password
#<-----Members Database ends----->

#<-----Entries Database----->
class Entries(General):
	__bind_key__ = "Entries"
	student_id=db.Column(db.Integer, primary_key=True)
	student_no=db.Column(db.Integer,nullable=False)
	username=db.Column(db.String(100),nullable=False)
	name=db.Column(db.String(100),nullable=False)
	branch=db.Column(db.String(3),nullable=False)
	year=db.Column(db.Integer,nullable=False)
	date=db.Column(db.String(100),nullable=False)
	check_in=db.Column(db.String(100),nullable=False)
	check_out=db.Column(db.String(100))
	#month=db.Column(db.Integer,nullable=False)
	def __init__(self, student_no, username, name, branch, year, date, check_in):
		self.student_no=student_no
		self.username=username
		self.name=name
		self.branch=branch
		self.year=year
		self.date=date
		self.check_in=check_in
		self.check_out=None
		#self.month=month
#<-----Entries Database ends----->

#<-----Face Recognition work----->
labels=[Members.query.all()[i].username for i in range(Members.query.count())]
#Preprocessing image
def preprocess(img):
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier('model/haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5);
    if (len(faces) == 0):
        img=cv2.resize(gray,(280,280))
    else: 
        (x, y, w, h) = faces[0]
        img=cv2.resize(gray[y:y+w, x:x+h],(280,280))
    img=img.flatten()
    img=img.reshape(1,len(img))
    img=np.array([value for value in img[0]])
    return img.reshape(1,len(img))

#Loading the model
model='model/model.pkl'
face_recognizer=joblib.load(model)

#Predicting the subject
def predict(test_img):
    label= face_recognizer.predict(test_img)
    return (labels[label[0]])
#<-----Face recognition work ends----->


#num=0
@app.route("/")
@app.route("/home")
def home():
	if request.cookies.get('username'):
		session['username']=request.cookies.get('username')
	if 'username' in session:
		return redirect(url_for('success'))
	return render_template('index.html')

@app.route("/success")
def success():
	if request.cookies.get('username'):
		session['username']=request.cookies.get('username')
	if 'username' in session:
		if session['username']=='admin':
			online_users=[user.username for user in Entries.query.filter_by(check_out=None)]
			d=time.localtime(time.time())
			date='-'.join(map(str,[d.tm_mday,d.tm_mon,d.tm_year]))
			all_users=Entries.query.filter_by(date=date)
			recent_entries=[]
			dates=[]
			for i in range(7):
				date='-'.join(map(str,[d.tm_mday-i,d.tm_mon,d.tm_year]))
				dates.append(str(date))
				q=Entries.query.filter_by(date=date)
				if q:
					recent_entries.append(sum([1 for i in q]))
				else:
					recent_entries.append(0)
			recent_entries=recent_entries[::-1]
			dates=dates[::-1]
			if not request.cookies.get('username'):
				resp=make_response(render_template('dashboard.html',online_users=online_users,all_users=all_users,recent_entries=recent_entries, dates=dates))
				resp.set_cookie('username','admin',max_age=21600)
				return resp
			return render_template('dashboard.html',online_users=online_users,all_users=all_users,recent_entries=recent_entries,dates=dates)
		elif 'confirmed' in session:
			return redirect(url_for('mark_attendance'))
		else:
			try:
				session['count']+=1
			except:
				session['count']=0
			if not request.cookies.get('username'):
				resp=make_response(render_template('face_detectp.html',title='Face Login',count=session['count']))
				resp.set_cookie('username',session['username'],max_age=21600)
				return resp
			return render_template('face_detectp.html',title='Face Login',count=session['count'])

	else:
		return redirect(url_for('home'))

@app.route("/logout")
def logout():
	resp='''<meta http-equiv="refresh" content="1; url=/home">
			<h1>Successfully logged out</h1>'''
	if 'username' in session:
		if request.cookies.get('username'):
			resp=make_response(resp)
			resp.set_cookie('username',session['username'],max_age=0)
		session.pop('username',None)
		if 'confirmed' in session:
			session.pop('confirmed',None)
		return resp
	return redirect(url_for('home'))


@app.route("/login",methods=['POST','GET'])
def login():
	if 'username' in session:
		return redirect(url_for('success'))
	if request.method=='POST':
		user=request.form['username']
		password=str(hashlib.md5(request.form['password'].encode()).hexdigest())
		if user=='admin' and password=='21232f297a57a5a743894a0e4a801fc3':
			session['username']=user
			session['i']=0
			mems=Entries.query.filter_by(check_out=None)
			for m in mems:
				d=list(map(int,m.date.split('-')))
				cd=time.localtime(time.time())
				flag=0
				if cd.tm_year==d[2]:
					if cd.tm_mon==d[1]:
						if cd.tm_mday==d[0]:
							flag=0
						else:flag=1
					else:
						flag=1
				else:
					flag=1
				if flag==1:
					m.check_out='23:00:00'
					db.session.commit()
			return redirect(url_for('success'))
		elif Members.query.filter_by(username=user).first():
			if Members.query.filter_by(username=user).first().password==password:
				session['username']=user
				session['count']=0
				return redirect('success')
			return render_template('index.html',alert='Invalid Password')
		else:
			return render_template('index.html',alert='Invalid Username or Password')
	return redirect(url_for('home'))

@app.route("/face_login",methods=['POST','GET'])
def face_login():
	if 'confirmed' in session:
		return redirect(url_for('mark_attendance'))
	if request.method=='POST':
		img=request.form['imgBase64'][22:]#Removing path
		img = base64.b64decode(img) #Converting base64 to bytes
		img=cv2.imdecode(np.frombuffer(img,np.uint8),-1)[:,:,:3]#Converting into numpy array and Removing alpha channel
		#scipy.misc.toimage(img, cmin=0.0, cmax=...).save('model/s{}/{}.jpg'.format(labels.index(session['username']),num))
		#num+=1
		img=preprocess(img)
		#scipy.misc.toimage(img, cmin=0.0, cmax=...).save('outfile.jpg')		
		subject=predict(img)
		print(subject)

		if session['username']==subject:
			session['confirmed']=1
			return redirect(url_for('success'))
		else:
			return redirect(url_for('face_login'))
	return redirect(url_for('home'))

@app.route("/manual_login",methods=['POST','GET'])
def manual_login():
	if 'username' in session:
		if 'confirmed' not in session:
			if request.method=='POST':
				password=request.form['pass']
				if password=='admin':
					session['confirmed']=1
					return redirect(url_for('mark_attendance'))
	return redirect(url_for('success'))

@app.route("/mark_attendance")
def mark_attendance():
	if 'confirmed' in session:
		if Entries.query.filter_by(username=session['username'],check_out=None).first():
			session['status']=1
		else:
			session['status']=0
		return render_template('mark_attendance.html',user=session['username'],status=session['status'])
	return redirect(url_for('home'))

@app.route("/status", methods=['POST','GET'])
def status():
	if 'confirmed' in session:
		if request.method=='POST':
			date=request.form['date']
			month=int(date.split('-')[1])
			time=request.form['time']
			if session['status']==1:
				member=Entries.query.filter_by(username=session['username'], check_out=None,date=date).first()
				member.check_out=time
				db.session.commit()
				session['status']=0
				return '0'
			else:
				member=Members.query.filter_by(username=session['username']).first()
				db.session.add(Entries(member.student_no,member.username,member.name,member.branch,member.year,
											date,time))
				db.session.commit()
				session['status']=1
				return '1'
	else:
		return redirect(url_for('home'))

@app.route('/details')
def details():
	if 'username' in session:
		if session['username']=='admin':
			online_users=[user.username for user in Entries.query.filter_by(check_out=None)]
			all_users=Entries.query.all()
			return render_template('details.html',online_users=online_users,all_users=all_users)

@app.route('/add_user',methods=['POST','GET'])
def add_user():
	if 'username' in session:
		if session['username']=='admin':
			if request.method=='POST':
				student_no=request.form['student_no']
				username=request.form['username']
				if username=='admin':
					return '''<meta http-equiv="refresh" content="1; url=/add_user">
							<h1>Username can't be admin!</h1>'''
				name=request.form['name']
				branch=request.form['branch']
				year=request.form['year']
				password=hashlib.md5(request.form['password'].encode()).hexdigest()
				try:
					db.session.add(Members(student_no,username,name,branch,year,password))
					db.session.commit()
					session['added_user']=username
					return '''<meta http-equiv="refresh" content="1; url=/home">
							<h1>Successfully Added</h1>'''
				except:
					return '''<meta http-equiv="refresh" content="1; url=/add_user">
							<h1>Details already present in database</h1>'''
				#return redirect(url_for('add_photos'))
			else:
				online_users=[user.username for user in Entries.query.filter_by(check_out=None)]
				return render_template('add_user.html',online_users=online_users)
	return redirect(url_for('success'))

'''@app.route('/add_photos',methods=['POST','GET'])
def add_photos():
	if 'username' in session:
		if session['username']=='admin':
			if request.method=='POST':
				username=request.form['username']
				if not os.path.exists('train_set'):
					os.makedirs('train_set/{}'.format(username))
				img=request.form['imgBase64'][22:]
				img=base64.b64decode(img)
				img=cv2.imdecode(np.frombuffer(img,np.uint8),-1)[:,:,:3]
				scipy.misc.toimage(img, cmin=0.0, cmax=...).save('train_set/{}/{}.jpg'.format(username,session['i']))
				session['i']+=1
				return 'success'
			else:
				return render_template('add_photos.html',added_user=session['added_user'])
	return('success')'''

					

@app.route("/filter",methods=['POST','GET'])
def filter():
	if 'username' in session:
		if session['username']=='admin':
			if request.method=='POST':
				d1=list(map(int,request.form['d1'].split('-')))
				d2=list(map(int,request.form['d2'].split('-')))
				t1=list(map(int,request.form['t1'].split(':')))
				t2=list(map(int,request.form['t2'].split(':')))
				print(d1,d2,t1,t2)
				output=[]
				return redirect(url_for('success'))
	return redirect(url_for('success'))

@app.route("/get_my_ip")
def get_my_ip():
	request.environ['REMOTE_ADDR']
	ip=request.remote_addr
	print(ip)
	return ip, 200


if __name__=='__main__':
	app.run(debug=True)