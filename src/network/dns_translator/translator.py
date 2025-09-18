# /src/network/dns_translator/translator.py

import json
import socket
import logging
from typing import Dict, Optional, Tuple

# --- Define aquí los 5 drivers de tu equipo ---
# Cada driver es un diccionario con dos funciones: 'encode' y 'decode'

def driver_checa():
    """Driver para el DNS que espera un formato específico."""
    return {
        "encode": lambda server_name: {"accion": "consultar", "nombre_servidor": server_name},
        "decode": lambda response: (response.get("ip"), response.get("port"))
    }

def driver_axel():
    """Driver para otro formato de DNS."""
    return {
        "encode": lambda server_name: {"type": "lookup", "server": server_name},
        "decode": lambda response: (response.get("address"), response.get("port"))
    }

# ... Añade aquí los drivers de los otros 3 integrantes ...

class DNSTranslator:
    def __init__(self, config: Dict):
        self.dns_servers_config = {dns["id"]: dns for dns in config.get("dns_servers", [])}
        self.drivers = {}
        self._register_drivers()
        print(f"[DNSTranslator] Traductor inicializado con {len(self.drivers)} drivers.")

    def _register_drivers(self):
        """Carga todos los drivers disponibles."""
        self.drivers["driver_checa"] = driver_checa()
        self.drivers["driver_axel"] = driver_axel()
        # ... registra los otros 3 drivers aquí ...

    def resolve(self, server_id: str, dns_id: str) -> Optional[Tuple[str, int]]:
        """
        Resuelve el nombre de un servidor usando el DNS y driver correctos.
        Este es el único método que el resto de la aplicación debe llamar.
        """
        if dns_id not in self.dns_servers_config:
            logging.error(f"Configuración para DNS ID '{dns_id}' no encontrada.")
            return None
        
        dns_config = self.dns_servers_config[dns_id]
        driver_name = dns_config.get("driver")
        
        if driver_name not in self.drivers:
            logging.error(f"Driver '{driver_name}' no encontrado para el DNS '{dns_id}'.")
            return None
        
        driver = self.drivers[driver_name]
        dns_address = (dns_config["host"], dns_config["port"])

        try:
            # 1. Codificar la petición usando el driver específico
            request_payload = driver["encode"](server_id)
            
            # 2. Enviar la consulta de red al servidor DNS
            response_payload = self._send_query(dns_address, request_payload)
            if not response_payload:
                return None

            # 3. Decodificar la respuesta usando el mismo driver
            ip, port = driver["decode"](response_payload)
            
            if ip and port:
                return (ip, port)
            return None
            
        except Exception as e:
            logging.error(f"Fallo en la resolución DNS para '{server_id}' usando '{dns_id}': {e}")
            return None

    def _send_query(self, dns_addr: Tuple[str, int], payload: Dict) -> Optional[Dict]:
        """Envía una consulta UDP a un servidor DNS y espera la respuesta."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(3.0) # 3 segundos de espera
                sock.sendto(json.dumps(payload).encode("utf-8"), dns_addr)
                data, _ = sock.recvfrom(4096)
                return json.loads(data.decode("utf-8"))
        except socket.timeout:
            logging.warning(f"Timeout consultando al DNS en {dns_addr}")
            return None
        except Exception as e:
            logging.error(f"Error de red consultando al DNS en {dns_addr}: {e}")
            return None