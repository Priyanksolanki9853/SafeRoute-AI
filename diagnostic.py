"""
Diagnostic Script for AI Road Safety Backend
Run this to check for common issues
"""

import sys
print(f"Python Version: {sys.version}")
print("-" * 50)

# Test imports
print("\n📦 Testing Dependencies:")
print("-" * 50)

dependencies = [
    "flask",
    "flask_cors",
    "requests",
    "osmnx",
    "networkx",
    "numpy",
    "cv2",
    "geopandas",
    "shapely",
    "pandas",
    "sklearn",
    "geopy",
    "rtree"
]

failed = []
for dep in dependencies:
    try:
        if dep == "cv2":
            import cv2
        elif dep == "sklearn":
            import sklearn
        else:
            __import__(dep)
        print(f"✅ {dep}")
    except ImportError as e:
        print(f"❌ {dep} - {e}")
        failed.append(dep)

print("\n" + "=" * 50)

if failed:
    print(f"\n⚠️ MISSING DEPENDENCIES: {', '.join(failed)}")
    print("\nTo fix, run:")
    print("pip install -r requirements.txt")
else:
    print("\n✅ All dependencies installed!")

# Check environment variables
print("\n🔧 Environment Variables:")
print("-" * 50)
import os

env_vars = ["GEMINI_API_KEY", "PORT"]
for var in env_vars:
    value = os.environ.get(var)
    if value:
        if var == "GEMINI_API_KEY":
            print(f"✅ {var}: {value[:10]}... (hidden)")
        else:
            print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: Not set")

# Check file structure
print("\n📁 File Structure:")
print("-" * 50)

required_files = [
    "app.py",
    "requirements.txt",
    "templates/Index.html",
    "static/script.js",
    "static/style.css"
]

for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file} - Missing!")

print("\n" + "=" * 50)
print("\n💡 Tips:")
print("1. If dependencies are missing, run: pip install -r requirements.txt")
print("2. If GEMINI_API_KEY is not set, the chatbot will use fallback mode")
print("3. Make sure templates/Index.html exists")
print("4. To run the server: python app.py")
print("\n" + "=" * 50)