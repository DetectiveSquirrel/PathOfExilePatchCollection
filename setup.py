import os
import subprocess
import sys

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
    setup_directories()
    print("Setup complete.")

if __name__ == "__main__":
    main()
