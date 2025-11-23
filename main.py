from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import sqlite3
from datetime import datetime, timedelta
import json
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import os
import random
import csv
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'face-attendance-secret-2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Utility functions - DEFINED FIRST
def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    # Remove existing database to start fresh
    if os.path.exists('attendance.db'):
        os.remove('attendance.db')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            student_id TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Courses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            instructor_id INTEGER,
            schedule TEXT,
            room TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (instructor_id) REFERENCES users (id)
        )
    ''')
    
    # Enrollments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')
    
    # Attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            course_id INTEGER,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            recognized_confidence REAL,
            method TEXT DEFAULT 'auto',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')
    
    # Insert sample data
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # Add sample instructor
        cursor.execute('''
            INSERT INTO users (username, password, role, name, email, phone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('professor', 'password', 'instructor', 'Dr. Sarah Johnson', 's.johnson@university.edu', '+1-555-0101'))
        
        # Add sample students
        students = [
            ('student1', 'password', 'student', 'Alice Chen', 'alice.chen@student.edu', 'S1001', '+1-555-0102'),
            ('student2', 'password', 'student', 'Bob Rodriguez', 'bob.rodriguez@student.edu', 'S1002', '+1-555-0103'),
            ('student3', 'password', 'student', 'Carol Williams', 'carol.williams@student.edu', 'S1003', '+1-555-0104'),
            ('student4', 'password', 'student', 'David Kim', 'david.kim@student.edu', 'S1004', '+1-555-0105'),
            ('student5', 'password', 'student', 'Eva Martinez', 'eva.martinez@student.edu', 'S1005', '+1-555-0106'),
        ]
        
        for student in students:
            cursor.execute('''
                INSERT INTO users (username, password, role, name, email, student_id, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', student)
        
        # Add sample courses
        courses = [
            ('CAP5178', 'Human-Computer Interaction', 1, 'Mon/Wed 10:00-11:30', 'Room 301'),
            ('CIS4930', 'Advanced HCI', 1, 'Tue/Thu 14:00-15:30', 'Room 205'),
        ]
        
        for course in courses:
            cursor.execute('''
                INSERT INTO courses (code, name, instructor_id, schedule, room)
                VALUES (?, ?, ?, ?, ?)
            ''', course)
        
        # Enroll students in courses
        for student_id in range(2, 7):  # Students 2-6
            cursor.execute('''
                INSERT INTO enrollments (student_id, course_id)
                VALUES (?, ?)
            ''', (student_id, 1))  # All in CAP5178
            
            if student_id <= 5:  # Some in CIS4930
                cursor.execute('''
                    INSERT INTO enrollments (student_id, course_id)
                    VALUES (?, ?)
                ''', (student_id, 2))
        
        # Add sample attendance records
        today = datetime.now()
        for i in range(5):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            for student_id in range(2, 7):
                if random.random() > 0.2:  # 80% attendance rate
                    cursor.execute('''
                        INSERT INTO attendance (student_id, course_id, date, status, timestamp, recognized_confidence, method)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        student_id, 1, date, 'present',
                        f"{random.randint(9, 11)}:{random.randint(10, 59)}:{random.randint(10, 59)}",
                        random.uniform(85.0, 98.0), 'auto'
                    ))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def mark_attendance(student_id, course_id, confidence=None, method='auto'):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    
    # Check if already marked today
    cursor.execute('''
        SELECT id FROM attendance 
        WHERE student_id = ? AND course_id = ? AND date = ?
    ''', (student_id, course_id, today))
    
    existing = cursor.fetchone()
    if existing:
        # Update existing record
        cursor.execute('''
            UPDATE attendance 
            SET status = 'present', timestamp = ?, recognized_confidence = ?, method = ?
            WHERE id = ?
        ''', (current_time, confidence, method, existing['id']))
    else:
        # Insert new record
        cursor.execute('''
            INSERT INTO attendance (student_id, course_id, date, status, timestamp, recognized_confidence, method)
            VALUES (?, ?, ?, 'present', ?, ?, ?)
        ''', (student_id, course_id, today, current_time, confidence, method))
    
    conn.commit()
    conn.close()

