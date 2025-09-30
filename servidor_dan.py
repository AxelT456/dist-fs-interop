# servidor_dan.py

import argparse
import logging
import os
import threading
import time
import json # --- CAMBIO: Importamos json

from app.config import ConfigManager
from app.scanner import FolderScanner
from app.udp_server import UdpServer

# --- CAMBIO: Cargamos la configuración de red al inicio ---
try:
    with open('network_config.json', 'r') as f:
        net_config = json.load(f)
    # Obtenemos la configuración específica para 'server_dan'
    dan_config = net_config['peers']['server_dan']
except (IOError, KeyError) as e:
    print(f"Error: No se pudo cargar la configuración para 'server_dan' desde network_config.json. {e}")
    # Valores de fallback por si falla la carga
    dan_config = {'server_ip': '127.0.0.1', 'server_port': 5006, 'dns_port': 50004}

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
    
    # --- CAMBIO: Usamos los valores del config como defaults ---
    parser.add_argument("--server-ip", type=str, default=dan_config['server_ip'], help="IP del servidor de archivos a anunciar")
    parser.add_argument("--server-port", type=int, default=dan_config['server_port'], help="Puerto del servidor de archivos a anunciar")
    parser.add_argument("--dns-port", type=int, default=dan_config['dns_port'], help="Puerto donde escucha este DNS local")
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

    scanner = FolderScanner(folder_path=folder, config=config)
    scanner.initial_sync_with_prompts()
    config.save()

    scanner_thread = threading.Thread(
        target=scanner.run_periodic_scan,
        kwargs={"interval_seconds": max(5, args.scan_interval)},
        name="ScannerThread", daemon=True,
    )
    scanner_thread.start()

    # --- CAMBIO: Pasamos explícitamente TODOS los valores de red al UdpServer ---
    udp_server = UdpServer(
        config=config,
        port=args.dns_port, # El puerto donde escucha este DNS
        server_ip=args.server_ip, # La IP del servidor de archivos que anuncia
        server_port=args.server_port # El puerto del servidor de archivos que anuncia
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
    
    