from flask import render_template, redirect, url_for, flash, request, Response
from sqlalchemy import cast, String, func
from app import app, db, mail
from datetime import datetime, timedelta
from app.forms import (LoginForm, RegistrationForm, RequestResetForm, ResetPasswordForm,
                       UpdateAccountForm, UploadImageForm, DeleteImageForm, ChangeImageForm, UploadLectureForm)
from app.models import Teacher, Student, Image, Lecture, Attendance
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit
from uuid import uuid4
from werkzeug.utils import secure_filename
import os
import csv
from email_validator import validate_email, EmailNotValidError
from werkzeug.security import generate_password_hash
from flask_mail import Message
from app.functions import (send_reset_email, create_student_directory, create_augmented_student_directory,
                           load_images, augment_and_save_images, augment_images_in_background,
                           delete_augmented_images, silent_remove, train_model_in_background, silent_remove, 
                           update_attendance, initialise_attendance)
import threading
import csv
from app.recognition import *
import face_recognition
import os
import numpy as np
import joblib  
import cv2 


@app.route('/')
@app.route('/home')
def home():
    if current_user.is_authenticated and current_user.role == 'teacher':
        if not model_files_exist():
            train_model_in_background(app.config['AUGMENTED_FOLDER'])
            flash('model training has begun', 'info')
            
    return render_template('home.html')


