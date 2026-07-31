# 🌿 CropDiseaseAI

> **AI-Powered Crop Disease Detection and Advisory System**

CropDiseaseAI is an AI-powered web application that helps farmers, students, and agriculture enthusiasts identify crop diseases using Artificial Intelligence. Users can upload a crop leaf image, and the application analyzes it using **Google Gemini Vision AI** to generate a detailed disease report along with treatment guidance and farming recommendations.

---

## 📸 Demo

🌐 Live Website

https://cropdisease-liard.vercel.app/

---

## ✨ Features

### 🤖 AI Disease Detection

- Upload a crop leaf image
- AI-powered disease identification
- Crop recognition
- Disease severity estimation
- AI-assisted diagnosis

---

### 📋 Detailed Disease Report

The system generates:

- Crop Name
- Disease Name
- AI Confidence Level
- Severity
- Symptoms
- Possible Causes
- Prevention Methods
- Treatment Guidance
- Fertilizer Recommendation
- Water Management Advice
- Additional Notes

---

### 🌦 Smart Weather Advisory *(Upcoming)*

Provides:

- Current Weather
- Temperature
- Humidity
- Rain Probability
- Wind Speed
- Seven-Day Forecast
- Disease Risk Analysis
- Spray Suitability
- Irrigation Recommendation

---

### 🌱 Treatment Guidance *(Upcoming)*

Includes:

- Immediate Actions
- Organic Management
- Biological Control
- Chemical Treatment
- Active Ingredient
- Application Method
- Safety Precautions
- Recovery Monitoring

---

### 👤 User Management

- Secure Login
- User Registration
- Authentication
- User Profile

---

### 📚 Prediction History

- View Previous Scans
- Download Reports
- Search History
- Filter Results

---

### 🌍 Multilingual Support

Supports multiple languages for better accessibility.

---

### 📱 Responsive Design

Optimized for:

- Desktop
- Tablet
- Mobile

---

## 🛠 Tech Stack

### Frontend

- HTML5
- Tailwind CSS
- JavaScript

### Backend

- Python
- Flask

### Artificial Intelligence

- Google Gemini Vision API

### Database

- SQLite

### Authentication

- Flask Session Authentication

### Deployment

- Vercel

---

## 🚀 Project Workflow

```text
User Uploads Leaf Image
          │
          ▼
Image Validation
          │
          ▼
Google Gemini Vision AI
          │
          ▼
Disease Analysis
          │
          ▼
Generate AI Report
          │
          ▼
Display Recommendations
```

---

## 📂 Project Structure

```
CropDiseaseAI
│
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│
├── templates/
│
├── uploads/
│
├── database/
│
├── app.py
├── ai_service.py
├── config.py
├── requirements.txt
├── vercel.json
└── README.md
```

---

## ⚙ Installation

### Clone Repository

```bash
git clone https://github.com/pratap-varma/crop-disease-ai.git
```

Move into the project

```bash
cd crop-disease-ai
```

Create Virtual Environment

```bash
python -m venv venv
```

Activate Environment

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

Install Dependencies

```bash
pip install -r requirements.txt
```

Create Environment File

```
GEMINI_API_KEY=YOUR_API_KEY
```

Run Application

```bash
python app.py
```

Open

```
http://127.0.0.1:5000
```

---

## 📷 How to Use

1. Open the website.
2. Login or Register.
3. Select the crop.
4. Upload a clear crop leaf image.
5. Click **Analyze**.
6. View the AI-generated disease report.
7. Read treatment guidance.
8. Save the report.

---

## 🎯 Project Objectives

- Early crop disease identification.
- Reduce crop losses.
- Assist farmers with AI.
- Improve farming decisions.
- Increase awareness of crop diseases.
- Promote sustainable agriculture.

---

## 🌍 Future Enhancements

- Weather Intelligence
- Verified Treatment Database
- AI Chat Assistant
- Mobile Application
- Offline Disease Detection
- Voice Assistant
- GPS-Based Advisory
- IoT Integration
- Drone Image Analysis
- Government Advisory Integration
- PDF Report Generation
- Disease Outbreak Prediction

---

## ⚠ Disclaimer

CropDiseaseAI is an **AI-powered decision-support system**.

The analysis provided by the application should be considered as guidance and not as a replacement for professional agricultural advice.

Before applying pesticides, fungicides, or other crop protection products, users should consult local agricultural experts and always follow official product labels and regional agricultural regulations.

---

## 👨‍💻 Developer

**UPPALAPATI PRATAP VARMA**

B.Tech Artificial Intelligence & Machine Learning

MVGR College of Engineering

GitHub

https://github.com/pratap-varma

LinkedIn

(Add your LinkedIn URL)

Email

pratapvarmauppalapati6@gmail.com

---

## ⭐ Support

If you found this project useful, consider giving the repository a ⭐ on GitHub.

---

## 📜 License

This project is developed for educational and research purposes.
