# servidor_dan.py

import argparse
import logging
import os
import threading
import time

from app.config import ConfigManager
from app.scanner import FolderScanner
from app.udp_server import UdpServer


def setup_logging(log_path: str) -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Servidor de Nombres de Recursos (UDP)")
    parser.add_argument("--folder", type=str, default="", help="Ruta absoluta de la carpeta a vigilar")
    parser.add_argument("--config", type=str, default="config.json", help="Ruta al archivo de configuración")
    parser.add_argument("--scan-interval", type=int, default=300, help="Segundos entre escaneos (default 300)")
    # --- Argumentos nuevos ---
    parser.add_argument("--server-ip", type=str, default="127.0.0.1", help="IP del servidor de archivos a anunciar")
    parser.add_argument("--server-port", type=int, default=5002, help="Puerto del servidor de archivos a anunciar")
    return parser.parse_args()


def ensure_folder_path(arg_folder: str, default_config_folder: str | None) -> str:
    folder = arg_folder.strip() or (default_config_folder or "")
    while not folder or not os.path.isdir(folder):
        if folder and not os.path.isdir(folder):
            print(f"La ruta no existe o no es carpeta: {folder}")
        folder = input("Ingresa la ruta ABSOLUTA de la carpeta a vigilar: ").strip()
    return os.path.abspath(folder)


def main() -> None:
    args = parse_args()

    setup_logging(os.path.join(os.getcwd(), "app.log"))
    log = logging.getLogger(__name__)

    config = ConfigManager(config_path=os.path.abspath(args.config))
    config.load()

    folder = ensure_folder_path(args.folder, config.get_folder())
    config.set_folder(folder)

    # Initial sync and prompting
    scanner = FolderScanner(folder_path=folder, config=config)
    scanner.initial_sync_with_prompts()
    config.save()

    # Start scanner thread
    scanner_thread = threading.Thread(
        target=scanner.run_periodic_scan,
        kwargs={"interval_seconds": max(5, args.scan_interval)},
        name="ScannerThread",
        daemon=True,
    )
    scanner_thread.start()

    # Start UDP server thread, pasando los nuevos argumentos
    udp_server = UdpServer(
        config=config,
        server_ip=args.server_ip,
        server_port=args.server_port
    )
    udp_thread = threading.Thread(target=udp_server.run, name="UDPServer", daemon=True)
    udp_thread.start()

    log.info(f"Servidor iniciado. Anunciando IP {args.server_ip}:{args.server_port}. Presiona Ctrl+C para salir.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Saliendo...")


if __name__ == "__main__":
    main()