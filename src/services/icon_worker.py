import sys
from pathlib import Path
from typing import Literal

import msgspec


class IconRequest(msgspec.Struct):
    game_dir: str
    kind: Literal["item", "class"]
    icon_id: int
    size: int


class IconResponse(msgspec.Struct):
    width: int = 0
    height: int = 0
    pixels: bytes = b""
    error: str | None = None


def main() -> None:
    from DBDofusUnity.dofus_unity_reader.data_center.item_icon_reader import IconBundleReader

    readers: dict[tuple[str, str], IconBundleReader | IconResponse] = {}
    for line in sys.stdin.buffer:
        try:
            request = msgspec.json.decode(line, type=IconRequest)
            key = (request.game_dir, request.kind)
            reader = readers.get(key)
            if reader is None:
                try:
                    reader = IconBundleReader(Path(request.game_dir), request.kind)
                except Exception as error:
                    reader = IconResponse(error=f"{type(error).__name__}: {error}")
                readers[key] = reader
            if isinstance(reader, IconResponse):
                response = reader
            else:
                image = reader.read(request.icon_id)
                response = IconResponse()
                if image is not None:
                    image.thumbnail((request.size, request.size))
                    response = IconResponse(image.width, image.height, image.tobytes())
        except Exception as error:
            response = IconResponse(error=f"{type(error).__name__}: {error}")
        sys.stdout.buffer.write(msgspec.json.encode(response) + b"\n")
        sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
