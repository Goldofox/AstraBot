from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap, QShowEvent
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import CaptionLabel

from DBDofusUnity.datas.protos.non_obf.game.common_pb2 import ObjectItemInventory
from DBDofusUnity.dofus_unity_reader.game_constants.inventory_position import (
    CharacterInventoryPositionEnum,
)
from src.gui.components.group_box import GroupBox
from src.gui.services.item_icons import class_icon_cache, item_icon_cache
from src.gui.utils.item_display import get_item_display
from src.services.display_catalog import load_display_catalog

_SLOT_SIZE = 75

_SLOT_LAYOUT: list[tuple[CharacterInventoryPositionEnum, str, int, int]] = [
    (CharacterInventoryPositionEnum.AccessoryPositionHat, "Chapeau", 0, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionCape, "Cape", 1, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionWeapon, "Arme", 3, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionShield, "Bouclier", 4, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionPets, "Familier", 5, 0),
    (CharacterInventoryPositionEnum.InventoryPositionMount, "Monture", 6, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionAmulet, "Amulette", 0, 5),
    (CharacterInventoryPositionEnum.InventoryPositionRingLeft, "Anneau G.", 1, 5),
    (CharacterInventoryPositionEnum.InventoryPositionRingRight, "Anneau D.", 2, 5),
    (CharacterInventoryPositionEnum.AccessoryPositionBelt, "Ceinture", 3, 5),
    (CharacterInventoryPositionEnum.AccessoryPositionBoots, "Bottes", 4, 5),
    (CharacterInventoryPositionEnum.InventoryPositionDofus1, "Dofus 1", 7, 0),
    (CharacterInventoryPositionEnum.InventoryPositionDofus2, "Dofus 2", 7, 1),
    (CharacterInventoryPositionEnum.InventoryPositionDofus3, "Dofus 3", 7, 2),
    (CharacterInventoryPositionEnum.InventoryPositionDofus4, "Dofus 4", 7, 3),
    (CharacterInventoryPositionEnum.InventoryPositionDofus5, "Dofus 5", 7, 4),
    (CharacterInventoryPositionEnum.InventoryPositionDofus6, "Dofus 6", 7, 5),
]


class _SlotWidget(QFrame):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.icon_id: int | None = None
        self._value: str | None = None
        self._image_key: int | None = None
        self._label = label
        self.setFixedSize(_SLOT_SIZE, _SLOT_SIZE)
        self.setObjectName("equipmentSlot")
        self.setStyleSheet("""
            QFrame#equipmentSlot {
                background: #282937;
                border: 1px solid #444657;
                border-radius: 3px;
            }
            QFrame#equipmentSlot:hover { border-color: #8199bf; }
            QLabel { background: transparent; border: none; color: #a5a8b4; font-size: 12px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.value_label = QLabel(label, self)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setWordWrap(True)
        layout.addWidget(self.value_label)
        self.setToolTip(label)

    def set_value(self, value: str | None, icon_id: int | None) -> None:
        if (value, icon_id) == (self._value, self.icon_id):
            return
        self._value = value
        self._image_key = None
        self.icon_id = icon_id
        self.value_label.setText(value or self._label)
        self.setToolTip(f"{self._label}\n{value}" if value else self._label)

    def set_image(self, image: QImage) -> None:
        if self._image_key == image.cacheKey():
            return
        self._image_key = image.cacheKey()
        self.value_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                _SLOT_SIZE - 15,
                _SLOT_SIZE - 15,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class EquipmentPanelWidget(GroupBox):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("", parent=parent)
        self._icons = item_icon_cache()
        self._icons.ready.connect(self._on_icon_ready)
        self._class_icons = class_icon_cache()
        self._class_icons.ready.connect(self._on_class_icon_ready)
        self._breed_id = 0
        self._class_image_key: int | None = None
        self.setFixedWidth(6 * _SLOT_SIZE + 5 * 6 + 22)
        self.setObjectName("equipmentPanel")
        self.setStyleSheet("""
            QWidget#equipmentPanel {
                background: transparent;
                border: none;
            }
        """)

        grid = QGridLayout()
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setSpacing(6)
        center = QWidget(self)
        center_layout = QVBoxLayout(center)
        center_layout.addStretch()
        self.class_icon = QLabel("Classe", center)
        self.class_icon.setFixedSize(120, 120)
        self.class_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_icon.setStyleSheet("color: #c7d8d2; background: transparent;")
        center_layout.addWidget(self.class_icon, 0, Qt.AlignmentFlag.AlignCenter)
        self.class_name = CaptionLabel("", center)
        self.class_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_name.setStyleSheet("color: #c7d8d2; background: transparent;")
        center_layout.addWidget(self.class_name)
        center_layout.addStretch()
        grid.addWidget(center, 0, 1, 7, 4)
        grid.setRowStretch(2, 1)
        self.slot_by_position: dict[int, _SlotWidget] = {}
        for position, label, row, col in _SLOT_LAYOUT:
            slot = _SlotWidget(label)
            grid.addWidget(slot, row, col)
            self.slot_by_position[int(position)] = slot

        self.content_layout.addLayout(grid)

    @pyqtSlot(int)
    def set_breed(self, breed_id: int) -> None:
        if self._breed_id != breed_id:
            self._breed_id = breed_id
            self._class_image_key = None
            self.class_icon.setText("Classe")
            self.class_name.setText(load_display_catalog().breed_names.get(breed_id, ""))
        self._load_class_icon()

    def _load_class_icon(self) -> None:
        if self.isVisible() and self._breed_id > 0:
            image = self._class_icons.request(self._breed_id)
            if image is not None:
                self._on_class_icon_ready(self._breed_id, image)

    @pyqtSlot(int, QImage)
    def _on_class_icon_ready(self, breed_id: int, image: QImage) -> None:
        if breed_id == self._breed_id and self._class_image_key != image.cacheKey():
            self._class_image_key = image.cacheKey()
            self.class_icon.setPixmap(
                QPixmap.fromImage(image).scaled(
                    self.class_icon.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def set_items(self, items_by_position: dict[int, ObjectItemInventory]) -> None:
        for position, slot in self.slot_by_position.items():
            object_item = items_by_position.get(position)
            if object_item is None:
                slot.set_value(None, None)
            else:
                slot.set_value(*get_item_display(object_item.item.gid))
        self._load_icons()
        self._load_class_icon()

    def _load_icons(self) -> None:
        if not self.isVisible():
            return
        for slot in self.slot_by_position.values():
            if slot.icon_id is not None:
                image = self._icons.request(slot.icon_id)
                if image is not None:
                    slot.set_image(image)

    @pyqtSlot(int, QImage)
    def _on_icon_ready(self, icon_id: int, image: QImage) -> None:
        for slot in self.slot_by_position.values():
            if slot.icon_id == icon_id:
                slot.set_image(image)

    def showEvent(self, a0: QShowEvent | None) -> None:
        super().showEvent(a0)
        self._load_icons()
        self._load_class_icon()
