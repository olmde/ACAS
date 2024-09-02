from flask_mail import Message
from app import mail, app, db
from flask import url_for, flash
import re
import os
from PIL import Image
import random
import tensorflow as tf
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from tensorflow.keras.preprocessing.image import ImageDataGenerator, img_to_array, load_img
import numpy as np
from  app.models import Image
import fnmatch
import cv2
import dlib
import tensorflow as tf
from app.recognition import train_model
import threading
import sqlite3
from datetime import datetime
from app.models import Student, Lecture, Attendance

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
predictor_path = os.path.join(os.path.dirname(__file__), 'shape_predictor_68_face_landmarks.dat')
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat') 

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender='attendance@portal.ac.uk',
                  recipients=[user.email])
    msg.body = f'''To reset your password, please visit the following link:
{url_for('reset_token', token=token, _external=True)}

If you did not make this request then simply ignore this email and no changes will be made.
'''

    with mail.connect() as conn:
        conn.send(msg)

def create_student_directory(student_id):
    '''
    Creating a directory to store student's individual images based on respective student IDs
    '''
    student_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(student_id))
    if not os.path.exists(student_folder):
        os.makedirs(student_folder)

def create_augmented_student_directory(student_id):
    '''
    Creating directory to store augmented images of student based on uploaded images in respective image folder
    '''
    augmented_student_folder = os.path.join(app.config['AUGMENTED_FOLDER'], str(student_id))
    if not os.path.exists(augmented_student_folder):
        os.makedirs(augmented_student_folder)

def silent_remove(filepath):
    '''
    Function to remove filepath and silently cancel any exceptions in the presence of failure
    '''
    try:
        os.remove(filepath)
    except:
        pass
    return

def load_images(student_id, new_filenames):  
    student_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(student_id))
    images = []
    if os.listdir(student_folder):
        for new_filename in new_filenames:                
            absolute_image_path = os.path.join(student_folder, new_filename)
            image = load_img(absolute_image_path)
            image_array = img_to_array(image)
            images.append(image_array)
            
        return images

def adjust_image_lighting(images):
    '''
    function to adjust brightness and contrast of augmented images
    '''
    adjusted_images = []
    for image in images:
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        #randomly adjusting image contrast, <1 means decrease contrast, <1 measn increased contrast
        alpha = np.random.uniform(0.8, 1.2)
        beta = np.random.randint(-30, 30)
        adjusted_image = cv2.convertScaleAbs(image_bgr,alpha=alpha, beta=beta)
        adjusted_image_rgb = cv2.cvtColor(adjusted_image, cv2.COLOR_BGR2RGB)
        adjusted_images.append(adjusted_image_rgb)
    
    return adjusted_images

def blend_eye_region(image, transformed_region, eye_rect):
    '''
    Blends the transformed eye region back into the original image
    '''
    x, y, w, h = eye_rect
    for i in range(h):
        for j in range(w):
            if (transformed_region[i, j] != 0).all():
                image[y + i, x + j] = transformed_region[i, j]

def blend_left_eye(image, transformed_region, eye_rect):
    blend_eye_region(image, transformed_region, eye_rect)

def blend_right_eye(image, transformed_region, eye_rect):
    blend_eye_region(image, transformed_region, eye_rect)

def change_eye_direction(images):
    '''
    Function to detect eyes in images and randomly change their direction
    '''
    adjusted_images = []

    for image in images:
        image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        faces = detector(image_gray)

        if not faces:
            # If no faces are detected, append the original image
            adjusted_images.append(image)
            continue

        for face in faces:
            landmarks = predictor(image_gray, face)

            left_eye_points = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(36, 42)]
            right_eye_points = [(landmarks.part(i).x, landmarks.part(i).y) for i in range(42, 48)]

            left_eye_rect = cv2.boundingRect(np.array(left_eye_points))
            right_eye_rect = cv2.boundingRect(np.array(right_eye_points))

            left_eye_region = image[left_eye_rect[1]:left_eye_rect[1]+left_eye_rect[3], left_eye_rect[0]:left_eye_rect[0]+left_eye_rect[2]]
            right_eye_region = image[right_eye_rect[1]:right_eye_rect[1]+right_eye_rect[3], right_eye_rect[0]:right_eye_rect[0]+right_eye_rect[2]]

            shift_x = np.random.randint(-15, 15)
            shift_y = np.random.randint(-15, 15)
            M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])

            left_eye_transformed = cv2.warpAffine(left_eye_region, M, (left_eye_region.shape[1], left_eye_region.shape[0]))
            right_eye_transformed = cv2.warpAffine(right_eye_region, M, (right_eye_region.shape[1], right_eye_region.shape[0]))

            # Create a new image copy only once per face
            new_image = image.copy()

            # Blend the transformed regions back into the image
            blend_left_eye(new_image, left_eye_transformed, left_eye_rect)
            blend_right_eye(new_image, right_eye_transformed, right_eye_rect)

            # Append the modified image to adjusted_images
            adjusted_images.append(new_image)

    return adjusted_images


            # 68 different landmarks, 36-45 are eyes
            # getting x,y coords for indicated landmarks (eyes)

