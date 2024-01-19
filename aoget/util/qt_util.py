import PyQt6.QtWidgets as QtWidgets
from PyQt6.QtCore import QTimer


def error_dialog(parent, message: str) -> None:
    """Show an error dialog with the given message
    :param parent:
        The parent window
    :param message:
        The message to show in the dialog"""
    msg = QtWidgets.QErrorMessage(parent)
    msg.setWindowTitle("Error")
    msg.showMessage(message)


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
