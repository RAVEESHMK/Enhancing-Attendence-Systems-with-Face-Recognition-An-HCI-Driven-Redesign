#!/usr/bin/env python3
import os
import sys
import webbrowser
from threading import Timer

def main():
    print("🚀 Starting Face Attendance System...")
    print("=" * 50)
    
    # Check if required packages are installed
    try:
        from flask import Flask
        import cv2
        import numpy as np
        from PIL import Image
        print("✅ All dependencies are installed")
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Start the application
    try:
        from main import app
        
        def open_browser():
            webbrowser.open_new('http://localhost:5000')
        
        # Open browser after 2 seconds
        Timer(2, open_browser).start()
        
        print("🌐 Starting web server...")
        print("📱 Application will open automatically in your browser")
        print("🔗 Manual access: http://localhost:5000")
        print("=" * 50)
        print("Demo Accounts:")
        print("👨‍🏫 Instructor: professor / password")
        print("👨‍🎓 Student: student1 / password")
        print("=" * 50)
        print("Press Ctrl+C to stop the server")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()