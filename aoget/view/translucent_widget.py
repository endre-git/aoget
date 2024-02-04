from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QMovie


class TranslucentWidget(QtWidgets.QWidget):
    """Loader popup, based on this:
    https://stackoverflow.com/questions/44264852/pyside-pyqt-overlay-widget"""

    def __init__(self, parent=None, overlayText="Loading..."):
        super(TranslucentWidget, self).__init__(parent)

        # make the window frameless
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        # self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.fillColor = QtGui.QColor(30, 30, 30, 120)
        self.penColor = QtGui.QColor("#333333")

        self.popup_fillColor = QtGui.QColor(240, 240, 240, 255)
        self.popup_penColor = QtGui.QColor(200, 200, 200, 255)

        self.movie = QMovie("resources/gifs/loading.gif")
        self.loader_label = QLabel(self)
        self.loader_label.setFixedSize(150, 150)
        self.loader_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.loader_label.setMovie(self.movie)
        self.movie.start()

        self.overlayText = overlayText

    def resizeEvent(self, event):
        s = self.size()
        popup_width = 300
        popup_height = 120
        ow = int(s.width() / 2 - popup_width / 2)
        oh = int(s.height() / 2 - popup_height / 2)
        self.loader_label.move(ow + 265, oh + 5)

    def paintEvent(self, event):
        # This method is, in practice, drawing the contents of
        # your window.

        # get current window size
        s = self.size()
        qp = QtGui.QPainter()
        qp.begin(self)
        # qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setPen(self.penColor)
        qp.setBrush(self.fillColor)
        qp.drawRect(0, 0, s.width(), s.height())

        # drawpopup
        qp.setPen(self.popup_penColor)
        qp.setBrush(self.popup_fillColor)
        popup_width = 300
        popup_height = 120
        ow = int(s.width() / 2 - popup_width / 2)
        oh = int(s.height() / 2 - popup_height / 2)
        qp.drawRoundedRect(ow, oh, popup_width, popup_height, 5, 5)

        font = QtGui.QFont()
        font.setPixelSize(18)
        font.setBold(True)
        qp.setFont(font)
        qp.setPen(QtGui.QColor(70, 70, 70))
        tolw, tolh = 80, -5
        qp.drawText(
            ow + int(popup_width / 2) - tolw,
            oh + int(popup_height / 2) - tolh,
            self.overlayText,
        )

        qp.end()

    def _onclose(self):
        print("Close")
