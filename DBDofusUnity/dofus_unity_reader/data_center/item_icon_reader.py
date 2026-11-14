from pathlib import Path
from typing import Any, Literal

from PIL.Image import Image
lazy from UnityPy.files.ObjectReader import ObjectReader

from DBDofusUnity.dofus_unity_reader.bundle_export import load_bundle


class IconBundleReader:
    def __init__(self, game_dir: Path, kind: Literal["item", "class"]) -> None:
        relative_path = "Items/item_assets_1x.bundle" if kind == "item" else "UI/class_assets_.bundle"
        self._prefix = "" if kind == "item" else "symbol_"
        source = game_dir / "Dofus_Data/StreamingAssets/Content/Picto" / relative_path
        self._environment = load_bundle(source, game_dir=game_dir)
        self._sprites: dict[str, ObjectReader[Any]] = {}
        for obj in self._environment.objects:
            if obj.type.name == "Sprite" and (name := obj.peek_name()):
                self._sprites[name] = obj
        if not self._sprites:
            raise ValueError(f"No sprites found in {source}")

    def read(self, icon_id: int) -> Image | None:
        sprite = self._sprites.get(f"{self._prefix}{icon_id}")
        if sprite is None:
            return None
        try:
            return sprite.parse_as_object().image.convert("RGBA")
        finally:
            sprite.assets_file._cache.clear()
