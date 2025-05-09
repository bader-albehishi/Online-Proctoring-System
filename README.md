# 🎓 Online Proctoring System

A comprehensive AI-powered solution for remote exam monitoring, authentication, and management.

## 📋 Overview

This system provides a secure environment for conducting online exams with advanced monitoring capabilities to maintain academic integrity. It integrates multiple AI technologies to detect various forms of suspicious behavior during remote testing.

---

## 🚀 Features

### 👤 Authentication & Security
- **Facial Recognition:** Secure identity verification using DeepFace
- **Continuous Identity Checking:** Periodic verification during exam sessions
- **Secure Login:** Two-factor authentication with biometric verification

### 📹 Visual Monitoring
- **Face Detection:** Ensures student presence throughout exam
- **Head Pose Estimation:** Detects when students look away from screen
- **Eye Tracking:** Monitors suspicious eye movements
- **Object Detection:** Identifies mobile phones and additional persons using YOLOv3

### 🎤 Audio Monitoring
- **Speech Recognition:** Transcribes and analyzes spoken content
- **Keyword Detection:** Flags suspicious keywords in conversations
- **Audio Chunking:** Splits audio based on silence to analyze specific segments

### 💻 Browser Activity Monitoring
- **Window Focus Detection:** Tracks app/tab switching
- **Clipboard Monitoring:** Captures copied content
- **Active Window Logging:** Records titles of active windows

### 📝 Exam Management
- **Multiple Question Types:** Supports objective, subjective, and practical assessments
- **Randomized Questions:** Different order for each student
- **Auto-grading:** Immediate results for objective questions
- **Manual Grading Interface:** For subjective answers

### 👨‍💼 Instructor Dashboard
- **Live Monitoring:** Real-time view of all active sessions
- **Alert System:** Notifications for suspicious activities
- **Session Recordings:** Complete exam playback with timestamps
- **Analytics:** Statistical breakdown of integrity violations

---

## 🛠️ Technical Architecture

### Backend Components
- **Flask Application Server:** Handles web requests and serves content
- **WebSocket Server:** Manages real-time communication
- **MySQL Database:** Stores user data, exam information, and logs
- **AI Processing Modules:**
  - Computer vision pipeline for image analysis
  - Audio processing for speech recognition
  - NLP for text analysis

### Frontend Components
- **Student Exam Interface:** Responsive UI for taking tests
- **Instructor Dashboard:** Monitoring and management interface
- **Admin Panel:** System configuration and user management

### AI Models
- **Face Detection:** SSD and ResNet models
- **Object Detection:** YOLOv3 custom trained model
- **Gaze Tracking:** Custom eye movement analysis
- **Speech Recognition:** Google Speech API integration
- **Facial Recognition:** DeepFace verification

---

## 💻 Usage

### For Students
1. Register an account with your institutional email
2. Complete identity verification process
3. Join scheduled exams using provided test ID and password
4. Follow on-screen instructions for the proctoring setup
5. Complete your exam while maintaining proper examination conduct

