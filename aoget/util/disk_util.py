import os
import re


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


def to_filesystem_friendly_string(original_string):
    # Replace forbidden characters with an underscore
    forbidden_chars = r'[<>:"/\\|?*\']'
    safe_string = re.sub(forbidden_chars, '_', original_string)

    # Replace or remove additional undesirable characters as needed
    safe_string = safe_string.replace(' ', '_')  # Replace spaces with underscores
    safe_string = re.sub(r'[^\w\s-]', '', safe_string)  # Remove non-word characters

    # Optionally, normalize to a standard case
    safe_string = safe_string.lower()  # Convert to lowercase

    return safe_string


def open_exclusive(file_path: str, mode: str) -> object:
    """Open a file for exclusive access. If the file already exists, an OSError will be raised.
    Not to be used for exclusive access locking on existing files.
    :param file_path: The path to the file
    :param mode: The mode to open the file in
    :return: The file object"""
    try:
        # Open the file in a mode that requests exclusive access
        fd = os.open(file_path, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        return os.fdopen(fd, mode)
    except OSError as e:
        new_message = f"Error opening file for exclusive access {file_path}: {str(e)}"
        raise type(e)(new_message).with_traceback(e.__traceback__)
