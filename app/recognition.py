import face_recognition
import os
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import joblib  # Import joblib
import cv2 as cv
import concurrent.futures

def encode_face(image_path):
    try:
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        if face_encodings:
            return face_encodings[0], os.path.basename(os.path.dirname(image_path))
    except Exception as e:
        print(f"Skipping file {image_path}: {e}")
    return None, None

def load_and_encode_images(images_directory):
    encoded_faces = []
    labels = []
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for student_id in os.listdir(images_directory):
            student_dir = os.path.join(images_directory, student_id)
            if os.path.isdir(student_dir):
                for image_name in os.listdir(student_dir):
                    image_path = os.path.join(student_dir, image_name)
                    futures.append(executor.submit(encode_face, image_path))
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result[0] is not None:
                encoded_faces.append(result[0])
                labels.append(result[1])
    return np.array(encoded_faces), np.array(labels)



def train_model(images_directory):
    
    '''
    function to train the model with given data and labels from encoded images
    '''
    X, y = load_and_encode_images(images_directory) # mapping (x=data, y=labels) --> (x=encoding, y=student_id)

    #encoding labels (converting from string to numerical value) 'y_encoded'=int(student_id)
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)

    # Split the data into training and testing.
    # each x (encoding) and corresponding y_encoded(label) will be split. 
    #0.2 = 20% of data used for testing and 8-% used fpr training
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    # Train a Support Vector Machine classifier
    model = SVC(kernel='linear', probability=True)
    model.fit(X_train, y_train) #teach model to map x(encodings) with y(labels)
    

    # Save the model and label encoder using joblib
    joblib.dump(model, 'face_recognition_model.pkl')
    joblib.dump(label_encoder, 'label_encoder.pkl')

    # Evaluate the model
    accuracy = model.score(X_test, y_test)
    print(f'Model accuracy: {accuracy * 100:.2f}%')

def load_trained_model():
    '''
    Load the trained SVM model and label encoder
    '''
    model_path = 'face_recognition_model.pkl'
    label_encoder_path = 'label_encoder.pkl'
    if not os.path.exists(model_path) or not os.path.exists(label_encoder_path):
        raise FileNotFoundError('Model or label encoder file not found. Please train the model first.')
    model = joblib.load(model_path)
    label_encoder = joblib.load(label_encoder_path)
    return model, label_encoder


def create_frame(frame, location, label, color=(255, 0, 0), font_scale=0.8):
    '''
    Function to create frame around detected faces in feed and specified textboxes
    '''
    top, right, bottom, left = location
    # Draw a rectangle around the face
    cv.rectangle(frame, (left, top), (right, bottom), color, 2)
    # Draw a label underneath the face
    cv.rectangle(frame, (left, bottom - 20), (right, bottom), color, cv.FILLED)
    font = cv.FONT_HERSHEY_DUPLEX
    cv.putText(frame, label, (left + 6, bottom - 6), font, font_scale, (255, 255, 255), 1)


def model_files_exist():
    return os.path.exists('face_recognition_model.pkl') and os.path.exists('label_encoder.pkl')



