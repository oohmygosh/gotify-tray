from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QIcon

from ..designs.widget_main import Ui_MainWindow
from .StatusWidget import StatusWidget
from ..models import (
    ApplicationModel,
    MessagesModel,
    MessagesModelItem,
)
from . import MessageWidget

from gotify_tray.__version__ import __title__
from gotify_tray.database import Settings
from gotify_tray.gui.themes import get_theme_file
from gotify_tray.gui.models import MessageItemDataRole
from gotify_tray import gotify


settings = Settings("gotify-tray")


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    refresh = QtCore.pyqtSignal()
    delete_all = QtCore.pyqtSignal(QtGui.QStandardItem)
    delete_message = QtCore.pyqtSignal(MessagesModelItem)
    application_selection_changed = QtCore.pyqtSignal(QtGui.QStandardItem)
    image_popup = QtCore.pyqtSignal(str, QtCore.QPoint)
    hidden = QtCore.pyqtSignal()
    activated = QtCore.pyqtSignal()

    def __init__(self, application_model: ApplicationModel, application_proxy_model: QtCore.QSortFilterProxyModel, messages_model: MessagesModel):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.installEventFilter(self)

        self.setWindowTitle(__title__)

        self.application_model = application_model
        self.application_proxy_model = application_proxy_model
        self.messages_model = messages_model

        self.listView_applications.setModel(application_proxy_model)
        self.listView_messages.setModel(messages_model)

        # Do not expand the applications listview when resizing
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        # Do not collapse the message list
        self.splitter.setCollapsible(1, False)
        self.status_widget = StatusWidget()
        self.horizontalLayout.insertWidget(0, self.status_widget)

        self.set_icons()

        font_title = QtGui.QFont()
        if s := settings.value("MainWindow/font/application", type=str):
            font_title.fromString(s)
        else:
            font_title.setBold(True)
            font_title.setPointSize(font_title.pointSize() + 2)
        self.label_application.setFont(font_title)

        # Set tooltips
        self.pb_refresh.setToolTip("Refresh")
        self.pb_delete_all.setToolTip("Delete all messages")

        self.restore_state()

        self.link_callbacks()

    def set_icons(self):
        # Set button icons
        self.pb_refresh.setIcon(QtGui.QIcon(get_theme_file("refresh.svg")))
        self.pb_delete_all.setIcon(QtGui.QIcon(get_theme_file("trashcan.svg")))

        # Resize the labels and icons
        size = settings.value("MainWindow/label/size", type=int)
        self.status_widget.setFixedSize(QtCore.QSize(size, size))

        size = settings.value("MainWindow/button/size", type=int)
        self.pb_refresh.setFixedSize(QtCore.QSize(size, size))
        self.pb_delete_all.setFixedSize(QtCore.QSize(size, size))
        self.pb_refresh.setIconSize(QtCore.QSize(int(0.7 * size), int(0.7 * size)))
        self.pb_delete_all.setIconSize(QtCore.QSize(int(0.9 * size), int(0.9 * size)))

        size = settings.value("MainWindow/application/icon/size", type=int)
        self.listView_applications.setIconSize(QtCore.QSize(size, size))

        # Refresh the status widget
        self.status_widget.refresh()

    def set_active(self):
        self.status_widget.set_active()

    def set_connecting(self):
        self.status_widget.set_connecting()

    def set_inactive(self):
        self.status_widget.set_inactive()

    def set_error(self):
        self.status_widget.set_error()

    def display_message_widgets(self, parent: QtCore.QModelIndex, first: int, last: int):
        for i in range(first, last+1):
            if index := self.messages_model.index(i, 0, parent):
                message_item = self.messages_model.itemFromIndex(index)

                message: gotify.GotifyMessageModel = self.messages_model.data(index, MessageItemDataRole.MessageRole)

                application_item = self.application_model.itemFromId(message.appid)
                message_widget = MessageWidget(self.listView_messages, message_item, icon=application_item.icon())
                message_widget.deletion_requested.connect(self.delete_message.emit)
                message_widget.image_popup.connect(self.image_popup.emit)
                
                self.listView_messages.setIndexWidget(index, message_widget)

    def currentApplicationIndex(self) -> QtCore.QModelIndex:
        return self.listView_applications.selectionModel().currentIndex()

    def application_selection_changed_callback(
        self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex
    ):
        if item := self.application_model.itemFromIndex(self.application_proxy_model.mapToSource(current)):
            self.label_application.setText(item.text())
            self.application_selection_changed.emit(item)

    def delete_all_callback(self):
        if (
            self.messages_model.rowCount() == 0
            or QtWidgets.QMessageBox.warning(
                self,
                "Are you sure?",
                "Delete all messages?",
                QtWidgets.QMessageBox.StandardButton.Ok
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                defaultButton=QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            != QtWidgets.QMessageBox.StandardButton.Ok
        ):
            return

        index = self.currentApplicationIndex()
        if item := self.application_model.itemFromIndex(self.application_proxy_model.mapToSource(index)):
            self.delete_all.emit(item)

    def disable_applications(self):
        self.listView_applications.clearSelection()
        self.listView_applications.setDisabled(True)

    def enable_applications(self):
        self.listView_applications.setEnabled(True)
        self.listView_applications.setCurrentIndex(self.application_proxy_model.index(0, 0))

    def disable_buttons(self):
        self.pb_delete_all.setDisabled(True)
        self.pb_refresh.setDisabled(True)

    def enable_buttons(self):
        self.pb_delete_all.setEnabled(True)
        self.pb_refresh.setEnabled(True)

    def bring_to_front(self):
        self.ensurePolished()
        self.setWindowState(
            self.windowState() & ~QtCore.Qt.WindowState.WindowMinimized
            | QtCore.Qt.WindowState.WindowActive
        )
        self.show()
        self.activateWindow()
        # pops on current desktop if window was visible on another desktop
        self.raise_()

    def link_callbacks(self):
        self.pb_refresh.clicked.connect(self.refresh.emit)
        self.pb_delete_all.clicked.connect(self.delete_all_callback)

        self.listView_applications.selectionModel().currentChanged.connect(self.application_selection_changed_callback)

    def store_state(self):
        settings.setValue("MainWindow/geometry", self.saveGeometry())
        settings.setValue("MainWindow/state", self.saveState())
        settings.setValue("MainWindow/splitter", self.splitter.saveState())

    def restore_state(self):
        if geometry := settings.value("MainWindow/geometry", type=QtCore.QByteArray):
            self.restoreGeometry(geometry)
        if state := settings.value("MainWindow/state", type=QtCore.QByteArray):
            self.restoreState(state)
        if splitter := settings.value("MainWindow/splitter", type=QtCore.QByteArray):
            self.splitter.restoreState(splitter)

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        self.hide()
        e.ignore()
        self.hidden.emit()

    def eventFilter(self, object: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            self.activated.emit()

        return super().eventFilter(object, event)
