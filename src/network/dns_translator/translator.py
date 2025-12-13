# translator.py (Versión Final Definitiva)

import json
import socket
import logging
from typing import Dict, Optional, Tuple, List

# ==============================================================================
# ==                            DRIVERS ESPECÍFICOS                           ==
# ==============================================================================

def driver_servidor_nombres(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_nombres.py"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
           # --- CAMBIO: Usar 0.0.0.0 permite salir a la red O quedarse local ---
            # El 0 en el puerto indica al OS que asigne un puerto efímero aleatorio libre.
            sock.bind(('0.0.0.0', 0))
            
            accion = request.get("accion")
            print("INtento de ver info : ", accion)
            if accion == "consultar":
                dns_request = {"accion": "consultar", "nombre_archivo": request.get("nombre_archivo", "server_info")}
            elif accion == "listar_archivos":
                dns_request = {"accion": "listar_archivos"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            print("FIN DE CONSULTA O LISTAR a tomar en cuenta ",dns_address)
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            print("SEND LISTO")
            data, addr = sock.recvfrom(4096)
            print("DATA LISTO")
            print("Data recibida del servidor de nombres: ", data)
            return json.loads(data.decode('utf-8'))
    except Exception as e:
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_christian(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_christian.py"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            # --- CAMBIO: Usar 0.0.0.0 permite salir a la red O quedarse local ---
            # El 0 en el puerto indica al OS que asigne un puerto efímero aleatorio libre.
            sock.bind(('0.0.0.0', 0))

            accion = request.get("accion")
            nombre_archivo = request.get("nombre_archivo")
            if accion == "consultar" and nombre_archivo == "servidor_info":
                dns_request = {"accion": "consultar", "nombre_archivo": "servidor_info"}
            elif accion == "listar_archivos":
                dns_request = {"type": "list"}
            else:
                if "." in nombre_archivo:
                    filename, extension = nombre_archivo.rsplit(".", 1)
                else:
                    filename, extension = nombre_archivo, "check"
                dns_request = {"filename": filename, "extension": extension, "type": "check"}

            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK" or response.get("response") == "ACK":
                if "files" in response:
                    archivos = [{"nombre_archivo": f"{f['name']}.{f['extension']}", "publicado": True, "ttl": 3600} for f in response.get("files", [])]
                    return {"status": "ACK", "archivos": archivos, "total": len(archivos), "ip": response.get("ip"), "puerto": response.get("port")}
                else:
                    return {"status": "ACK", "ip": response.get("ip"), "puerto": response.get("puerto") or response.get("port")}
            else:
                return {"status": "NACK", "mensaje": response.get("reason", "Archivo no encontrado")}
    except Exception as e:
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_marco(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_marco.py"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            # --- CAMBIO: Usar 0.0.0.0 permite salir a la red O quedarse local ---
            # El 0 en el puerto indica al OS que asigne un puerto efímero aleatorio libre.
            sock.bind(('0.0.0.0', 0))

            accion = request.get("accion")
            nombre_archivo = request.get("nombre_archivo")
            if accion == "consultar" and nombre_archivo == "servidor_info":
                dns_request = {"accion": "listar_archivos"}
            elif accion == "listar_archivos":
                dns_request = {"accion": "listar_archivos"}
            else:
                if "." in nombre_archivo:
                    name, extension = nombre_archivo.rsplit(".", 1)
                else:
                    name, extension = nombre_archivo, "txt"
                dns_request = {"accion": "consultar", "name": name, "extension": extension}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if accion == "consultar" and nombre_archivo == "servidor_info":
                return {"status": "ACK", "ip": response.get("ip"), "puerto": response.get("port")} if response.get("status") == "ACK" else {"status": "NACK", "mensaje": "No se pudo obtener la info del servidor"}
            
            if response.get("status") == "ACK":
                if "files" in response:
                    archivos = [{"nombre_archivo": f"{f['name']}.{f['extension']}", "publicado": True, "ttl": f.get("ttl", 3600)} for f in response.get("files", [])]
                    return {"status": "ACK", "archivos": archivos, "total": len(archivos), "ip": response.get("ip"), "puerto": response.get("port")}
                else:
                    return {"status": "ACK", "ip": response.get("ip"), "puerto": response.get("port")}
            else:
                return {"status": "NACK", "mensaje": response.get("error", "Error")}
    except Exception as e:
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_dan(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_dan.py"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            # --- CAMBIO: Usar 0.0.0.0 permite salir a la red O quedarse local ---
            # El 0 en el puerto indica al OS que asigne un puerto efímero aleatorio libre.
            sock.bind(('0.0.0.0', 0))

            accion = request.get("accion")
            nombre_archivo = request.get("nombre_archivo")
            if accion == "consultar" and nombre_archivo == "servidor_info":
                dns_request = {"accion": "consultar", "nombre_archivo": "servidor_info"}
            elif accion == "consultar":
                dns_request = {"accion": "consultar_ip", "filename": nombre_archivo}
            elif accion == "listar_archivos":
                dns_request = {"accion": "listar_archivos"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}

            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            return response if response.get("status") == "ACK" else {"status": "NACK", "mensaje": response.get("error", "archivo no encontrado o no publicado")}
    except Exception as e:
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_gus(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_gus.py"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
           # --- CAMBIO: Usar 0.0.0.0 permite salir a la red O quedarse local ---
            # El 0 en el puerto indica al OS que asigne un puerto efímero aleatorio libre.
            sock.bind(('0.0.0.0', 0))

            accion = request.get("accion")
            if accion == "consultar" and request.get("nombre_archivo") == "servidor_info":
                dns_request = {"action": "get_server_info"}
            elif accion == "listar_archivos":
                dns_request = {"action": "list_all_files"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            if response.get("status") == "ACK":
                if "files" in response:
                    archivos = [{"nombre_archivo": f"{f['name']}.{f['extension']}", "publicado": True, "ttl": f.get("ttl", 3600)} for f in response.get("files", []) if f.get("can_publish", True)]
                    return {"status": "ACK", "archivos": archivos, "total": len(archivos), "ip": response.get("ip"), "puerto": response.get("port")}
                else:
                    return {"status": "ACK", "ip": response.get("ip"), "puerto": response.get("port")}
            else:
                return {"status": "NACK", "mensaje": response.get("reason", "Error")}
    except Exception as e:
        return {"status": "ERROR", "mensaje": str(e)}
    
def driver_dns_general(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para DNS General (sistema distribuido)"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            sock.sendto(json.dumps(request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(8192)
            return json.loads(data.decode('utf-8'))
    except Exception as e:
        logging.error(f"Error en driver_dns_general: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

# ==============================================================================
# ==                           CLASE DNSTranslator                            ==
# ==============================================================================

class DNSTranslatorIntegrated:
    def __init__(self):
        self.config = self._load_and_build_config()
        self.dns_servers = {dns["id"]: dns for dns in self.config.get("dns_servers", [])}
        self.drivers = self._register_drivers()
        logging.info(f"DNSTranslatorIntegrated inicializado con {len(self.drivers)} drivers desde config.")
        
    def _register_drivers(self) -> Dict:
        """Registra todos los drivers disponibles"""
        return {
            "driver_servidor_nombres": driver_servidor_nombres,
            "driver_servidor_christian": driver_servidor_christian,
            "driver_servidor_marco": driver_servidor_marco,
            "driver_servidor_dan": driver_servidor_dan,
            "driver_servidor_gus": driver_servidor_gus,
            "driver_dns_general": driver_dns_general
        }

    def _load_and_build_config(self) -> Dict:
        """Carga network_config.json y almacena AMBAS IPs (interna y externa)."""
        try:
            with open('network_config.json', 'r') as f:
                net_config = json.load(f)
        except Exception as e:
            logging.error(f"FATAL: No se pudo cargar network_config.json: {e}")
            return {"dns_servers": []}

        dns_servers_list = []
        peer_map = {
            "SERVER1": ("driver_servidor_nombres", "servidor_nombres"),
            "SERVER_MARCO": ("driver_servidor_marco", "servidor_marco"),
            "server_gus": ("driver_servidor_gus", "servidor_gus"),
            "server_christian": ("driver_servidor_christian", "servidor_christian"),
            "server_dan": ("driver_servidor_dan", "servidor_dan")
        }
        
        for server_id, peer_info in net_config.get("peers", {}).items():
            driver, type = peer_map.get(server_id, (None, None))
            if driver:
                dns_servers_list.append({
                    "id": peer_info["id_dns_cliente"],
                    "type": type,
                    # --- CAMBIO: Almacenamos ambas IPs con nombres claros ---
                    "host_internal": peer_info["dns_ip"],      # Para comunicación en la misma máquina
                    "host_external": peer_info["server_ip"],   # Para comunicación entre máquinas
                    "port": peer_info["dns_port"],
                    "driver": driver,
                    "server_id": server_id
                })
        # ... (el resto de la función para el dns_general no cambia) ...
        return {"dns_servers": dns_servers_list}

    def _try_resolve(self, request: Dict, dns_id: str, caller_context: str = 'external') -> Dict:
        """
        Intenta resolver con un DNS específico, usando una bandera de contexto para elegir la IP.
        """
        if dns_id not in self.dns_servers:
            return {"status": "ERROR", "mensaje": f"DNS {dns_id} no encontrado en configuración"}
        
        dns_config = self.dns_servers[dns_id]
        driver_name = dns_config.get("driver")
        
        if driver_name not in self.drivers:
            return {"status": "ERROR", "mensaje": f"Driver {driver_name} no encontrado"}
        
        try:
            driver_function = self.drivers[driver_name]
            
            # --- LÓGICA CONDICIONAL CON LA BANDERA ---
            if caller_context == 'internal':
                # El servidor usa la IP interna para hablar consigo mismo
                host_to_use = dns_config["host_internal"]
            else: # 'external' o cualquier otro valor
                # El cliente usa la IP externa para hablar por la red
                host_to_use = dns_config["host_external"]
            
            dns_address = (host_to_use, dns_config["port"])
            
            print(f"llegaste lejos crack ({caller_context})", dns_id)
            print("datos de direccion a conectar : ", dns_address)
            
            result = driver_function(request, dns_address)
            
            if isinstance(result, dict):
                result["dns_used"] = dns_id
            return result
        except Exception as e:
            logging.error(f"Error en resolución con {dns_id}: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

    def get_available_dns(self) -> List[Dict]:
        """Devuelve lista de DNS disponibles del archivo de configuración."""
        return self.config.get("dns_servers", [])