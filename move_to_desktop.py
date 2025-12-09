import shutil
import os

def main():
    # Define source paths
    backend_zip = r"c:\Users\WinUser\.gemini\antigravity\scratch\backend\vysalytica_backend_export.zip"
    frontend_zip = r"c:\Users\WinUser\.gemini\antigravity\scratch\frontend\vysalytica_frontend_export.zip"
    
    # Define Desktop path
    # Using os.path.expanduser to be safe, though we know the user is WinUser
    desktop_path = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    
    # Create a specific folder on Desktop to keep it tidy
    export_folder = os.path.join(desktop_path, "Vysalytica_Export")
    if not os.path.exists(export_folder):
        os.makedirs(export_folder)
        print(f"Created folder: {export_folder}")

    # Target paths
    target_backend = os.path.join(export_folder, "vysalytica_backend.zip")
    target_frontend = os.path.join(export_folder, "vysalytica_frontend.zip")

    # Copy files
    print(f"Copying files to {export_folder}...")
    
    if os.path.exists(backend_zip):
        shutil.copy2(backend_zip, target_backend)
        print(f"[OK] Copied Backend Zip")
    else:
        print(f"X Backend zip not found at {backend_zip}")

    if os.path.exists(frontend_zip):
        shutil.copy2(frontend_zip, target_frontend)
        print(f"[OK] Copied Frontend Zip")
    else:
        print(f"X Frontend zip not found at {frontend_zip}")

if __name__ == "__main__":
    main()
