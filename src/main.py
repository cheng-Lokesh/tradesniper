#!/usr/bin/env python3
"""
TradeSniper Entry Point
"""
import os
import sys

def main():
    # Set project root to sys.path
    project_root = os.path.dirname(os.path.abspath(__file__))
    # Ideally project_root is the directory containing 'src', which is one level up
    # Wait, src/main.py is INSIDE src. So project root is ONE level up.
    # But usually entry point is OUTSIDE src, e.g. run.py in root.
    # If I keep main.py in src, running it requires running 'python src/main.py'.
    # I should add the parent directory of 'src' to sys.path.
    
    sys.path.insert(0, os.path.dirname(project_root))

    try:
        from src.ui.app import main as app_main
        app_main()
    except ImportError as e:
        print(f"Error starting application: {e}")
        print("Please ensure you are running from the project root or have installed dependencies.")
        sys.exit(1)

if __name__ == "__main__":
    main()
