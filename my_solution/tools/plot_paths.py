"""Output and cache paths shared by the policy timeline tools."""
import os
import pathlib


PROJECT_FOLDER = pathlib.Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_FOLDER / '.cache'


def get_path(folder_name):
    """
    Get the absolute path of a folder in the project folder, and create it if needed.

    Parameters:
    - folder_name (str): Name of the folder.

    Returns:
    - pathlib.Path: Absolute path of the folder.
    """
    folder_path = PROJECT_FOLDER / folder_name
    os.makedirs(folder_path, exist_ok=True)
    return folder_path
