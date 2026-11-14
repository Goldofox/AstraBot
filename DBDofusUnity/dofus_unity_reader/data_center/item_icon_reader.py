from functools import cache
from pathlib import Path
from typing import Any

from PIL.Image import Image
lazy from UnityPy.files.ObjectReader import ObjectReader

from DBDofusUnity.dofus_unity_reader.bundle_export import load_bundle


class ItemIconReader:
    def __init__(self, game_dir: Path) -> None:
        source = game_dir / "Dofus_Data/StreamingAssets/Content/Picto/Items/item_assets_1x.bundle"
        self._environment = load_bundle(source, game_dir=game_dir)
        self._sprites: dict[int, ObjectReader[Any]] = {}
        for obj in self._environment.objects:
            if obj.type.name == "Sprite":
                name = obj.peek_name()
                if name and name.isascii() and name.isdecimal():
                    self._sprites[int(name)] = obj
        if not self._sprites:
            raise ValueError(f"No item sprites found in {source}")

    @cache
    def read(self, icon_id: int) -> Image | None:
        sprite = self._sprites.get(icon_id)
        if sprite is None:
            return None
        try:
            return sprite.parse_as_object().image.convert("RGBA")
        finally:
            sprite.assets_file._cache.clear()
