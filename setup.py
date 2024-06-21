import os
import subprocess
import sys

def install_requirements():
    requirements_file = 'requirements.txt'
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--root-user-action", "-r", requirements_file])
    # Conditionally install pywin32 if on Windows
    if sys.platform.startswith('win'):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--root-user-action", "pywin32"])

def setup_directories():
    base_directory = 'data'
    storage_directory = os.path.join(base_directory, 'stored')
    download_directory = os.path.join(base_directory, 'download')

    os.makedirs(base_directory, exist_ok=True)
    os.makedirs(storage_directory, exist_ok=True)
    os.makedirs(download_directory, exist_ok=True)

    base_directory_dev = 'data_dev'
    storage_directory_dev = os.path.join(base_directory_dev, 'stored')
    download_directory_dev = os.path.join(base_directory_dev, 'download')
    
    os.makedirs(base_directory_dev, exist_ok=True)
    os.makedirs(storage_directory_dev, exist_ok=True)
    os.makedirs(download_directory_dev, exist_ok=True)

def main():
    #install_requirements()
    setup_directories()
    print("Setup complete.")

if __name__ == "__main__":
    main()
