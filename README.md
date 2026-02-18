# ACAS – Automated Classroom Attendance System

ACAS is a Flask‑based web application that automates classroom attendance using facial recognition. Students upload images to train the model, and teachers take attendance automatically through their webcam during scheduled lectures.

---

## 🚀 Overview

ACAS provides an automated, accurate roll‑call system by recognising students’ faces in real time.

It includes two main user flows:

### **Students**
- Register with basic details (full name, email, password (which becomes hashed) and more).
- Upload photos of themselves.
- Model generates facial embeddings from these images.
- Embeddings are mapped to the student's **unique ID**.

### **Teachers**
- Log in to access their teaching timetable.
- Select a lecture/lesson from their schedule.
- Start an automatic attendance session using a webcam.
- ACAS detects and recognises **only students enrolled** in that lecture.

---

## 🧱 Built With
- **Flask (Python)** – backend framework  
- **HTML / CSS / JavaScript** – user interface  
- **OpenCV + dlib/face_recognition** – face detection + recognition  
- **68‑point facial landmark model** – used to extract facial features  
- **Local storage / CSV** – attendance logs, registries, embeddings  

---

## 🧠 Machine Learning Model

ACAS uses a standard face‑recognition pipeline:

### **1. Face Detection**
- Detects faces in webcam frames using OpenCV/dlib.

### **2. Landmark Detection**
- Uses a **68‑point landmark model** (eyes, nose, jawline, mouth).

### **3. Facial Embeddings**
- Student images are converted into numerical vectors.
- Stored securely and linked to the student’s ID.

### **4. Recognition**
- Live webcam frames generate new embeddings.
- Compared against enrolled students for the selected class.
- Matches = students marked **Present**.



Logs can be exported or integrated into external MIS systems.

---

## ▶️ Running the App

```bash
# Install dependencies
pip install -r requirements.txt
  
    
## Run Locally

Clone the project

```bash
  git clone https://github.com/olmde/ACAS.git
```

Go to the project directory

```bash
  cd ACAS
```


Start the server

```bash
  flask run
```

# Start the Flask app
python run.py

# Open in browser
http://localhost:5000
