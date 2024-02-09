import os
from config.app_config import get_config_value, AppConfig


def get_url_history():
    """Load and return a list of URLs that have been previously used in jobs."""
    url_history = []
    url_history_rel_path = get_config_value(AppConfig.URL_HISTORY_FILE)
    if not os.path.exists(url_history_rel_path):
        return url_history
    with open(url_history_rel_path, "r") as f:
        for line in f:
            url_history.append(line.strip())
    url_history.reverse()
    return url_history


def get_target_folder_history():
    """Load and return a list of target folders that have been previously used in jobs."""
    target_folder_history = []
    target_folder_history_rel_path = get_config_value(
        AppConfig.TARGET_FOLDER_HISTORY_FILE
    )
    if not os.path.exists(target_folder_history_rel_path):
        return target_folder_history
    with open(target_folder_history_rel_path, "r") as f:
        for line in f:
            target_folder_history.append(line.strip())
    target_folder_history.reverse()
    return target_folder_history


def update_url_history(new_url):
    """Update the URL history file with the URLs that have been used in the current job."""
    url_history = get_url_history()
    url_history_rel_path = get_config_value(AppConfig.URL_HISTORY_FILE)
    if new_url in url_history:
        return
    url_history.append(new_url)
    if len(url_history) > 10:
        url_history = url_history[-10:]
    with open(url_history_rel_path, "w") as f:
        for url in url_history:
            f.write(url + "\n")


def update_target_folder_history(new_target_folder):
    """Update the target folder history file with the target folders that have been used in the
    current job."""
    target_folder_history = get_target_folder_history()
    if new_target_folder in target_folder_history:
        return
    target_folder_history_rel_path = get_config_value(
        AppConfig.TARGET_FOLDER_HISTORY_FILE
    )
    target_folder_history.append(new_target_folder)
    if len(target_folder_history) > 10:
        target_folder_history = target_folder_history[-10:]
    with open(target_folder_history_rel_path, "w") as f:
        for target_folder in target_folder_history:
            f.write(target_folder + "\n")
