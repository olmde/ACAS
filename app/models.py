import os
from app import db, login, app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeSerializer as Serializer
import jwt
import datetime

class Teacher(UserMixin, db.Model):
    __tablename__ = 'teachers'
    teacher_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(64), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default='teacher')
    lectures = db.relationship('Lecture', backref='lecturer', lazy='dynamic')
    
    #method for creating timed session token for 1800 secs (30mins)
    def get_reset_token(self, expires_sec=1800):
        reset_token = jwt.encode(
            {
                "confirm": self.teacher_id,
                "exp": datetime.datetime.now(tz=datetime.timezone.utc)
                       + datetime.timedelta(seconds=expires_sec)
            },
            app.config['SECRET_KEY'],
            algorithm="HS256"
        )
        return reset_token

    
    def verify_reset_token(self, token):
        try:
            data = jwt.decode(
                token,
                app.config['SECRET_KEY'],
                leeway=datetime.timedelta(seconds=10),
                algorithms=["HS256"]
            )
        except:
            return False
        if data.get('confirm') != self.teacher_id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True



    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"teacher_{self.teacher_id}"

    def __repr__(self):
        return f"Teacher(id='{self.teacher_id}', '{self.first_name}', '{self.last_name}', '{self.email}')"

class Student(UserMixin, db.Model):
    __tablename__ = 'students'
    student_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    first_name = db.Column(db.String(32), nullable=False)
    last_name = db.Column(db.String(32), nullable=False, index=True)
    email = db.Column(db.String(64), nullable=False, unique=True, index=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default='student')
    images = db.relationship('Image', backref='students', lazy='dynamic')

    
    def get_reset_token(self, expires_sec=1800):
            reset_token = jwt.encode(
                {
                    "confirm": self.student_id,
                    "exp": datetime.datetime.now(tz=datetime.timezone.utc)
                        + datetime.timedelta(seconds=expires_sec)
                },
                app.config['SECRET_KEY'],
                algorithm="HS256"
            )
            return reset_token

    
    def verify_reset_token(self, token):
        try:
            data = jwt.decode(
                token,
                app.config['SECRET_KEY'],
                leeway=datetime.timedelta(seconds=10),
                algorithms=["HS256"]
            )
        except:
            return False
        if data.get('confirm') != self.student_id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True


    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return f"student_{self.student_id}"
    
    def __repr__(self):
        return f"Student(id='{self.student_id}', '{self.first_name}', '{self.last_name}', '{self.email}', active='{self.active}')"

@login.user_loader
def load_user(id):
    if id.startswith('teacher_'):
        user_id = int(id[len('teacher_'):])
        return Teacher.query.get(user_id)
    elif id.startswith('student_'):
        user_id = int(id[len('student_'):])
        return Student.query.get(user_id)
    return None

class Attendance(db.Model):
    __tablename__ = 'attendance'
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.lecture_id'), nullable=False, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False, primary_key=True)
    status = db.Column(db.String(32), default='Absent', nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"Attendance(lecture_id='{self.lecture_id}', student_id='{self.student_id}', timestamp='{self.timestamp}')"

class Lecture(db.Model):
    __tablename__ = 'lectures'
    lecture_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    title = db.Column(db.String(32), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'), nullable=False)
    date = db.Column(db.DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"Lecture(lecture_id='{self.lecture_id}', title='{self.title}', teacher_id='{self.teacher_id}', date='{self.date}')"

class Image(db.Model):
    __tablename__ = 'images'
    image_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False)
