import atexit
import subprocess
import sys
from threading import Lock

import msgspec

from src.services.icon_worker import IconRequest, IconResponse
from src.utils.project_paths import BUNDLE_ROOT, IS_PACKAGED


class IconProcess:
    def __init__(self) -> None:
        self._lock = Lock()
        self._process: subprocess.Popen[bytes] | None = None

    def load(self, request: IconRequest) -> IconResponse:
        with self._lock:
            if self._process is None:
                args = ["--icon-worker"] if IS_PACKAGED else ["-m", "src.services.icon_worker"]
                self._process = subprocess.Popen(
                    [sys.executable, *args],
                    cwd=BUNDLE_ROOT,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            process = self._process
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(msgspec.json.encode(request) + b"\n")
            process.stdin.flush()
            response = process.stdout.readline()
            if not response:
                raise RuntimeError("The icon decoding process stopped unexpectedly")
            return msgspec.json.decode(response, type=IconResponse)

    def close(self) -> None:
        with self._lock:
            process = self._process
            if process is None:
                return
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.stdout is not None:
                process.stdout.close()
            self._process = None


icon_process = IconProcess()
atexit.register(icon_process.close)
