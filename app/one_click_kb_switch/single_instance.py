from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SingleInstanceGuard:
    lock_path: Path
    handle: object | None = None
    locked: bool = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.lock_path.open("w", encoding="utf-8")
        self.handle.write(str(os.getpid()))
        self.handle.flush()
        self.locked = False
        if sys.platform == "win32":
            import msvcrt

            try:
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                self.handle.close()
                self.handle = None
                raise RuntimeError("Another instance of 1-Click-KB-Switch is already running.") from exc
            self.locked = True
        else:
            import fcntl

            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                self.handle.close()
                self.handle = None
                raise RuntimeError("Another instance of 1-Click-KB-Switch is already running.") from exc
            self.locked = True

    def release(self) -> None:
        if not self.handle:
            return
        try:
            if self.locked:
                if sys.platform == "win32":
                    import msvcrt

                    self.handle.seek(0)
                    try:
                        msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                else:
                    import fcntl

                    try:
                        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
        finally:
            self.handle.close()
            self.handle = None
            self.locked = False
