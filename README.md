# visitor-pass-and-access-control-management
# Visitor Pass & Access Control Management System

A web-based Visitor Pass and Access Control Management System developed using Flask and MongoDB. The system enables secure visitor registration, QR-code based authentication, zone-based access control, and real-time visitor monitoring.

---

## Features

- Visitor Registration System
- QR Code Pass Generation
- Zone-Based Access Control
- Admin Dashboard
- Receptionist Interface
- Security QR Scanner
- Real-Time Visitor Tracking
- Access Approval & Denial System
- Printable Visitor Passes

---

## Technologies Used

### Frontend
- HTML
- CSS
- JavaScript

### Backend
- Flask (Python)

### Database
- MongoDB

### Additional Libraries
- Flask-Login
- qrcode
- PyMongo

---

## Project Modules

### Admin Module
- Manage Users
- Manage Zones
- View Visitor Analytics
- Monitor Access Logs

### Receptionist Module
- Register Visitors
- Generate Visitor Passes
- Assign Access Zones

### Security Module
- Scan QR Codes
- Validate Visitor Access
- Grant/Deny Zone Entry

---

## System Workflow

1. Receptionist registers visitor details
2. QR-based visitor pass is generated
3. Security scans QR code
4. System validates authorized zones
5. Access is granted or denied
6. Entry logs are stored in MongoDB

---

## Screenshots

### Login Page
<img width="659" height="836" alt="Screenshot (61)" src="https://github.com/user-attachments/assets/e9d9b2cb-7f8f-4500-9568-613755035e58" />


### Admin Dashboard
<img width="1881" height="923" alt="Screenshot (71)" src="https://github.com/user-attachments/assets/f14b02e0-6fe7-4e7b-b2c0-f918798f9ef1" />



### QR Scanner
<img width="1920" height="1080" alt="Screenshot (66)" src="https://github.com/user-attachments/assets/1c9730de-a71c-461b-b660-6bfb7148f2cc" />


### Visitor Pass
<img width="1338" height="847" alt="Screenshot (65)" src="https://github.com/user-attachments/assets/b9f2d02c-4c67-4216-8a85-d4c3844d2687" />


---

## Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/visitor-pass-management.git
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
python app.py
```

---

## Future Enhancements

- Face Recognition Integration
- Email/SMS Notifications
- Advanced Visitor Analytics
- Employee Directory Integration
- Mobile Application Support

---

## Author

Misbah Koukab
