from flask_wtf import FlaskForm
from flask_login import current_user
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import Teacher, Student
import re

class RegistrationForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('Register as', choices=[('student', 'Student'), ('teacher', 'Teacher')], validators=[DataRequired()])
    submit = SubmitField('Register')
    
    def validate_first_name(self, first_name):
        for x in first_name.data:
            if x.isnumeric() or not x.isalnum():
                raise ValidationError('No: special characters, numbers or space permitted.')
        
        
    def validate_last_name(self, last_name):
        for x in last_name.data:
            if x.isnumeric() or not x.isalnum():

                raise ValidationError('No: special characters, numbers or space permitted.')
            
    def validate_email(self, email): 
        email.data=email.data.lower()
        teacher = Teacher.query.filter_by(email=email.data).first()
        student = Student.query.filter_by(email=email.data).first()
        if teacher or student:
            raise ValidationError('This email is already registered. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Request Password Request')
    
    def validate_email(self, email):
        lowercase_email = email.data.lower()
        email_pattern = re.compile(r'^\w.+@(\w+\.)?\w+\.(com|co.uk|org|net|ac.uk)$', re.IGNORECASE)
        if not email_pattern.match(lowercase_email):
                raise ValidationError('Invalid email address.')

        teacher = Teacher.query.filter_by(email=lowercase_email).first()
        student = Student.query.filter_by(email=lowercase_email).first()
        if not teacher and not student:
            raise ValidationError('Sorry, this email is not currently registered.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class UpdateAccountForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Update')


    def validate_first_name(self, first_name):
        for x in first_name.data:
            if x.isnumeric() or not x.isalnum():
                raise ValidationError('No: special characters, numbers or space permitted.')
        
        
    def validate_last_name(self, last_name):
        for x in last_name.data:
            if x.isnumeric() or not x.isalnum():

                raise ValidationError('No: special characters, numbers or space permitted.')
        
        
    def validate_email(self, email): 
        if email.data != current_user.email:
            email.data=email.data.lower()
            teacher = Teacher.query.filter_by(email=email.data).first()
            student = Student.query.filter_by(email=email.data).first()
            if teacher or student:
                raise ValidationError('This email is already registered. Please choose a different one.')

class UploadImageForm(FlaskForm):
    upload_file = FileField('Upload your pictures below', validators=[DataRequired(),FileAllowed(['jpg', 'png', 'heic'])])
    submit = SubmitField('Upload')
    

        
class DeleteImageForm(FlaskForm):
    submit = SubmitField('Delete')

class ChangeImageForm(FlaskForm):
    new_image = FileField('New Image', validators=[DataRequired(), FileAllowed(['jpg', 'png', 'heic'])])
    submit = SubmitField('Change Image')

class UploadLectureForm(FlaskForm):
    lecture_file = FileField('Upload Lectures below', validators=[DataRequired(), FileAllowed(['csv'])])
    submit = SubmitField('Upload Lectures')
    
