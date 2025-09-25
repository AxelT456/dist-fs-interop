# app/udp_server.py

import json
import logging
import os
import socket
from typing import Any, Dict, Tuple

from .config import ConfigManager

log = logging.getLogger(__name__)


class UdpServer:
    def __init__(
        self,
        config: ConfigManager,
        # CAMBIO: IP y puerto donde este servidor DNS escuchará
        host: str = "0.0.0.0",
        port: int = 50004,
        # CAMBIO: IP y puerto del servidor de archivos que se anunciará
        server_ip: str = "127.0.0.9",
        server_port: int = 5006,
    ) -> None:
        self._config = config
        self._host = host
        self._port = port
        self._server_ip = server_ip
        self._server_port = server_port

    # En app/udp_server.py, reemplaza el método _handle_request
    def _handle_request(self, data: bytes, addr: Tuple[str, int]) -> bytes:
        try:
            payload = json.loads(data.decode("utf-8"))
            action = payload.get("accion")

            if action == "consultar" and payload.get("nombre_archivo") == "servidor_info":
                response = { "status": "ACK", "ip": self._server_ip, "puerto": self._server_port, }
            elif action == "consultar_ip":
                response = self._handle_query(payload)
            elif action == "listar_archivos":
                response = self._handle_list()
            else:
                response = {"status": "NACK", "error": "accion no reconocida"}
        except Exception as e:
            log.error(f"Error procesando la solicitud de {addr}: {e}")
            response = {"status": "NACK", "error": "internal server error"}
        return json.dumps(response).encode("utf-8")

    def _handle_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Maneja la acción 'consultar_ip' para un archivo específico.
        """
        filename = payload.get("filename")
        if not filename or not isinstance(filename, str):
            return {"status": "NACK", "error": "invalid filename"}

        meta = self._config.get_file(filename)

        if meta and meta.publish:
            return {
                "status": "ACK",
                "filename": filename,
                "ttl": meta.ttl,
                "ip": self._server_ip,
                "port": self._server_port,
            }
        else:
            return {
                "status": "NACK",
                "filename": filename,
                "error": "archivo no encontrado o no publicado",
            }

    def _handle_list(self) -> Dict[str, Any]:
        """
        Maneja la acción 'listar_archivos' para devolver todos los archivos publicados.
        """
        published_files = self._config.list_published_files()
        
        file_list = []
        for name, config in published_files.items():
            _, ext = os.path.splitext(name)
            file_list.append({
                "nombre_archivo": name,
                "extension": ext.lstrip("."),
                "publicado": config.publish,
                "ttl": config.ttl,
            })

        return {
            "status": "ACK",
            "archivos": file_list,
            "total": len(file_list),
            "ip": self._server_ip,
            "port": self._server_port,
        }

    def run(self) -> None:
        log.info(f"Servidor UDP escuchando en {self._host}:{self._port}")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self._host, self._port))
            while True:
                try:
                    data, addr = sock.recvfrom(8192)
                    log.info(f"Recibida petición de {addr}")
                    resp = self._handle_request(data, addr)
                    sock.sendto(resp, addr)
                except Exception as e:
                    log.error(f"Error en el bucle principal del servidor UDP: {e}")