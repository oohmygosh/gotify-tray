from gotify_tray.gotify.models import GotifyVersionModel
from gotify_tray.tasks import VerifyServerInfoTask
from PyQt6 import QtWidgets

from ..designs.widget_server import Ui_Dialog


class ServerInfoDialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, url: str = "", token: str = ""):
        super(ServerInfoDialog, self).__init__()
        self.setupUi(self)
        self.setWindowTitle("Server info")
        self.line_url.setPlaceholderText("https://gotify.example.com")
        self.line_url.setText(url)
        self.line_token.setText(token)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setDisabled(
            True
        )
        self.link_callbacks()

    def test_server_info(self):
        self.pb_test.setStyleSheet("")
        self.line_url.setStyleSheet("")
        self.line_token.setStyleSheet("")
        self.label_server_info.clear()

        url = self.line_url.text()
        client_token = self.line_token.text()
        if not url or not client_token:
            return

        self.pb_test.setDisabled(True)
        self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setDisabled(
            True
        )

        self.task = VerifyServerInfoTask(url, client_token)
        self.task.success.connect(self.server_info_success)
        self.task.incorrect_token.connect(self.incorrect_token_callback)
        self.task.incorrect_url.connect(self.incorrect_url_callback)
        self.task.start()

    def server_info_success(self, version: GotifyVersionModel):
        self.pb_test.setEnabled(True)
        self.label_server_info.setText(f"Version: {version.version}")
        self.pb_test.setStyleSheet("background-color: rgba(0, 255, 0, 100);")
        self.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(
            True
        )

    def incorrect_token_callback(self, version: GotifyVersionModel):
        self.pb_test.setEnabled(True)
        self.label_server_info.setText(f"Version: {version.version}")
        self.pb_test.setStyleSheet("background-color: rgba(255, 0, 0, 100);")
        self.line_token.setStyleSheet("border: 1px solid red;")

    def incorrect_url_callback(self):
        self.pb_test.setEnabled(True)
        self.label_server_info.clear()
        self.pb_test.setStyleSheet("background-color: rgba(255, 0, 0, 100);")
        self.line_url.setStyleSheet("border: 1px solid red;")

    def link_callbacks(self):
        self.pb_test.clicked.connect(self.test_server_info)
        self.line_url.textChanged.connect(
            lambda: self.buttonBox.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).setDisabled(True)
        )
        self.line_token.textChanged.connect(
            lambda: self.buttonBox.button(
                QtWidgets.QDialogButtonBox.StandardButton.Ok
            ).setDisabled(True)
        )