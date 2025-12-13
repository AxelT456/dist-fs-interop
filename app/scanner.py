import logging
import os
import time
from typing import Dict, Tuple

from .config import ConfigManager


log = logging.getLogger(__name__)


def split_name_and_ext(filename: str) -> Tuple[str, str]:
    base, ext = os.path.splitext(filename)
    return base, ext.lstrip(".")

class FolderScanner:
    def __init__(self, folder_path: str, config: ConfigManager) -> None:
        self._folder = folder_path
        self._config = config

    def _scan_folder(self) -> Dict[str, Tuple[str, str]]:
        entries: Dict[str, Tuple[str, str]] = {}
        try:
            for name in os.listdir(self._folder):
                path = os.path.join(self._folder, name)
                if os.path.isfile(path):
                    base, ext = split_name_and_ext(name)
                    entries[name] = (base, ext)
        except FileNotFoundError:
            log.error(f"Carpeta no encontrada: {self._folder}")
        return entries

    # --- CAMBIO: Eliminamos el método interactivo _prompt_for_file ---

    def initial_sync_with_prompts(self) -> None:
        """Sincroniza y publica todo automáticamente al iniciar."""
        current = self._scan_folder()
        known = self._config.list_files()

        for filename in sorted(current.keys()):
            if filename not in known:
                # Publicar automáticamente con TTL de 1 hora
                self._config.upsert_file(filename, publish=True, ttl=3600)
                log.info(f"Nuevo archivo auto-publicado: {filename}")

        for filename in list(known.keys()):
            if filename not in current:
                self._config.remove_file(filename)
                log.info(f"Archivo eliminado de la carpeta: {filename}")

    def run_periodic_scan(self, interval_seconds: int = 300) -> None:
        """Escanea periódicamente y publica nuevos archivos automáticamente."""
        log.info(f"Hilo de escaneo automático iniciado cada {interval_seconds}s")
        while True:
            try:
                current = self._scan_folder()
                known = self._config.list_files()

                for filename in sorted(current.keys()):
                    if filename not in known:
                        self._config.upsert_file(filename, publish=True, ttl=3600)
                        log.info(f"[SCAN] Nuevo archivo auto-publicado: {filename}")

                for filename in list(known.keys()):
                    if filename not in current:
                        self._config.remove_file(filename)
                        log.info(f"[SCAN] Archivo eliminado: {filename}")

                self._config.save()
            except Exception as e:
                log.error(f"Error en escaneo: {e}")
            time.sleep(max(5, interval_seconds))