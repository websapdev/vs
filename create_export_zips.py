import os
import zipfile

def zip_directory(folder_path, output_path, ignore_dirs):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for file in files:
                # Skip .DS_Store and other common junk
                if file == '.DS_Store':
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                
                # Double check we aren't zipping the zip itself if it's in the same dir
                if os.path.abspath(file_path) == os.path.abspath(output_path):
                    continue
                    
                print(f"Adding {arcname}")
                zipf.write(file_path, arcname)

def main():
    # Configuration
    backend_path = r"c:\Users\WinUser\.gemini\antigravity\scratch\backend"
    frontend_path = r"c:\Users\WinUser\.gemini\antigravity\scratch\frontend"
    
    ignore_list = {
        '.git', '.next', 'node_modules', '__pycache__', 
        '.pytest_cache', 'venv', '.venv', 'env', '.env', 
        'dist', 'build', 'coverage'
    }

    # Zip Backend
    print("Zipping Backend...")
    zip_directory(backend_path, os.path.join(backend_path, "vysalytica_backend_export.zip"), ignore_list)
    
    # Zip Frontend
    print("\nZipping Frontend...")
    zip_directory(frontend_path, os.path.join(frontend_path, "vysalytica_frontend_export.zip"), ignore_list)

    print("\nDone! Export files created:")
    print(f"1. {os.path.join(backend_path, 'vysalytica_backend_export.zip')}")
    print(f"2. {os.path.join(frontend_path, 'vysalytica_frontend_export.zip')}")

if __name__ == "__main__":
    main()
