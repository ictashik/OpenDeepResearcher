#!/usr/bin/env python3
"""
Test script to verify OpenDeepResearcher installation and basic functionality.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Test basic dependencies
        import streamlit as st
        print("✅ Streamlit imported successfully")
    except ImportError as e:
        print(f"❌ Streamlit import failed: {e}")
        return False
    
    try:
        import pandas as pd
        print("✅ Pandas imported successfully")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import fitz  # PyMuPDF
        print("✅ PyMuPDF imported successfully")
    except ImportError as e:
        print(f"❌ PyMuPDF import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    return True

def test_file_structure():
    """Test if all required files exist."""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "src/app.py",
        "src/components/__init__.py",
        "src/components/logger.py",
        "src/components/sidebar.py",
        "src/pages/__init__.py",
        "src/pages/dashboard.py",
        "src/pages/settings.py",
        "src/pages/scoping.py",
        "src/pages/screening.py",
        "src/pages/analysis.py",
        "src/pages/report.py",
        "src/utils/__init__.py",
        "src/utils/data_manager.py",
        "src/utils/ollama_client.py",
        "src/utils/pdf_processor.py",
        "requirements.txt",
        "README.md"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_data_manager():
    """Test data manager functionality."""
    print("\n💾 Testing data manager...")
    
    try:
        # Add src to path for imports
        sys.path.insert(0, str(Path("src").absolute()))
        
        from utils.data_manager import ensure_data_structure, load_config
        
        # Test data structure creation
        ensure_data_structure()
        print("✅ Data structure creation works")
        
        # Test config loading
        config = load_config()
        print("✅ Config loading works")
        
        return True
    except Exception as e:
        print(f"❌ Data manager test failed: {e}")
        return False

def test_ollama_client():
    """Test Ollama client (without requiring Ollama to be running)."""
    print("\n🤖 Testing Ollama client...")
    
    try:
        sys.path.insert(0, str(Path("src").absolute()))
        
        from utils.ollama_client import OllamaClient
        
        # Just test initialization
        client = OllamaClient()
        print("✅ Ollama client initialization works")
        
        return True
    except Exception as e:
        print(f"❌ Ollama client test failed: {e}")
        return False

def test_pdf_processor():
    """Test PDF processor."""
    print("\n📄 Testing PDF processor...")
    
    try:
        sys.path.insert(0, str(Path("src").absolute()))
        
        from utils.pdf_processor import PDFProcessor
        
        # Just test initialization
        processor = PDFProcessor()
        print("✅ PDF processor initialization works")
        
        return True
    except Exception as e:
        print(f"❌ PDF processor test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🔬 OpenDeepResearcher Installation Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("File Structure Test", test_file_structure),
        ("Data Manager Test", test_data_manager),
        ("Ollama Client Test", test_ollama_client),
        ("PDF Processor Test", test_pdf_processor)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! OpenDeepResearcher is ready to use.")
        print("\n🚀 To start the application, run:")
        print("   python run.py")
        print("   or")
        print("   streamlit run src/app.py")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        print("\n📦 To install missing dependencies:")
        print("   pip install -r requirements.txt")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
