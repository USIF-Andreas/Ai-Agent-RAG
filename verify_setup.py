#!/usr/bin/env python3
"""
Quick test script to verify RAG Agent setup
Run this to check if everything is configured correctly
"""

import os
import sys
import subprocess

def check_python():
    """Check Python version"""
    print("🔍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print(f"✅ Python {sys.version.split()[0]} found")
    return True

def check_ollama():
    """Check if Ollama is running"""
    print("\n🔍 Checking Ollama connection...")
    try:
        response = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True,
            timeout=2
        )
        if response.returncode == 0:
            print("✅ Ollama is running on localhost:11434")
            return True
        else:
            print("❌ Ollama is not responding")
            print("   → Run: ollama serve")
            return False
    except Exception as e:
        print("❌ Ollama is not running")
        print("   → Make sure to run: ollama serve")
        return False

def check_documents():
    """Check if documents exist"""
    print("\n🔍 Checking documents directory...")
    doc_dir = "documents"
    if os.path.exists(doc_dir):
        files = [f for f in os.listdir(doc_dir) if f.endswith('.txt')]
        if files:
            print(f"✅ Found {len(files)} document(s)")
            for f in files:
                print(f"   - {f}")
            return True
        else:
            print("⚠️  No documents found in documents/")
            print("   → Add .txt files to documents/ folder")
            return False
    else:
        print("⚠️  documents/ directory not found")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking Python dependencies...")
    required = ['flask', 'flask_sqlalchemy', 'flask_login', 'langchain', 'chromadb', 'ollama']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("   → Run: pip install -r requirements.txt")
        return False
    else:
        print("✅ All required packages installed")
        return True

def check_database():
    """Check if database is initialized"""
    print("\n🔍 Checking database...")
    if os.path.exists("users.db"):
        print("✅ Database file exists")
        return True
    else:
        print("⚠️  Database not initialized yet")
        print("   → Will be created on first run")
        return False

def main():
    print("=" * 50)
    print("🚀 RAG Agent Setup Verification")
    print("=" * 50)
    
    checks = [
        check_python(),
        check_dependencies(),
        check_ollama(),
        check_documents(),
        check_database()
    ]
    
    print("\n" + "=" * 50)
    if all(checks[:-1]):  # All except database are required
        print("✅ Setup looks good! You can start the app.")
        print("\nTo run the app:")
        print("  python app.py")
        print("\nThen open: http://localhost:5000")
        return 0
    else:
        print("⚠️  Some issues found. Please fix them before running.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
