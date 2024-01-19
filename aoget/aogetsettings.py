import os

URL_HISTORY_REL_PATH = "app_settings/url_history.lst"
TARGET_FOLDER_HISTORY_REL_PATH = "app_settings/target_folder_history.lst"


def get_config_value(key):
    pass


def get_url_history():
    """Load and return a list of URLs that have been previously used in jobs, and stored in app_settings/url_history.lst."""
    url_history = []
    if not os.path.exists(URL_HISTORY_REL_PATH):
        return url_history
    with open(URL_HISTORY_REL_PATH, "r") as f:
        for line in f:
            url_history.append(line.strip())
    return url_history


def get_target_folder_history():
    """Load and return a list of target folders that have been previously used in jobs, and stored in app_settings/target_folder_history.lst."""
    target_folder_history = []
    if not os.path.exists(TARGET_FOLDER_HISTORY_REL_PATH):
        return target_folder_history
    with open(TARGET_FOLDER_HISTORY_REL_PATH, "r") as f:
        for line in f:
            target_folder_history.append(line.strip())
    return target_folder_history


def update_url_history(new_url):
    """Update the URL history file with the URLs that have been used in the current job."""
    url_history = get_url_history()
    if new_url in url_history:
        return
    url_history.append(new_url)
    if len(url_history) > 10:
        url_history = url_history[-10:]
    with open(URL_HISTORY_REL_PATH, "w") as f:
        for url in url_history:
            f.write(url + "\n")


def update_target_folder_history(new_target_folder):
    """Update the target folder history file with the target folders that have been used in the current job."""
    target_folder_history = get_target_folder_history()
    if new_target_folder in target_folder_history:
        return
    target_folder_history.append(new_target_folder)
    if len(target_folder_history) > 10:
        target_folder_history = target_folder_history[-10:]
    with open(TARGET_FOLDER_HISTORY_REL_PATH, "w") as f:
        for target_folder in target_folder_history:
            f.write(target_folder + "\n")
