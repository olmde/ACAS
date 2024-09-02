import os
from app import db, login, app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer


# Association table for many-to-many relationship between students and lectures
student_lectures = db.Table('student_lectures',
    db.Column('student_id', db.Integer, db.ForeignKey('students.student_id'), primary_key=True),
    db.Column('lecture_id', db.Integer, db.ForeignKey('lectures.lecture_id'), primary_key=True)
)

class Teacher(UserMixin, db.Model):
    __tablename__ = 'teachers'
    teacher_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(11), nullable=False, unique=True)
    email = db.Column(db.String(64), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default='teacher')
    lectures = db.relationship('Lecture', backref='lecturer', lazy='dynamic')
    
    #method for creating timed session token for 1800 secs (30mins)
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'teacher_id': self.teacher_id}).decode('utf-8')
    
    #method to validate tokens activation
    @staticmethod #no self parameter argument expected
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            teacher_id = s.loads(token)['teacher_id']
        except:
            return None
        return Teacher.query.get(teacher_id)


    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return str(self.teacher_id)

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
    lectures = db.relationship('Lecture', backref='student', lazy='dynamic')
    images = db.relationship('Image', backref='students', lazy='dynamic')

    
    def get_reset_token(self, expires_sec=1800):
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'student_id': self.student_id}).decode('utf-8')

    
    @staticmethod
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            student_id = s.loads(token)['student_id']
        except:
            return None
        return Student.query.get(student_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, salt_length=32)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        return str(self.student_id)
    def __repr__(self):
        return f"Student(id='{self.student_id}', '{self.first_name}', '{self.last_name}', '{self.email}', active='{self.active}')"

@login.user_loader
def load_user(id):
    user=Teacher.query.get(int(id))
    if user is None:
        user = Student.query.get(int(id))
        
class Attendance(db.Model):
    __tablename__ = 'attendance'
    attendance_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.lecture_id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    present = db.Column(db.Boolean, nullable=False)
    attendance_date = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"Attendance(attendance_id='{self.attendance_id}', lecture_id='{self.lecture_id}', student_id='{self.student_id}', attendance_date='{self.attendance_date}')"

class Lecture(db.Model):
    __tablename__ = 'lectures'
    lecture_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    title = db.Column(db.String(32), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.teacher_id'), nullable=False)
    attendees = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    lecture_date = db.Column(db.DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"Lecture(lecture_id='{self.lecture_id}', title='{self.title}', teacher_id='{self.teacher_id}', lecture_date='{self.lecture_date}')"

class Image(db.Model):
    __tablename__ = 'images'
    image_id = db.Column(db.Integer, primary_key=True, unique=True, nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    
    def save_image(image_file, filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image_file.save(file_path)
        new_image = Image(image_path=file_path)
        db.session.add(new_image)
        db.session.commit()
        
    def __repr__(self):
        return f"Image(image_id='{self.image_id}', image_path='{self.image_path}', student_id='{self.student_id}')"
        
