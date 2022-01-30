import abc
import logging
import time

from PyQt6 import QtCore
from PyQt6.QtCore import pyqtSignal

from gotify_tray.gotify.api import GotifyClient
from gotify_tray.gotify.models import GotifyVersionModel

from . import gotify


logger = logging.getLogger("gotify-tray")


class BaseTask(QtCore.QThread):
    failed = pyqtSignal()

    def __init__(self):
        super(BaseTask, self).__init__()
        self.running = False

    @abc.abstractmethod
    def task(self):
        ...

    def run(self):
        self.running = True
        try:
            self.task()
        except Exception as e:
            logger.error(f"{self.__class__.__name__} failed: {e}")
            self.failed.emit()
        finally:
            self.running = False


class DeleteAllMessagesTask(BaseTask):
    deleted = pyqtSignal(bool)

    def __init__(self, gotify_client: gotify.GotifyClient):
        super(DeleteAllMessagesTask, self).__init__()
        self.gotify_client = gotify_client

    def task(self):
        success = self.gotify_client.delete_messages()
        self.deleted.emit(success)


class GetApplicationsTask(BaseTask):
    success = pyqtSignal(list)
    error = pyqtSignal(gotify.GotifyErrorModel)

    def __init__(self, gotify_client: gotify.GotifyClient):
        super(GetApplicationsTask, self).__init__()
        self.gotify_client = gotify_client

    def task(self):
        result = self.gotify_client.get_applications()
        if isinstance(result, gotify.GotifyErrorModel):
            self.error.emit(result)
        else:
            self.success.emit(result)


class VerifyServerInfoTask(BaseTask):
    success = pyqtSignal(GotifyVersionModel)
    incorrect_token = pyqtSignal(GotifyVersionModel)
    incorrect_url = pyqtSignal()

    def __init__(self, url: str, client_token: str):
        super(VerifyServerInfoTask, self).__init__()
        self.url = url
        self.client_token = client_token

    def task(self):
        try:
            gotify_client = gotify.GotifyClient(self.url, self.client_token)

            version = gotify_client.version()
            if isinstance(version, gotify.GotifyErrorModel):
                self.incorrect_url.emit()
                return

            result = gotify_client.get_messages(limit=1)

            if isinstance(result, gotify.GotifyPagedMessagesModel):
                self.success.emit(version)
                return
            elif (
                isinstance(result, gotify.GotifyErrorModel)
                and result["error"] == "Unauthorized"
            ):
                self.incorrect_token.emit(version)
                return
            self.incorrect_url.emit()
        except Exception as e:
            self.incorrect_url.emit()


class ServerConnectionWatchdogTask(BaseTask):
    closed = pyqtSignal()

    def __init__(self, gotify_client: GotifyClient):
        super(ServerConnectionWatchdogTask, self).__init__()
        self.gotify_client = gotify_client
        self.interval = 60

    def task(self):
        while True:
            time.sleep(self.interval)
            if not self.gotify_client.is_listening():
                self.closed.emit()
                logger.debug(
                    f"ServerConnectionWatchdogTask: gotify_client is not listening"
                )
