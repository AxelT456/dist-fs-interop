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

    def _prompt_for_file(self, filename: str) -> Tuple[bool, int]:
        while True:
            ans = input(f"¿Publicar '{filename}'? [s/n]: ").strip().lower()
            if ans in ("s", "n"):
                publish = ans == "s"
                break
            print("Responde 's' o 'n'.")
        ttl = 300
        if publish:
            while True:
                t = input("TTL en segundos (ej. 300): ").strip()
                if t.isdigit() and int(t) > 0:
                    ttl = int(t)
                    break
                print("Ingresa un entero positivo.")
        return publish, ttl

    def initial_sync_with_prompts(self) -> None:
        current = self._scan_folder()
        known = self._config.list_files()

        # Add new files or confirm existing
        for filename in sorted(current.keys()):
            if filename not in known:
                publish, ttl = self._prompt_for_file(filename)
                self._config.upsert_file(filename, publish, ttl)
                log.info(f"Nuevo archivo: {filename} | publish={publish} ttl={ttl}")

        # Remove missing files
        for filename in list(known.keys()):
            if filename not in current:
                self._config.remove_file(filename)
                log.info(f"Archivo eliminado de la carpeta: {filename}")

    def run_periodic_scan(self, interval_seconds: int = 300) -> None:
        log.info(f"Hilo de escaneo iniciado cada {interval_seconds}s")
        while True:
            try:
                current = self._scan_folder()
                known = self._config.list_files()

                # Add new files and prompt
                for filename in sorted(current.keys()):
                    if filename not in known:
                        publish, ttl = self._prompt_for_file(filename)
                        self._config.upsert_file(filename, publish, ttl)
                        log.info(f"[SCAN] Nuevo archivo: {filename} | publish={publish} ttl={ttl}")

                # Remove missing files
                for filename in list(known.keys()):
                    if filename not in current:
                        self._config.remove_file(filename)
                        log.info(f"[SCAN] Archivo eliminado: {filename}")

                # Persist config after each scan
                self._config.save()
            except Exception as e:
                log.error(f"Error en escaneo: {e}")
            time.sleep(max(5, interval_seconds))

