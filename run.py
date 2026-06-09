import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 60)
    print(" MUSE UPSCALE - Vulkan-Powered AI Video Upscaling App")
    print(" Developed for AMD & NVIDIA GPUs (Vulkan Powered) on Windows")

    print("=" * 60)

    try:
        from src.app import MuseUpscaleApp
        app = MuseUpscaleApp()
        app.mainloop()
    except ImportError as e:
        print(f"\n[ERROR] Failed to import application packages: {e}")
        print("Please ensure you have installed the requirements using:")
        print("    pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Application failed to launch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
