class JobEditorMode:
    """Enum for job editor mode."""

    JOB_NEW = 0
    JOB_EDITED = 1
    JOB_IMPORTED = 2


ERROR_TEXT_STYLE = """
        QLineEdit {
            border: 2px solid #ffaa99;
            background-color: #ffaa99;
        }"""

DEFAULT_TEXT_STYLE = """
        QLineEdit {
        }"""

PROGRESS_BAR_PASSIVE_STYLE = """
    QProgressBar {
        border: 1px solid grey;
        border-radius: 0px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #d0d6db;
        width: 1px;
    }"""

PROGRESS_BAR_ACTIVE_STYLE = """
    QProgressBar {
        border: 1px solid grey;
        border-radius: 0px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #31a7f5;
        width: 1px;
    }"""
