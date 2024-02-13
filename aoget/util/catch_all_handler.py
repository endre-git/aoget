
import sys
import os.path
import traceback
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6 import QtGui
from util.aogetutil import get_last_log_lines
from config.app_config import get_app_version


logger = logging.getLogger(__name__)


def install_catch_all_exception_handler(main_window, log_path, error_path):
    """Install a catch all exception handler that will show an error dialog with the exception
    message and stack trace"""

    def handle_exception(exc_type, exc_value, exc_traceback):
        # KeyboardInterrupt is a special case.
        # We don't raise the error dialog when it occurs.
        if issubclass(exc_type, KeyboardInterrupt):
            if QtGui.qApp:
                QtGui.qApp.quit()

        try:
            logger.error("App crash due to unhandled error:")
            logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            filename, line, dummy, dummy = traceback.extract_tb(exc_traceback).pop()
            filename = os.path.basename(filename)
            error = "%s: %s" % (exc_type.__name__, exc_value)

            last_50_lines = "".join(get_last_log_lines(log_path, 20))
            monospaced_last_50_lines = f"<pre>{last_50_lines}</pre>"

            msg = f"""<html><h4>AOGet Crash Report</h4><p>A critical error killed the application.
                It might be a bug or an unexpected system condition. Error message was:
                <b>{error}</b><br/><br/>
                It occurred at <b>line {line}</b> of file <b>{filename}</b>.<br/>
                App version is <b>{get_app_version()}</b>.<br/>
                <p>The last 50 lines of app log were:</br>
                {monospaced_last_50_lines}</p>
                </html>"""

            with open(error_path, "w") as f:
                f.write(msg)

            main_window.closing = True
            QApplication.quit()
            os._exit(1)
        except Exception as e:
            print("An error occurred while handling an error. This is the error:")
            print(e)
            print("This is the original error:")
            print("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
            os._exit(1)

    # install handler for exceptions
    sys.excepthook = handle_exception
