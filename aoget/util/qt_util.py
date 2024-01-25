import sys
import os.path
import traceback

import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtCore import QTimer
from PyQt6 import QtGui


def error_dialog(parent, message: str, header="Error") -> None:
    """Show an error dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog"""
    msg = QtWidgets.QErrorMessage(parent)
    msg.setWindowTitle(header)
    msg.showMessage(message)


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
    msg.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
    msg.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
    return msg.exec() == QtWidgets.QMessageBox.StandardButton.Yes


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

    component.debounce = QTimer()
    component.debounce.setInterval(wait_ms)
    component.debounce.setSingleShot(True)
    component.debounce.timeout.connect(lambda: function(*args, **kwargs))

    return component.debounce.start


def install_catch_all_exception_handler(main_window):
    """Install a catch all exception handler that will show an error dialog with the exception
    message and stack trace"""

    def handle_exception(exc_type, exc_value, exc_traceback):
        ## KeyboardInterrupt is a special case.
        ## We don't raise the error dialog when it occurs.
        if issubclass(exc_type, KeyboardInterrupt):
            if QtGui.qApp:
                QtGui.qApp.quit()
                return

        filename, line, dummy, dummy = traceback.extract_tb(exc_traceback).pop()
        filename = os.path.basename(filename)
        error = "%s: %s" % (exc_type.__name__, exc_value)

        error_dialog(
            main_window,
            "<html>A critical error has occured.<br/> "
            + "<b>%s</b><br/><br/>" % error
            + "It occurred at <b>line %d</b> of file <b>%s</b>.<br/>" % (line, filename)
            + "</html>",
        )
        print("Closed due to an error. This is the full error report:")
        print()
        print("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        sys.exit(1)

    # install handler for exceptions
    sys.excepthook = handle_exception
