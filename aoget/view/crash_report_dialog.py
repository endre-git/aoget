from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6 import uic


ISSUE_REPORT_URL = "https://github.com/kosaendre/aoget/issues/new"


class CrashReportDialog(QDialog):

    def __init__(self, crash_report: str):
        super(CrashReportDialog, self).__init__()
        self.crash_report = crash_report
        uic.loadUi("aoget/qt/crash_report_dialog.ui", self)
        self.txtDetails.setText(crash_report)
        self.btnCopyToClipboard.clicked.connect(self.copy_to_clipboard)
        self.btnGotoGithub.clicked.connect(self.goto_github)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txtDetails.toPlainText())

    def goto_github(self):
        QDesktopServices.openUrl(QUrl(ISSUE_REPORT_URL))
