import os


def setup_directories():
    base_directory = "data"
    storage_directory = os.path.join(base_directory, "stored")
    download_directory = os.path.join(base_directory, "download")

    os.makedirs(base_directory, exist_ok=True)
    os.makedirs(storage_directory, exist_ok=True)
    os.makedirs(download_directory, exist_ok=True)


def main():
    setup_directories()


if __name__ == "__main__":
    main()
