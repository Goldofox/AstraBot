import logging
from collections import OrderedDict
from functools import cache
from pathlib import Path

from ankama_launcher_emulator.utils.environment import resolve_dofus_path
from PyQt6.QtCore import QCoreApplication, QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage

from DBDofusUnity.dofus_unity_reader.data_center.item_icon_reader import ItemIconReader

logger = logging.getLogger()
ICON_SIZE = 64


class ItemIconLoader:
    def __init__(self) -> None:
        self._reader: ItemIconReader | None = None
        self._unavailable = False

    def load(self, icon_id: int) -> QImage:
        if self._unavailable:
            return QImage()
        if self._reader is None:
            try:
                self._reader = ItemIconReader(Path(resolve_dofus_path()).parent)
            except Exception:
                self._unavailable = True
                logger.warning("Item icon bundle is unavailable", exc_info=True)
                return QImage()
        try:
            image = self._reader.read(icon_id)
            if image is None:
                return QImage()
            image.thumbnail((ICON_SIZE, ICON_SIZE))
            pixels = image.tobytes()
            return QImage(pixels, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
        except Exception:
            logger.warning("Cannot decode item icon %s", icon_id, exc_info=True)
            return QImage()


class _IconSignals(QObject):
    loaded = pyqtSignal(int, QImage)


class _LoadIcon(QRunnable):
    def __init__(self, loader: ItemIconLoader, signals: _IconSignals, icon_id: int) -> None:
        super().__init__()
        self.loader = loader
        self.signals = signals
        self.icon_id = icon_id

    def run(self) -> None:
        self.signals.loaded.emit(self.icon_id, self.loader.load(self.icon_id))


class ItemIconCache(QObject):
    ready = pyqtSignal(int, QImage)

    def __init__(self, parent: QObject | None = None, *, max_bytes: int = 16 * 1024 * 1024) -> None:
        super().__init__(parent)
        self._max_bytes = max_bytes
        self._bytes = 0
        self._images: OrderedDict[int, QImage] = OrderedDict()
        self._pending: set[int] = set()
        self._missing: set[int] = set()
        self._loader = ItemIconLoader()
        self._signals = _IconSignals(self)
        self._signals.loaded.connect(self._loaded)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)

    @pyqtSlot()
    def shutdown(self) -> None:
        self._pool.clear()
        self._pool.waitForDone()

    def request(self, icon_id: int) -> QImage | None:
        image = self._images.get(icon_id)
        if image is not None:
            self._images.move_to_end(icon_id)
            return image
        if icon_id not in self._pending and icon_id not in self._missing:
            self._pending.add(icon_id)
            self._pool.start(_LoadIcon(self._loader, self._signals, icon_id))
        return None

    @pyqtSlot(int, QImage)
    def _loaded(self, icon_id: int, image: QImage) -> None:
        self._pending.discard(icon_id)
        if image.isNull():
            self._missing.add(icon_id)
            return
        self._images[icon_id] = image
        self._bytes += image.sizeInBytes()
        while self._bytes > self._max_bytes and self._images:
            _, evicted = self._images.popitem(last=False)
            self._bytes -= evicted.sizeInBytes()
        self.ready.emit(icon_id, image)


@cache
def item_icon_cache() -> ItemIconCache:
    app = QCoreApplication.instance()
    icons = ItemIconCache(app)
    if app is not None:
        app.aboutToQuit.connect(icons.shutdown)
    return icons
