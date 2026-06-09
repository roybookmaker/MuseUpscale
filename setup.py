import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print(" MUSE UPSCALE SETUP - Prerequisite Installer Tool")
    print(" Diagnoses and silently installs system dependencies on Windows")
    print("=" * 60)

    try:
        from src.checker_app import PrerequisiteCheckerApp
        app = PrerequisiteCheckerApp()
        app.mainloop()
    except ImportError as e:
        print(f"\n[ERROR] Failed to import application packages: {e}")
        print("Please ensure you have installed the requirements using:")
        print("    pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Prerequisite Installer failed to launch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
