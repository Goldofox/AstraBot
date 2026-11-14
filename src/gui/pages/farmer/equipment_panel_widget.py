from DBDofusUnity.datas.protos.non_obf.game.common_pb2 import ObjectItemInventory
from DBDofusUnity.dofus_unity_reader.data_center.data_reader import DataReader
from DBDofusUnity.dofus_unity_reader.data_center.i18n import I18N
from DBDofusUnity.dofus_unity_reader.game_constants.inventory_position import (
    CharacterInventoryPositionEnum,
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap, QShowEvent
from PyQt6.QtWidgets import QGridLayout, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel, CaptionLabel

from src.gui.components.group_box import GroupBox
from src.gui.services.item_icons import ICON_SIZE, item_icon_cache

_EMPTY_VALUE = "—"

_SLOT_LAYOUT: list[tuple[CharacterInventoryPositionEnum, str, int, int]] = [
    (CharacterInventoryPositionEnum.AccessoryPositionHat, "Chapeau", 0, 1),
    (CharacterInventoryPositionEnum.AccessoryPositionAmulet, "Amulette", 1, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionCape, "Cape", 1, 2),
    (CharacterInventoryPositionEnum.InventoryPositionRingLeft, "Anneau G.", 2, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionWeapon, "Arme", 2, 1),
    (CharacterInventoryPositionEnum.InventoryPositionRingRight, "Anneau D.", 2, 2),
    (CharacterInventoryPositionEnum.AccessoryPositionBelt, "Ceinture", 3, 0),
    (CharacterInventoryPositionEnum.AccessoryPositionShield, "Bouclier", 3, 1),
    (CharacterInventoryPositionEnum.AccessoryPositionPets, "Familier", 3, 2),
    (CharacterInventoryPositionEnum.AccessoryPositionBoots, "Bottes", 4, 0),
    (CharacterInventoryPositionEnum.InventoryPositionMount, "Monture", 4, 2),
    (CharacterInventoryPositionEnum.InventoryPositionDofus1, "Dofus 1", 5, 0),
    (CharacterInventoryPositionEnum.InventoryPositionDofus2, "Dofus 2", 5, 1),
    (CharacterInventoryPositionEnum.InventoryPositionDofus3, "Dofus 3", 5, 2),
    (CharacterInventoryPositionEnum.InventoryPositionDofus4, "Dofus 4", 6, 0),
    (CharacterInventoryPositionEnum.InventoryPositionDofus5, "Dofus 5", 6, 1),
    (CharacterInventoryPositionEnum.InventoryPositionDofus6, "Dofus 6", 6, 2),
]


def get_item_name(object_item: ObjectItemInventory) -> str:
    item_data = DataReader().item_by_id.get(object_item.item.gid)
    if item_data and item_data.nameId:
        return I18N().name_by_id.get(item_data.nameId, f"Item {object_item.item.gid}")
    return f"Item {object_item.item.gid}"


class _SlotWidget(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent=parent)
        self.icon_id: int | None = None
        self._value: str | None = None
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        self.setLayout(layout)

        title = CaptionLabel(text=label, parent=self)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.value_label = BodyLabel(text=_EMPTY_VALUE, parent=self)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setWordWrap(True)
        self.value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.value_label.setMinimumHeight(ICON_SIZE)
        layout.addWidget(self.value_label)

    def set_value(self, value: str | None, icon_id: int | None) -> None:
        if (value, icon_id) == (self._value, self.icon_id):
            return
        self._value = value
        self.icon_id = icon_id
        self.value_label.setText(value if value else _EMPTY_VALUE)
        self.value_label.setToolTip(value or "")

    def set_image(self, image: QImage) -> None:
        self.value_label.setPixmap(QPixmap.fromImage(image))


class EquipmentPanelWidget(GroupBox):
    def __init__(self, parent: QWidget | None = None):
        super().__init__("", parent=parent)
        self._icons = item_icon_cache()
        self._icons.ready.connect(self._on_icon_ready)

        grid = QGridLayout()
        grid.setSpacing(6)
        self.slot_by_position: dict[int, _SlotWidget] = {}
        for position, label, row, col in _SLOT_LAYOUT:
            slot = _SlotWidget(label)
            grid.addWidget(slot, row, col)
            self.slot_by_position[int(position)] = slot

        self.content_layout.addLayout(grid)

    def set_items(self, items_by_position: dict[int, ObjectItemInventory]) -> None:
        for position, slot in self.slot_by_position.items():
            object_item = items_by_position.get(position)
            item_data = DataReader().item_by_id.get(object_item.item.gid) if object_item else None
            slot.set_value(
                get_item_name(object_item) if object_item else None,
                item_data.iconId if item_data is not None else None,
            )
        self._load_icons()

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