@app.route("/register", methods=['GET', 'POST']) 
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        if form.user_type.data == 'teacher':
            user = Teacher(first_name=form.first_name.data, last_name=form.last_name.data, email=email, password_hash=generate_password_hash(form.password.data, salt_length=32))
        else:
            user = Student(first_name=form.first_name.data, last_name=form.last_name.data, email=email, password_hash=generate_password_hash(form.password.data, salt_length=32))         
        db.session.add(user)
        db.session.commit()
        
        if form.user_type.data != 'teacher':
            student_id = user.student_id
            create_student_directory(student_id)
            create_augmented_student_directory(student_id)

        flash('Account created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower()
        user = Teacher.query.filter_by(email=email).first()
        if not user:
            user = Student.query.filter_by(email=email).first()
            
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        flash(f'Welcome back {user.first_name} {user.last_name}!', 'success')
        
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('home')
        
        return redirect(next_page)
    
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/reset_password', methods = ['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect (url_for('home.html'))
    form = RequestResetForm()
    if form.validate_on_submit():
        email = form.email.data.lower()

        user = Teacher.query.filter_by(email=email).first()
        if not user:
            user = Student.query.filter_by(email=email).first()
            
            send_reset_email(user)
            flash ('An email with instructions to reset your password has been sent','info')
            return redirect('login')
        
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods = ['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    user = Teacher.verify_reset_token(token)
    student = None
    if not user:
        user = Student.verify_reset_token(token)
    
    else:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data)
        user.password_hash = password_hash 
        db.session.commit()
        flash(f'Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)

@app.route('/account', methods = ['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.email = form.email.data.lower()
        db.session.commit()
        flash('Account changes saved', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    student_id = current_user.student_id
    image_counter = Image.query.filter_by(student_id=student_id).count()

    form = UploadImageForm()
    if form.validate_on_submit():
        if request.method == 'POST':
            files = request.files.getlist(form.upload_file.name)
            image = 0
            duplicate_image_list = []
            successful_image_upload_list = []
            combined_message = ''
            images_with_ids = []

            for file in files:
                image += 1
                filename = secure_filename(file.filename)
                relative_path = os.path.join('images', str(student_id), filename)
                absolute_path = os.path.join(app.config['UPLOAD_FOLDER'], str(student_id), filename)
                
                if os.path.exists(absolute_path):
                    duplicate_image_list.append(image)
                else:
                    new_image = Image(image_path=relative_path, student_id=student_id, upload_date=datetime.now())     
                    try:
                        db.session.add(new_image)
                        db.session.commit()
                        file.save(absolute_path)
                        successful_image_upload_list.append(image)
                        images_with_ids.append((filename, new_image.image_id))

                    except Exception as e:
                        db.session.rollback()
                        if os.path.exists(absolute_path):
                            os.remove(absolute_path)
            
            if duplicate_image_list:
                flash(f'Image(s) {duplicate_image_list} have already been uploaded. Only new images can be uploaded.', 'info')
            if successful_image_upload_list:
                image_counter = Image.query.filter_by(student_id=student_id).count()
                combined_message = f'Image(s) {successful_image_upload_list} successfully uploaded: You now have {image_counter} picture(s) uploaded.'

                if image_counter < 3:
                    combined_message += '<br> A minimum of 3 images are required.'

                flash(combined_message, 'success')   

                # Thread to create and save augmented images upon upload so user does not have to wait on loading page
                threading.Thread(target=augment_images_in_background, args=(student_id, images_with_ids)).start()
            return redirect(url_for('upload'))
    return render_template('upload.html', title='Image Upload', form=form)


@app.route('/view_images', methods=['GET', 'POST'])
@login_required
def view_images():
    student_id = current_user.student_id
    images = Image.query.filter_by(student_id=student_id).all()
    counter = Image.query.filter_by(student_id=student_id).count()
    
    delete_forms = {image.image_id: DeleteImageForm() for image in images}
    change_forms = {image.image_id: ChangeImageForm() for image in images}
    
    if request.method == 'POST':
        image_id = int(request.form.get('image_id'))
        action = request.form.get('action')
        image = Image.query.get(image_id)
        
        if action == 'delete':
            form = delete_forms.get(image_id)
            if form and form.validate_on_submit():
                relative_path=image.image_path                
                filename=os.path.basename(relative_path)
                absolute_path = os.path.join(app.config['UPLOAD_FOLDER'], str(student_id), filename)
                
                if os.path.exists(absolute_path):
                    os.remove(absolute_path)
                delete_augmented_images(student_id, image_id)
                    
                        
                db.session.delete(image)
                db.session.commit()
                flash('Image successfully deleted', 'success')
                return redirect(url_for('view_images'))
                
            
        if action == 'change':
            form = change_forms.get(image_id)
            if form and form.validate_on_submit():
                new_image_file = form.new_image.data
                if new_image_file:
                    filename = secure_filename(new_image_file.filename)
                    new_relative_path = os.path.join('images', str(student_id), filename)
                    new_absolute_path = os.path.join(app.config['UPLOAD_FOLDER'], str(student_id), filename)
                    
                    if os.path.exists(new_absolute_path):
                        flash('Image already exists. Only new uploads can be made', 'error')
                        return redirect(url_for('view_images'))
                    
                    old_relative_path=image.image_path
                    old_filename=os.path.basename(old_relative_path)
                    old_absolute_path = os.path.join(app.config['UPLOAD_FOLDER'], str(student_id), old_filename)

                    if os.path.exists(old_absolute_path):
                        os.remove(old_absolute_path)
                    delete_augmented_images(student_id, image_id)
                        
                    new_image_file.save(new_absolute_path)
                    
                    image.image_path = new_relative_path
                    image.upload_date = datetime.now()
                    
                    db.session.commit()
                    threading.Thread(target=augment_images_in_background, args=(student_id, [(filename, image_id)])).start()

                    flash('Image successfully changed', 'success')
                    return redirect(url_for('view_images'))
    
    return render_template('view_images.html', title='View Images', images=images, counter=counter, delete_forms=delete_forms, change_forms=change_forms)






#TEACHER SIDE

@app.route('/upload_lectures', methods=['GET', 'POST'])
@login_required
def upload_lectures():
    form = UploadLectureForm()
    if form.validate_on_submit():
        if form.lecture_file.data:
            unique_str = str(uuid4())
            filename = secure_filename(f'{unique_str}-{form.lecture_file.data.filename}')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            form.lecture_file.data.save(filepath)
            try:
                with open(filepath, newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    error_count = 0
                    row = next(reader)
                    if row != ['Title', 'TeacherId', 'Date']:
                        form.lecture_file.errors.append(
                            'First row of file must be a Header row containing "Title, TeacherId, Date"')
                        raise ValueError('Incorrect header format')
                    
                    for idx, row in enumerate(reader):
                        row_num = idx + 2  # Spreadsheets have the first row as 0, and we skip the header
                        
                        if len(row) != 3:
                            form.lecture_file.errors.append(f'Row {row_num} does not have precisely 3 fields')
                            error_count += 1
                            continue
                        
                        if not Teacher.query.filter_by(teacher_id=row[1]).first():
                            form.lecture_file.errors.append(
                                f'Row {row_num} has TeacherId {row[1]}, which is not registered. Only registered teachers can upload lectures')
                            error_count += 1
                            continue
                        
                        try:
                            # Expecting the date and time in the format "DD/MM/YY HH:MM"
                            date_obj = datetime.strptime(row[2], '%d/%m/%y %H:%M')
                        except ValueError:
                            form.lecture_file.errors.append(f'Row {row_num} has an invalid date format. Expected DD/MM/YY HH:MM')
                            error_count += 1
                            continue
                        
                        if error_count == 0:
                            lecture = Lecture(title=row[0], teacher_id=row[1], date=date_obj)
                            db.session.add(lecture)
                    
                    if error_count > 10:
                        form.lecture_file.errors.append('Too many errors found, any further errors omitted')
                        raise ValueError('Exceeded error limit')
                    
                if error_count > 0:
                    raise ValueError('Errors found in file')
                
                db.session.commit()
                flash('Lectures Uploaded Successfully!', 'success')
                return redirect(url_for('upload_lectures'))
            
            except Exception as e:
                flash(f'Lectures upload failed. Please try again', 'danger')
                db.session.rollback()
            finally:
                silent_remove(filepath)

    return render_template('upload_lectures.html', title='Class Upload', form=form)


@app.route('/view_lectures', methods=['GET', 'POST'])
@login_required
def view_lectures():
    current_date = datetime.now()
    search_query = request.args.get('search', '').strip()
    if search_query:
        lectures = Lecture.query.filter(
            (Lecture.title.ilike(f'%{search_query}%')) |
            (Lecture.lecture_id.ilike(f'%{search_query}%')) |
            (func.strftime('%d/%m', Lecture.date).ilike(f'%{search_query}%'))
        ).all()
    else:
        lectures = Lecture.query.filter_by(teacher_id=current_user.teacher_id).all()
    
    for lecture in lectures:
        time_difference = abs((current_date - lecture.date).total_seconds() / 60)
        lecture.allow_recording = time_difference <= 30
        
        
    return render_template('view_lectures.html', title='View Classes', lectures=lectures, search=search_query, current_date=current_date)


#video
camera = cv2.VideoCapture(0)
identified_students = set()  # Track identified students

def generate_frames(lecture_id, threshold=0.75):
    initialise_attendance(lecture_id)
    
    if not model_files_exist():
        print("Model files do not exist, skipping frame processing.")
        while True:
            success, frame = camera.read()
            if not success:
                break
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    else:
        model, label_encoder = load_trained_model()
        identified_students = set()
        while True:
            success, frame = camera.read()
            if not success:
                break
            face_locations = face_recognition.face_locations(frame)
            if face_locations:
                print('Face location detected:', face_locations)
            else:
                print("No face locations detected.")
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            if face_encodings:
                print("Face encodings detected.")
            else:
                print("No face encodings detected.")

            for face_encoding, face_location in zip(face_encodings, face_locations):
                probabilities = model.predict_proba([face_encoding])[0]
                if max(probabilities) >= threshold:
                    best_match_index = np.argmax(probabilities)
                    student_id = label_encoder.inverse_transform([best_match_index])[0]
                    
                    create_frame(frame, face_location, student_id)

                    if student_id not in identified_students:
                        identified_students.add(student_id)
                        update_attendance(student_id, lecture_id, status='Present', timestamp=datetime.now())
                        print(f"Detected face with confidence {max(probabilities):.2f} above threshold.")
                        print(f"Attendance marked for student: {student_id}")
                else:
                    print(f"Detected face but confidence {max(probabilities):.2f} is below threshold.")

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')



@app.route('/video/<int:lecture_id>')
def video(lecture_id):
    return Response(generate_frames(lecture_id), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/record_attendance/<int:lecture_id>', methods=['GET', 'POST'])
def record_attendance(lecture_id):
    lecture = Lecture.query.filter_by(lecture_id=lecture_id).first()
    return render_template('record_attendance.html', title='Record Lecture', lecture=lecture)


@app.route('/manual_attendance/<int:lecture_id>', methods=['GET', 'POST'])
@login_required
def manual_attendance(lecture_id):
    lecture = Lecture.query.filter_by(lecture_id=lecture_id).first()
    students = Student.query.all()

    # Fetch attendance records for the specific lecture
    attendance_records = db.session.query(
        Student.student_id,
        Student.first_name,
        Student.last_name,
        Attendance.lecture_id,
        Attendance.status
    ).join(Attendance, Student.student_id == Attendance.student_id).filter(Attendance.lecture_id == lecture_id).all()
    
    if request.method == 'POST':
        for record in attendance_records:
            current_status = record.status
            student_id = record.student_id
            new_status = request.form.get(str(student_id))
            
            if new_status != current_status:
                Attendance.query.filter_by(student_id=student_id, lecture_id=lecture_id).update({
                    'status': new_status,
                    'timestamp': datetime.now()
                })
        
        db.session.commit()
        flash('Attendance updated successfully', 'success')
        return redirect(url_for('manual_attendance', lecture_id=lecture_id))

    return render_template('manual_attendance.html', title='Manual Attendance', students=students, attendance_records=attendance_records, lecture=lecture)

@app.route('/view_attendance', methods=['GET', 'POST'])
@login_required
def view_attendance():
    search_query = request.args.get('search', '').strip()
    if search_query:
        students =  Student.query.filter(
            (Student.student_id.ilike(f'%{search_query}%')) |
            (Student.first_name.ilike(f'%{search_query}%')) |
            (Student.last_name.ilike(f'%{search_query}%'))
        ).all()
    else:
        students = Student.query.all()
    
    for student in students:
        # Calculate the number of lectures for which attendance records exist for the student
        lectures_with_records = db.session.query(Attendance.lecture_id).filter_by(student_id=student.student_id).distinct().count()
        
        # Calculate the number of lectures the student attended
        attended_lectures = Attendance.query.filter_by(student_id=student.student_id, status='Present').count()

        # Calculate attendance percentage based on lectures that have attendance records
        if lectures_with_records > 0:
            attendance_percentage = (attended_lectures / lectures_with_records) * 100
        else:
            attendance_percentage = 0
        
        student.attendance_percentage = f'{attendance_percentage:.2f}%'

    return render_template('view_attendance.html', title='View Attendance', students=students, search=search_query)


@app.route('/attendance_report/<int:student_id>', methods=['GET', 'POST'])
@login_required
def attendance_report(student_id):
    student = Student.query.filter_by(student_id=student_id).first()
    search_query = request.args.get('search', '').strip()

    base_query = db.session.query(
        Lecture.lecture_id,
        Lecture.teacher_id,
        Lecture.title,
        Lecture.date,
        Attendance.status,
        Attendance.timestamp
    ).join(Attendance, Lecture.lecture_id == Attendance.lecture_id).filter(Attendance.student_id == student_id)

    if search_query:
        base_query = base_query.filter(
            (Lecture.lecture_id.ilike(f'%{search_query}%')) |
            (Lecture.title.ilike(f'%{search_query}%'))
        )

    attendance_records = base_query.all()

    return render_template('attendance_report.html', title='Attendance Report', student=student, attendance_records=attendance_records, search=search_query)






@app.route('/delete_lectures')
@login_required
def delete_lectures():
    lectures = Lecture.query.all()
    for lecture in lectures:
        db.session.delete(lecture)
    db.session.commit()
    return "Lectures deleted successfully."








@app.errorhandler(413)
def error_413(error):
    return render_template('errors/413.html', title='413 Payload Too Large'), 413

@app.errorhandler(403)
def error_403(error):
    return render_template('errors/403.html', title='403 Access Denied'), 403

@app.errorhandler(404)
def error_404(error):
    return render_template('errors/404.html', title='404 Not Found'), 404

@app.errorhandler(500)
def error_500(error):
    return render_template('errors/500.html', title='500 Server Error'), 500
