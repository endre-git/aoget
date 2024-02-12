import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtCore import QTimer

import logging

logger = logging.getLogger(__name__)


def error_dialog(parent, message: str, header="Error") -> None:
    """Show an error dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog"""
    msg = QtWidgets.QMessageBox(parent)
    if parent is None:
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
    msg.setText(message)
    msg.setWindowTitle(header)
    msg.exec()


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