def get_course_stats(course_id):
    """Get comprehensive course statistics"""
    conn = get_db_connection()
    
    # Total enrolled students
    total_students = conn.execute('''
        SELECT COUNT(*) FROM enrollments WHERE course_id = ?
    ''', (course_id,)).fetchone()[0]
    
    # Today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    today_present = conn.execute('''
        SELECT COUNT(DISTINCT student_id) FROM attendance 
        WHERE course_id = ? AND date = ? AND status = 'present'
    ''', (course_id, today)).fetchone()[0]
    
    conn.close()
    
    return {
        'total_students': total_students,
        'today_present': today_present,
        'attendance_rate': round((today_present / total_students * 100) if total_students > 0 else 0, 1)
    }

# Face Detection System - SIMPLIFIED VERSION
class FaceDetectionSystem:
    """Simple face detection system for demo"""
    
    def __init__(self):
        self.student_data = {
            2: {'name': 'Alice Chen', 'student_id': 'S1001'},
            3: {'name': 'Bob Rodriguez', 'student_id': 'S1002'},
            4: {'name': 'Carol Williams', 'student_id': 'S1003'},
            5: {'name': 'David Kim', 'student_id': 'S1004'},
            6: {'name': 'Eva Martinez', 'student_id': 'S1005'}
        }
    
    def detect_faces(self, image_data):
        """Simulate face detection for demo"""
        try:
            # Simulate processing time
            import time
            time.sleep(1)
            
            # Return 0-2 random recognitions
            num_faces = random.randint(0, 2)
            recognized_faces = []
            
            for i in range(num_faces):
                student_id = random.choice(list(self.student_data.keys()))
                recognized_faces.append({
                    'user_id': student_id,
                    'name': self.student_data[student_id]['name'],
                    'student_id': self.student_data[student_id]['student_id'],
                    'confidence': round(random.uniform(85.0, 98.0), 1),
                    'location': (100 + i*50, 100, 200, 200),
                    'eyes_detected': True,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
            
            return recognized_faces
            
        except Exception as e:
            print(f"Face detection error: {e}")
            # Return demo data for testing
            return [{
                'user_id': 2,
                'name': 'Alice Chen', 
                'student_id': 'S1001',
                'confidence': 92.3,
                'location': (100, 100, 200, 200),
                'eyes_detected': True,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            }]

# Initialize database and face system
init_db()
face_system = FaceDetectionSystem()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'instructor':
            return redirect('/instructor/dashboard')
        else:
            return redirect('/student/dashboard')
    return render_template('auth/login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, role, name FROM users WHERE username = ? AND password = ?', 
                   (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['name'] = user['name']
        
        return jsonify({
            'success': True,
            'redirect': '/instructor/dashboard' if user['role'] == 'instructor' else '/student/dashboard'
        })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Instructor Routes
@app.route('/instructor/dashboard')
def instructor_dashboard():
    if session.get('role') != 'instructor':
        return redirect('/')
    
    conn = get_db_connection()
    
    # Get instructor's courses with stats
    courses = conn.execute('''
        SELECT c.*, 
               COUNT(DISTINCT e.student_id) as enrolled_count
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id
        WHERE c.instructor_id = ?
        GROUP BY c.id
    ''', (session['user_id'],)).fetchall()
    
    # Get overall statistics
    total_students = conn.execute('''
        SELECT COUNT(DISTINCT student_id) FROM enrollments 
        WHERE course_id IN (SELECT id FROM courses WHERE instructor_id = ?)
    ''', (session['user_id'],)).fetchone()[0]
    
    today = datetime.now().strftime('%Y-%m-%d')
    today_attendance = conn.execute('''
        SELECT COUNT(DISTINCT student_id) FROM attendance 
        WHERE date = ? AND course_id IN (
            SELECT id FROM courses WHERE instructor_id = ?
        )
    ''', (today, session['user_id'])).fetchone()[0]
    
    conn.close()
    
    return render_template('instructor/dashboard.html',
                         courses=courses,
                         total_students=total_students,
                         today_attendance=today_attendance,
                         name=session.get('name'),
                         now=datetime.now())

@app.route('/instructor/courses')
def instructor_courses():
    if session.get('role') != 'instructor':
        return redirect('/')
    
    conn = get_db_connection()
    courses = conn.execute('''
        SELECT c.*, COUNT(DISTINCT e.student_id) as student_count
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id
        WHERE c.instructor_id = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('instructor/courses.html',
                         courses=courses,
                         name=session.get('name'))