def augment_and_save_images(images, student_id, image_id, num_augmented=10):
    '''
    Function to augment images by specified values and save to augmented_images directory for respective student
    '''
    
    student_image_folder = os.path.join(app.config['AUGMENTED_FOLDER'], str(student_id))
    if not os.path.exists(student_image_folder):
        os.makedirs(student_image_folder)
        
    datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=5,
        horizontal_flip=True,
        fill_mode='nearest',
    ) 
    
    augment_counter = 1
    for image_index, image_array in enumerate(images):
        x = image_array.reshape((1,) + image_array.shape)  # Reshape to (1, height, width, channels)

        # Generate augmented images
        for batch in datagen.flow(x, batch_size=1):
            augmented_image = batch[0] 
            
            augmented_image = augmented_image * 255.0
            augmented_image = np.clip(augmented_image, 0, 255).astype(np.uint8)
            
            lighting_adjusted_images = adjust_image_lighting([augmented_image])
            
            # Apply eye direction changes
            fully_adjusted_images = change_eye_direction(lighting_adjusted_images)  
            
            for adjusted_image in fully_adjusted_images:
                save_path = os.path.join(student_image_folder, f'aug_{student_id}_{image_id}_{augment_counter}.jpg')
                cv2.imwrite(save_path, cv2.cvtColor(adjusted_image, cv2.COLOR_RGB2BGR))
                
                augment_counter += 1
                if augment_counter >= num_augmented:
                    break
            if augment_counter >= num_augmented:
                break

def augment_images_in_background(student_id, images_with_ids):
    '''
    Function to combine all augmentation functions to use as single thread in views file
    '''
    with app.app_context():
        for filename, image_id in images_with_ids:
            loaded_images = load_images(student_id, [filename])
            augment_and_save_images(loaded_images, student_id, image_id)

def delete_augmented_images(student_id, image_id):
    '''
    Function to delete augmented images for a given student and image ID
    '''
    augmented_file_pattern =  f'aug_{student_id}_{image_id}_*.jpg' #using this pattern to implement fnmatch to compare each augmented filer against 
    augmented_dir = os.path.join(app.config['AUGMENTED_FOLDER'], str(student_id))
                    
    for augmented_file in os.listdir(augmented_dir):
        if fnmatch.fnmatch(augmented_file, augmented_file_pattern):
            os.remove(os.path.join(augmented_dir,augmented_file))

def train_model_in_background(images_directory):
    '''
    function to create new thread to train facial recognition model with dataset of student augmented images
    '''
    threading.Thread(target=train_model, args=(images_directory,), daemon=True).start()
    
def silent_remove(filepath):
    try:
        os.remove(filepath)
    except OSError as e:
        print(f"Error removing file {filepath}: {e}")
        
def initialise_attendance(lecture_id):
    '''
    Function to initialise attendance records for all students with default status 'Absent'.
    '''
    with app.app_context():
        all_students = Student.query.all()
        for student in all_students:
            attendance = Attendance.query.filter_by(student_id=student.student_id, lecture_id=lecture_id).first()
            if attendance is None:
                new_attendance = Attendance(
                    lecture_id=lecture_id,
                    student_id=student.student_id,
                    status='Absent',
                    timestamp=datetime.now(),
                )
                db.session.add(new_attendance)
        db.session.commit()

def update_attendance(student_id, lecture_id, status, timestamp):
    '''
    Function to mark attendance of students from video feed.
    '''
    with app.app_context():
        attendance = Attendance.query.filter_by(student_id=student_id, lecture_id=lecture_id).first()
        if attendance and attendance.status != 'Present':
            attendance.timestamp = timestamp
            attendance.status = status
            db.session.commit()
            print(f"Attendance updated to {status} for student ID {student_id} for lecture ID {lecture_id}")

