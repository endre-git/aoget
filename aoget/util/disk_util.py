import os


def get_local_file_size(file_path: str) -> int:
    """Get the size of a local file.
    :param file_path: The path to the file
    :return: The size of the file in bytes"""
    if not os.path.exists(file_path):
        return -1
    return os.path.getsize(file_path)


def get_all_file_names_from_folders(folders: list) -> list:
    """Get all file names from a list of folders.
    :param folders: The list of folders
    :return: The list of file names"""
    file_names = []
    for folder in folders:
        for root, dirs, files in os.walk(folder):
            for file in files:
                file_names.append(file)
    return file_names
