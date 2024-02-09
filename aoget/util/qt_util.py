import sys
import os.path
import traceback

import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6 import QtGui
from util.aogetutil import get_last_log_lines
from config.app_config import get_app_version
import logging

logger = logging.getLogger(__name__)


def error_dialog(parent, message: str, header="Error") -> None:
    """Show an error dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog"""
    msg = QtWidgets.QErrorMessage(parent)
    msg.setWindowTitle(header)
    msg.showMessage(message)


def message_dialog(parent, message: str, header="Message") -> None:
    """Show a message dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog"""
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(header)
    msg.setText(message)
    msg.exec()


def confirmation_dialog(parent, message: str, header="Please confirm") -> bool:
    """Show a confirmation dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog
    :return:
        True if the user confirmed, False otherwise"""
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(header)
    msg.setText(message)
    msg.setStandardButtons(
        QtWidgets.QMessageBox.StandardButton.Yes
        | QtWidgets.QMessageBox.StandardButton.No
    )
    msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
    return msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes


def show_warnings(parent, brief: str, messages: list, header="Warning") -> bool:
    """Show a confirmation dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog
    :return:
        True if the user confirmed, False otherwise"""
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle(header)
    brief = f"<p>{brief}</p>"
    html_message = "<br/>".join(messages)
    msg.setText(f"{brief}<p>{html_message}</p>")
    msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
    msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.Ok)
    return msg.exec()


def qt_debounce(component, wait_ms, function, *args, **kwargs):
    """Debounce a function call to the given component. The function will be called after the
    given wait time in milliseconds. The function will be called with the given arguments and
    keyword arguments.
        :param component:
            The component to debounce the function call to
        :param wait_ms:
            The wait time in milliseconds
        :param function:
            The function to call
        :param args:
            The arguments to pass to the function
        :param kwargs:
            The keyword arguments to pass to the function
        :return:
            The function to call to start the debounce timer
    """

    # if the component has no debounced attribute, create it
    if not hasattr(component, "debounced"):
        component.debounced = []
    debounce = QTimer()
    debounce.setInterval(wait_ms)
    debounce.setSingleShot(True)
    debounce.timeout.connect(lambda: function(*args, **kwargs))
    component.debounced.append(debounce)

    return debounce.start


def install_catch_all_exception_handler(main_window, log_path, error_path):
    """Install a catch all exception handler that will show an error dialog with the exception
    message and stack trace"""

    def handle_exception(exc_type, exc_value, exc_traceback):
        ## KeyboardInterrupt is a special case.
        ## We don't raise the error dialog when it occurs.
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
