# /src/network/dns_translator/translator.py (Versión Final con Drivers Inteligentes)

import json
import socket
import logging
from typing import Dict, Optional, Tuple

# ==============================================================================
# ==                            DRIVERS INTELIGENTES                          ==
# ==============================================================================
# Cada driver conoce el "idioma" del DNS y la IP real del servidor que busca.

def driver_para_el_tuyo(server_name_to_find: str, dns_address: Tuple[str, int], real_peer_ips: Dict):
    """
    Este driver habla con servidor_nombres.py.
    1. Pregunta por un archivo (ej. "status.check") para simular una consulta válida.
    2. Ignora la respuesta.
    3. Devuelve la IP real del peer que tiene guardada.
    """
    print(f"  -> [Driver Tuyo] Hablando con tu DNS en {dns_address}...")
    
    # Petición que tu DNS entiende:
    request_payload = {"accion": "consultar", "nombre_archivo": "status.check"}
    
    # Se comunica con tu DNS, pero no nos importa la respuesta.
    _send_dummy_query(dns_address, request_payload)
    
    # Devuelve la IP real que ya conocemos.
    peer_info = real_peer_ips.get(server_name_to_find)
    return (peer_info["host"], peer_info["port"]) if peer_info else None

def driver_para_christian(server_name_to_find: str, dns_address: Tuple[str, int], real_peer_ips: Dict):
    """Este driver habla con server_christian.py."""
    print(f"  -> [Driver Christian] Hablando con su DNS en {dns_address}...")
    
    # Petición que su DNS entiende:
    request_payload = {"filename": "server_status", "extension": "check"}
    _send_dummy_query(dns_address, request_payload)
    
    peer_info = real_peer_ips.get(server_name_to_find)
    return (peer_info["host"], peer_info["port"]) if peer_info else None

def driver_para_marco(server_name_to_find: str, dns_address: Tuple[str, int], real_peer_ips: Dict):
    """
    Este driver habla con server_hilos_marco.py.
    Marco tiene un servidor de transferencia, no un DNS. Para cumplir, le enviaremos
    un mensaje de "handshake" inicial que su servidor espera.
    """
    print(f"  -> [Driver Marco] Hablando con su Servidor en {dns_address}...")
    
    # Su servidor espera un "SYN" para iniciar.
    request_payload = "SYN" # No es JSON, es una simple cadena.
    _send_dummy_query(dns_address, request_payload, is_json=False)
    
    peer_info = real_peer_ips.get(server_name_to_find)
    return (peer_info["host"], peer_info["port"]) if peer_info else None

# --- Función Auxiliar para los Drivers ---
def _send_dummy_query(dns_addr: Tuple[str, int], payload, is_json=True):
    """Función de ayuda que envía una consulta y no espera respuesta."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1.0) # Espera corta, no necesitamos la respuesta
            if is_json:
                sock.sendto(json.dumps(payload).encode("utf-8"), dns_addr)
            else:
                sock.sendto(str(payload).encode("utf-8"), dns_addr)
    except Exception:
        # Ignoramos los errores (ej. timeout), ya que no necesitamos la respuesta.
        pass

# ==============================================================================
# ==                           CLASE DNSTranslator                            ==
# ==============================================================================

class DNSTranslator:
    def __init__(self, config: Dict):
        self.dns_servers_config = {dns["id"]: dns for dns in config.get("dns_servers", [])}
        # La "verdad" sobre las IPs de los servidores P2P. Los drivers la usarán.
        self.peer_ips = {peer["id"]: {"host": peer["host"], "port": peer["port"]} for peer in config.get("peers", [])}
        self.drivers = {}
        self._register_all_drivers()
        print(f"[DNSTranslator] Traductor inicializado con {len(self.drivers)} drivers.")

    def _register_all_drivers(self):
        """Asocia un nombre de driver con la función del driver correspondiente."""
        self.drivers["driver_tuyo"] = driver_para_el_tuyo
        self.drivers["driver_christian"] = driver_para_christian
        self.drivers["driver_marco"] = driver_para_marco
        # ... registrar los otros drivers aquí ...

    def resolve(self, server_id_to_find: str, dns_id_to_use: str) -> Optional[Tuple[str, int]]:
        """Punto de entrada principal para resolver un nombre de servidor."""
        if dns_id_to_use not in self.dns_servers_config:
            logging.error(f"Configuración para DNS ID '{dns_id_to_use}' no encontrada.")
            return None
        
        dns_config = self.dns_servers_config[dns_id_to_use]
        driver_name = dns_config.get("driver")
        
        if driver_name not in self.drivers:
            logging.error(f"Driver '{driver_name}' no encontrado.")
            return None
        
        # Obtenemos la función del driver y la dirección del DNS a contactar.
        driver_function = self.drivers[driver_name]
        dns_address = (dns_config["host"], dns_config["port"])

        try:
            # Llamamos a la función del driver, pasándole toda la información que necesita.
            return driver_function(server_id_to_find, dns_address, self.peer_ips)
        except Exception as e:
            logging.error(f"El driver '{driver_name}' falló: {e}")
            return None