@app.route('/instructor/students')
def instructor_students():
    if session.get('role') != 'instructor':
        return redirect('/')
    
    conn = get_db_connection()
    
    # Get all students with their enrollment info
    students = conn.execute('''
        SELECT u.*, 
               GROUP_CONCAT(c.name, ', ') as courses,
               COUNT(DISTINCT c.id) as course_count
        FROM users u
        JOIN enrollments e ON u.id = e.student_id
        JOIN courses c ON e.course_id = c.id
        WHERE u.role = 'student' AND c.instructor_id = ?
        GROUP BY u.id
        ORDER BY u.name
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('instructor/students.html',
                         students=students,
                         name=session.get('name'))

@app.route('/instructor/live-attendance/<int:course_id>')
def live_attendance(course_id):
    if session.get('role') != 'instructor':
        return redirect('/')
    
    conn = get_db_connection()
    
    # Verify course belongs to instructor
    course = conn.execute('''
        SELECT c.*, COUNT(DISTINCT e.student_id) as total_students
        FROM courses c
        LEFT JOIN enrollments e ON c.id = e.course_id
        WHERE c.id = ? AND c.instructor_id = ?
        GROUP BY c.id
    ''', (course_id, session['user_id'])).fetchone()
    
    if not course:
        conn.close()
        return redirect('/instructor/dashboard')
    
    # Get enrolled students
    students = conn.execute('''
        SELECT u.id, u.name, u.student_id, u.email
        FROM users u
        JOIN enrollments e ON u.id = e.student_id
        WHERE e.course_id = ? AND u.role = 'student'
        ORDER BY u.name
    ''', (course_id,)).fetchall()
    
    # Get today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    present_students = conn.execute('''
        SELECT student_id FROM attendance 
        WHERE course_id = ? AND date = ? AND status = 'present'
    ''', (course_id, today)).fetchall()
    present_ids = [row['student_id'] for row in present_students]
    
    conn.close()
    
    return render_template('instructor/live-attendance.html',
                         course=course,
                         students=students,
                         present_students=present_ids,
                         today=today)

@app.route('/instructor/attendance-history/<int:course_id>')
def attendance_history(course_id):
    if session.get('role') != 'instructor':
        return redirect('/')
    
    conn = get_db_connection()
    
    course = conn.execute('''
        SELECT * FROM courses 
        WHERE id = ? AND instructor_id = ?
    ''', (course_id, session['user_id'])).fetchone()
    
    if not course:
        conn.close()
        return redirect('/instructor/dashboard')
    
    # Get attendance dates with stats
    dates = conn.execute('''
        SELECT date, 
               COUNT(DISTINCT student_id) as present_count
        FROM attendance 
        WHERE course_id = ? 
        GROUP BY date 
        ORDER BY date DESC
        LIMIT 30
    ''', (course_id,)).fetchall()
    
    conn.close()
    
    return render_template('instructor/attendance-history.html',
                         course=course,
                         dates=dates)

@app.route('/instructor/reports')
def instructor_reports():
    if session.get('role') != 'instructor':
        return redirect('/')
    
    conn = get_db_connection()
    
    # Get courses for report generation
    courses = conn.execute('''
        SELECT * FROM courses WHERE instructor_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('instructor/reports.html',
                         courses=courses,
                         name=session.get('name'))

# API Routes
@app.route('/api/recognize-face', methods=['POST'])
def api_recognize_face():
    if session.get('role') != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    image_data = data.get('image')
    course_id = data.get('course_id')
    
    recognized_faces = face_system.detect_faces(image_data)
    
    results = []
    for face in recognized_faces:
        # Mark attendance for recognized face
        mark_attendance(face['user_id'], course_id, face['confidence'], 'auto')
        results.append({
            'user_id': face['user_id'],
            'name': face['name'],
            'student_id': face['student_id'],
            'confidence': face['confidence'],
            'eyes_detected': face['eyes_detected'],
            'timestamp': face['timestamp']
        })
    
    return jsonify({'recognized_faces': results})

@app.route('/api/manual-attendance', methods=['POST'])
def api_manual_attendance():
    if session.get('role') != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    student_id = data.get('student_id')
    course_id = data.get('course_id')
    
    mark_attendance(student_id, course_id, 100, 'manual')
    
    # Get student info
    conn = get_db_connection()
    student = conn.execute('SELECT name, student_id FROM users WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    
    return jsonify({
        'success': True,
        'student_name': student['name'],
        'student_id': student['student_id'],
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })

@app.route('/api/attendance-stats/<int:course_id>/<date>')
def api_attendance_stats(course_id, date):
    if session.get('role') != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    
    # Get attendance for specific date
    attendance_data = conn.execute('''
        SELECT u.name, u.student_id, a.status, a.timestamp, a.recognized_confidence, a.method
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.course_id = ? AND a.date = ?
        ORDER BY u.name
    ''', (course_id, date)).fetchall()
    
    # Get total enrolled students
    total_students = conn.execute('''
        SELECT COUNT(*) FROM enrollments 
        WHERE course_id = ?
    ''', (course_id,)).fetchone()[0]
    
    conn.close()
    
    present_count = len([record for record in attendance_data if record['status'] == 'present'])
    attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
    
    return jsonify({
        'date': date,
        'attendance_rate': round(attendance_rate, 2),
        'present_count': present_count,
        'total_students': total_students,
        'absent_count': total_students - present_count,
        'records': [
            {
                'student_name': record['name'],
                'student_id': record['student_id'],
                'status': record['status'],
                'timestamp': record['timestamp'],
                'confidence': record['recognized_confidence'],
                'method': record['method']
            } for record in attendance_data
        ]
    })

@app.route('/api/export-attendance/<int:course_id>')
def api_export_attendance(course_id):
    if session.get('role') != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Verify course belongs to instructor
    conn = get_db_connection()
    course = conn.execute('SELECT * FROM courses WHERE id = ? AND instructor_id = ?', 
                         (course_id, session['user_id'])).fetchone()
    if not course:
        conn.close()
        return jsonify({'error': 'Course not found'}), 404
    
    # Get attendance data
    attendance_data = conn.execute('''
        SELECT a.date, u.name, u.student_id, a.status, a.timestamp, a.method, a.recognized_confidence
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.course_id = ?
        ORDER BY a.date DESC, u.name
    ''', (course_id,)).fetchall()
    conn.close()
    
    # Create CSV
    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Student Name', 'Student ID', 'Status', 'Time', 'Method', 'Confidence'])
    
    for record in attendance_data:
        writer.writerow([
            record['date'],
            record['name'],
            record['student_id'],
            record['status'],
            record['timestamp'],
            record['method'],
            f"{record['recognized_confidence']}%" if record['recognized_confidence'] else 'N/A'
        ])
    
    output.seek(0)
    
    filename = f"attendance_{course['code']}_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/course-stats/<int:course_id>')
def api_course_stats(course_id):
    if session.get('role') != 'instructor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    stats = get_course_stats(course_id)
    return jsonify(stats)

# Student Routes
@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect('/')
    
    conn = get_db_connection()
    
    # Get student's courses and today's attendance
    today = datetime.now().strftime('%Y-%m-%d')
    courses = conn.execute('''
        SELECT c.id, c.code, c.name, c.schedule, c.room,
               (SELECT status FROM attendance 
                WHERE student_id = ? AND course_id = c.id AND date = ?) as status
        FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        WHERE e.student_id = ?
        ORDER BY c.name
    ''', (session['user_id'], today, session['user_id'])).fetchall()
    
    conn.close()
    
    return render_template('student/dashboard.html',
                         courses=courses,
                         name=session.get('name'),
                         today=today)

@app.route('/student/attendance/<int:course_id>')
def student_course_attendance(course_id):
    if session.get('role') != 'student':
        return redirect('/')
    
    conn = get_db_connection()
    
    # Verify student is enrolled
    enrollment = conn.execute('''
        SELECT e.*, c.name as course_name, c.code as course_code
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        WHERE e.student_id = ? AND e.course_id = ?
    ''', (session['user_id'], course_id)).fetchone()
    
    if not enrollment:
        conn.close()
        return redirect('/student/dashboard')
    
    # Get attendance history
    attendance_history = conn.execute('''
        SELECT date, status, timestamp, recognized_confidence, method
        FROM attendance 
        WHERE student_id = ? AND course_id = ?
        ORDER BY date DESC
        LIMIT 50
    ''', (session['user_id'], course_id)).fetchall()
    
    # Calculate statistics
    total_classes = len(attendance_history)
    present_classes = len([a for a in attendance_history if a['status'] == 'present'])
    course_attendance_rate = (present_classes / total_classes * 100) if total_classes > 0 else 0
    
    conn.close()
    
    return render_template('student/attendance-view.html',
                         course=enrollment,
                         attendance_history=attendance_history,
                         present_classes=present_classes,
                         total_classes=total_classes,
                         attendance_rate=round(course_attendance_rate, 1))

if __name__ == '__main__':
    # Create uploads directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    print("🚀 Face Attendance System Starting...")
    print("✅ Database initialized with fresh data!")
    print("👨‍🏫 Demo Instructor: professor / password")
    print("👨‍🎓 Demo Student: student1 / password") 
    print("🌐 Access: http://localhost:5000")
    print("-" * 50)
    
    app.run(debug=True, port=5000)
    