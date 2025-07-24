#!/usr/bin/env python3
"""
OpenDeepResearcher - AI-Powered Systematic Review & Research Application
Run script to start the Streamlit application.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Start the OpenDeepResearcher application."""
    
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    app_path = script_dir / "src" / "app.py"
    
    if not app_path.exists():
        print(f"Error: Could not find app.py at {app_path}")
        sys.exit(1)
    
    print("🔬 Starting OpenDeepResearcher...")
    print("📄 AI-Powered Systematic Review & Research Application")
    print("-" * 60)
    
    try:
        # Run the Streamlit application
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            str(app_path),
            "--server.headless=false",
            "--browser.gatherUsageStats=false"
        ], check=True, cwd=script_dir)
        
    except subprocess.CalledProcessError as e:
        print(f"Error running application: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
