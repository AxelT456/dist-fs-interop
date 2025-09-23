# app/config.py

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass
from typing import Dict, Optional

log = logging.getLogger(__name__)


@dataclass
class FileConfig:
    publish: bool
    ttl: int


class ConfigManager:
    def __init__(self, config_path: str) -> None:
        self._config_path = config_path
        self._lock = threading.RLock()
        self._folder: Optional[str] = None
        self._files: Dict[str, FileConfig] = {}

    def load(self) -> None:
        with self._lock:
            if not os.path.isfile(self._config_path):
                log.info(f"Config no existe, se creará al guardar: {self._config_path}")
                return
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._folder = raw.get("folder")
                files = raw.get("files", {})
                self._files = {}
                for name, meta in files.items():
                    try:
                        self._files[name] = FileConfig(
                            publish=bool(meta.get("publish", False)),
                            ttl=int(meta.get("ttl", 300)),
                        )
                    except Exception as e:
                        log.warning(f"Entrada inválida en config para {name}: {e}")
                log.info("Config cargada")
            except Exception as e:
                log.error(f"Error leyendo config: {e}")

    def save(self) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self._config_path) or ".", exist_ok=True)
            payload = {
                "folder": self._folder,
                "files": {name: asdict(cfg) for name, cfg in self._files.items()},
            }
            tmp_path = self._config_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._config_path)
            log.info("Config guardada")

    def get_folder(self) -> Optional[str]:
        with self._lock:
            return self._folder

    def set_folder(self, folder: str) -> None:
        with self._lock:
            self._folder = folder

    def get_file(self, filename: str) -> Optional[FileConfig]:
        with self._lock:
            return self._files.get(filename)

    def upsert_file(self, filename: str, publish: bool, ttl: int) -> None:
        with self._lock:
            self._files[filename] = FileConfig(publish=publish, ttl=ttl)

    def remove_file(self, filename: str) -> None:
        with self._lock:
            if filename in self._files:
                del self._files[filename]

    def list_files(self) -> Dict[str, FileConfig]:
        with self._lock:
            return dict(self._files)

    def list_published_files(self) -> Dict[str, FileConfig]:
        """
        Devuelve un diccionario solo con los archivos que tienen 'publish' a True.
        """
        with self._lock:
            return {
                name: cfg
                for name, cfg in self._files.items()
                if cfg.publish
            }