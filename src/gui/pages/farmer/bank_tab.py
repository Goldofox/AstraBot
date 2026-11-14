from __future__ import annotations

lazy from src.core.bot.bot import Bot

from DBDofusUnity.datas.protos.non_obf.game.common_pb2 import (
    ObjectItemInventory,
)
from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel

from src.gui.components.item_grid import ItemGrid


class BankTab(QWidget):
    def __init__(self, bot: Bot, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.bot = bot
        self.items_by_uid: dict[int, ObjectItemInventory] = {}
        self.signals_connected = False
        self._render_dirty = False
        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setInterval(50)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.timeout.connect(self._rebuild_sorted_list)

        self.list_widget = ItemGrid(self)
        self.loading_label = CaptionLabel(text="Loading bank…", parent=self)
        self.loading_label.hide()

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.loading_label)
        layout.addWidget(self.list_widget)

    @pyqtSlot(list)
    def on_bank_refreshed(self, objects: list[ObjectItemInventory]):
        self.items_by_uid.clear()
        for object_item in objects:
            self.items_by_uid[object_item.item.uid] = object_item
        self._schedule_rebuild()

    @pyqtSlot(ObjectItemInventory)
    def on_bank_item_updated(self, object_item: ObjectItemInventory):
        self.items_by_uid[object_item.item.uid] = object_item
        self._schedule_rebuild()

    @pyqtSlot(int)
    def on_bank_item_removed(self, uid: int):
        if uid not in self.items_by_uid:
            return
        del self.items_by_uid[uid]
        self._schedule_rebuild()

    def _schedule_rebuild(self) -> None:
        self._render_dirty = True
        if self.isVisible() and not self._rebuild_timer.isActive():
            self.loading_label.show()
            self._rebuild_timer.start()

    def _rebuild_sorted_list(self) -> None:
        self.list_widget.setUpdatesEnabled(False)
        self.list_widget.clear()
        sorted_items = sorted(self.items_by_uid.values(), key=lambda obj: obj.item.quantity, reverse=True)
        for object_item in sorted_items:
            self.list_widget.add_object_item(object_item)
        self.list_widget.setUpdatesEnabled(True)
        self._render_dirty = False
        self.loading_label.hide()

    def connect_signals(self) -> None:
        if self.signals_connected:
            return
        self.bot.inventory_signals.bank_refreshed.connect(self.on_bank_refreshed)
        self.bot.inventory_signals.bank_item_updated.connect(self.on_bank_item_updated)
        self.bot.inventory_signals.bank_item_removed.connect(self.on_bank_item_removed)
        self.signals_connected = True
        self._resync_bank()

    def disconnect_signals(self) -> None:
        if not self.signals_connected:
            return
        self.bot.inventory_signals.bank_refreshed.disconnect(self.on_bank_refreshed)
        self.bot.inventory_signals.bank_item_updated.disconnect(self.on_bank_item_updated)
        self.bot.inventory_signals.bank_item_removed.disconnect(self.on_bank_item_removed)
        self.signals_connected = False
        self.items_by_uid.clear()
        self._rebuild_timer.stop()
        self.list_widget.clear()
        self.loading_label.hide()

    def _resync_bank(self) -> None:
        self.items_by_uid.clear()
        self.list_widget.clear()
        bank_items = list(self.bot.game_state.inventory.bank_objects_by_uid.values())
        if bank_items:
            self.on_bank_refreshed(bank_items)

    def showEvent(self, a0: QShowEvent | None) -> None:
        if self._render_dirty:
            self._rebuild_sorted_list()
        super().showEvent(a0)
