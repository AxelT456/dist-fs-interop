# translator_integrated.py - Traductor integrado con DNS General
import json
import socket
import logging
from typing import Dict, Optional, Tuple, List

# Configuración del DNS General
DNS_GENERAL_IP = "127.0.0.5"
DNS_GENERAL_PORT = 50005

# ==============================================================================
# ==                            DRIVERS ESPECÍFICOS                           ==
# ==============================================================================

def driver_servidor_nombres(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_nombres.py (tu servidor original)"""
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                dns_request = {
                    "accion": "consultar",
                    "nombre_archivo": request.get("nombre_archivo", "server_info")
                }
            elif accion == "listar_archivos":
                dns_request = {"accion": "listar_archivos"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            return response
            
    except Exception as e:
        logging.error(f"Error en driver_servidor_nombres: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_christian(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_christian.py"""
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                nombre_archivo = request.get("nombre_archivo", "server_info.check")
                if "." in nombre_archivo:
                    filename, extension = nombre_archivo.rsplit(".", 1)
                else:
                    filename, extension = nombre_archivo, "check"
                
                dns_request = {
                    "filename": filename,
                    "extension": extension,
                    "type": "check"
                }
            elif accion == "listar_archivos":
                dns_request = {"type": "list"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            # Traducir respuesta de Christian a formato estándar
            if response.get("response") == "ACK":
                if "files" in response:  # Lista de archivos
                    archivos = []
                    for file_info in response.get("files", []):
                        archivos.append({
                            "nombre_archivo": f"{file_info['name']}.{file_info['extension']}",
                            "extension": f".{file_info['extension']}",
                            "publicado": True,
                            "ttl": 3600,
                            "bandera": 0,
                            "ip_origen": response.get("ip", "127.0.0.12"),
                            "servidor_principal": "SERVER2"
                        })
                    
                    return {
                        "status": "ACK",
                        "archivos": archivos,
                        "total": response.get("count", 0),
                        "ip": response.get("ip"),
                        "puerto": response.get("port")
                    }
                else:  # Consulta individual
                    return {
                        "status": "ACK",
                        "nombre_archivo": request.get("nombre_archivo"),
                        "ttl": 3600,
                        "ip": response.get("ip"),
                        "puerto": response.get("port")
                    }
            else:
                return {
                    "status": "NACK",
                    "mensaje": response.get("reason", "Archivo no encontrado"),
                    "ip": response.get("ip"),
                    "puerto": response.get("port")
                }
            
    except Exception as e:
        logging.error(f"Error en driver_servidor_christian: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_marco(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_marco.py actualizado"""
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                nombre_archivo = request.get("nombre_archivo", "test.txt")
                if "." in nombre_archivo:
                    name, extension = nombre_archivo.rsplit(".", 1)
                else:
                    name, extension = nombre_archivo, "txt"
                
                dns_request = {
                    "accion": "consultar",
                    "name": name,
                    "extension": extension
                }
            elif accion == "listar_archivos":
                dns_request = {"accion": "listar_archivos"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            # Traducir respuesta de Marco a formato estándar
            if response.get("status") == "ACK":
                if "files" in response:  # Lista de archivos
                    archivos = []
                    for file_info in response.get("files", []):
                        archivos.append({
                            "nombre_archivo": f"{file_info['name']}.{file_info['extension']}",
                            "extension": f".{file_info['extension']}",
                            "publicado": True,
                            "ttl": file_info.get("ttl", 3600),
                            "bandera": 0,
                            "ip_origen": response.get("ip", "127.0.0.8"),
                            "servidor_principal": "SERVER_MARCO"
                        })
                    
                    return {
                        "status": "ACK",
                        "archivos": archivos,
                        "total": len(archivos),
                        "ip": response.get("ip"),
                        "puerto": response.get("port")
                    }
                else:  # Consulta individual
                    return {
                        "status": "ACK",
                        "nombre_archivo": request.get("nombre_archivo"),
                        "ttl": response.get("ttl", 3600),
                        "ip": response.get("ip"),
                        "puerto": response.get("port")
                    }
            else:
                return {
                    "status": "NACK",
                    "mensaje": response.get("error", "Archivo no encontrado o TTL expirado"),
                    "ip": response.get("ip", "127.0.0.8"),
                    "puerto": response.get("port", 5005)
                }
            
    except Exception as e:
        logging.error(f"Error en driver_servidor_marco: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_dan(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_dan.py (usa módulos app)"""
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                nombre_archivo = request.get("nombre_archivo", "test.txt")
                dns_request = {
                    "accion": "consultar_ip",
                    "filename": nombre_archivo
                }
            elif accion == "listar_archivos":
                dns_request = {"accion": "listar_archivos"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            # Traducir respuesta de Dan a formato estándar
            if response.get("status") == "ACK":
                if "archivos" in response:  # Lista de archivos
                    return response  # Ya está en formato estándar
                else:  # Consulta individual
                    return {
                        "status": "ACK",
                        "nombre_archivo": response.get("filename"),
                        "ttl": response.get("ttl", 3600),
                        "ip": response.get("ip"),
                        "puerto": response.get("port")
                    }
            else:
                return {
                    "status": "NACK",
                    "mensaje": response.get("error", "Archivo no encontrado"),
                    "ip": response.get("ip", "127.0.0.9"),
                    "puerto": response.get("port", 5006)
                }
            
    except Exception as e:
        logging.error(f"Error en driver_servidor_dan: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_gus(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para servidor_gus.py"""
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                dns_request = {"action": "get_server_info"}
            elif accion == "listar_archivos":
                dns_request = {"action": "list_all_files"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            # Traducir respuesta de Gus a formato estándar
            if response.get("status") == "ACK":
                if "files" in response:  # Lista de archivos
                    archivos = []
                    for file_info in response.get("files", []):
                        if file_info.get("can_publish", True):
                            archivos.append({
                                "nombre_archivo": f"{file_info['name']}.{file_info['extension']}",
                                "extension": f".{file_info['extension']}",
                                "publicado": True,
                                "ttl": file_info.get("ttl", 3600),
                                "bandera": 0,
                                "ip_origen": response.get("ip", "127.0.0.10"),
                                "servidor_principal": "SERVER_GUS"
                            })
                    
                    return {
                        "status": "ACK",
                        "archivos": archivos,
                        "total": len(archivos),
                        "ip": response.get("ip"),
                        "puerto": response.get("port", 5007)
                    }
                else:  # Información del servidor
                    return {
                        "status": "ACK",
                        "ip": response.get("ip"),
                        "puerto": response.get("port", 5007)
                    }
            else:
                return {
                    "status": "NACK",
                    "mensaje": response.get("reason", "Error en servidor Gus"),
                    "ip": "127.0.0.10",
                    "puerto": 5007
                }
            
    except Exception as e:
        logging.error(f"Error en driver_servidor_gus: {e}")
        return {"status": "ERROR", "mensaje": str(e)}
    """Driver para DNS General (sistema distribuido)"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            # El DNS General ya usa formato estándar
            sock.sendto(json.dumps(request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            return response
            
    except Exception as e:
        logging.error(f"Error en driver_dns_general: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

def driver_dns_general(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """Driver para DNS General (sistema distribuido)"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            # El DNS General ya usa formato estándar
            sock.sendto(json.dumps(request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(8192)
            response = json.loads(data.decode('utf-8'))
            
            return response
            
    except Exception as e:
        logging.error(f"Error en driver_dns_general: {e}")
        return {"status": "ERROR", "mensaje": str(e)}
    
# ==============================================================================
# ==                           CLASE DNSTranslator MEJORADA                   ==
# ==============================================================================

class DNSTranslatorIntegrated:
    """
    Traductor DNS integrado que maneja comunicación con DNS locales 
    y DNS General del sistema distribuido.
    """
    
    def __init__(self, config_dict: Dict = None):
        """Inicializa el traductor con configuración"""
        if config_dict:
            self.config = config_dict
        else:
            self.config = self._get_default_config()
        
        self.dns_servers = {dns["id"]: dns for dns in self.config.get("dns_servers", [])}
        self.drivers = self._register_drivers()
        
        logging.info(f"DNSTranslatorIntegrated inicializado con {len(self.drivers)} drivers")
    
    def _get_default_config(self) -> Dict:
        """Configuración por defecto del sistema distribuido expandido"""
        return {
            "dns_servers": [
                {
                    "id": "servidor_nombres",
                    "type": "servidor_nombres",
                    "host": "127.0.0.2",
                    "port": 50000,
                    "driver": "driver_servidor_nombres",
                    "server_id": "SERVER1"
                },
                {
                    "id": "servidor_christian", 
                    "type": "servidor_christian",
                    "host": "127.0.0.12",
                    "port": 50000,
                    "driver": "driver_servidor_christian",
                    "server_id": "SERVER2"
                },
                {
                    "id": "servidor_marco",
                    "type": "servidor_marco",
                    "host": "127.0.0.8",
                    "port": 50000,
                    "driver": "driver_servidor_marco",
                    "server_id": "SERVER_MARCO"
                },
                {
                    "id": "servidor_dan",
                    "type": "servidor_dan",
                    "host": "127.0.0.9",
                    "port": 50000,
                    "driver": "driver_servidor_dan",
                    "server_id": "SERVER_DAN"
                },
                {
                    "id": "servidor_gus",
                    "type": "servidor_gus",
                    "host": "127.0.0.10",
                    "port": 50000,
                    "driver": "driver_servidor_gus",
                    "server_id": "SERVER_GUS"
                },
                {
                    "id": "dns_alternativo",
                    "type": "servidor_nombres", 
                    "host": "127.0.0.7",
                    "port": 50001,
                    "driver": "driver_servidor_nombres",
                    "server_id": "SERVER3"
                },
                {
                    "id": "dns_general",
                    "type": "dns_general", 
                    "host": DNS_GENERAL_IP,
                    "port": DNS_GENERAL_PORT,
                    "driver": "driver_dns_general",
                    "server_id": "DNS_GENERAL"
                }
            ],
            "default_dns": "dns_general",
            "fallback_dns": ["servidor_nombres", "servidor_christian", "servidor_marco", "servidor_dan", "servidor_gus", "dns_alternativo"]
        }
    
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
    
    def resolve_for_server(self, request: Dict, server_id: str) -> Dict:
        """
        Resuelve una petición para un servidor específico usando DNS General.
        Usado por servidores para comunicarse entre ellos.
        """
        # Siempre usar DNS General para comunicación entre servidores
        dns_general_request = request.copy()
        dns_general_request["requesting_server"] = server_id
        
        return self._try_resolve(dns_general_request, "dns_general")
    
    def resolve_for_client(self, request: Dict, preferred_dns: str = None) -> Dict:
        """
        Resuelve una petición para un cliente.
        Puede usar DNS local o DNS General según disponibilidad.
        """
        # Si se especifica un DNS preferido, usarlo primero
        if preferred_dns and preferred_dns in self.dns_servers:
            result = self._try_resolve(request, preferred_dns)
            if result.get("status") != "ERROR":
                return result
        
        # Usar DNS por defecto (DNS General)
        result = self._try_resolve(request, "dns_general")
        if result.get("status") != "ERROR":
            return result
        
        # Fallback a DNS locales
        for fallback_dns in self.config.get("fallback_dns", []):
            logging.info(f"Intentando fallback con {fallback_dns}")
            result = self._try_resolve(request, fallback_dns)
            if result.get("status") != "ERROR":
                result["fallback_used"] = fallback_dns
                return result
        
        return {"status": "ERROR", "mensaje": "Ningún DNS disponible"}
    
    def request_remote_action(self, server_id: str, action_request: Dict) -> Dict:
        """
        Solicita una acción a un servidor remoto a través del DNS General.
        Usado por servidores para coordinar acciones.
        """
        remote_request = {
            "accion": "solicitar_remoto",
            "server_id": server_id,
            **action_request
        }
        
        return self._try_resolve(remote_request, "dns_general")
    
    def register_server_with_general(self, server_info: Dict) -> Dict:
        """
        Registra un servidor con el DNS General.
        """
        register_request = {
            "accion": "registrar_servidor",
            **server_info
        }
        
        return self._try_resolve(register_request, "dns_general")
    
    def _try_resolve(self, request: Dict, dns_id: str) -> Dict:
        """Intenta resolver con un DNS específico"""
        if dns_id not in self.dns_servers:
            return {"status": "ERROR", "mensaje": f"DNS {dns_id} no encontrado en configuración"}
        
        dns_config = self.dns_servers[dns_id]
        driver_name = dns_config.get("driver")
        
        if driver_name not in self.drivers:
            return {"status": "ERROR", "mensaje": f"Driver {driver_name} no encontrado"}
        
        try:
            driver_function = self.drivers[driver_name]
            dns_address = (dns_config["host"], dns_config["port"])
            
            logging.debug(f"Resolviendo con {dns_id} usando {driver_name}")
            result = driver_function(request, dns_address)
            
            # Añadir información del DNS usado
            if isinstance(result, dict):
                result["dns_used"] = dns_id
                result["dns_type"] = dns_config.get("type")
                result["server_id"] = dns_config.get("server_id")
            
            return result
            
        except Exception as e:
            logging.error(f"Error en resolución con {dns_id}: {e}")
            return {"status": "ERROR", "mensaje": str(e)}
    
    def send_heartbeat(self, server_info: Dict) -> Dict:
        """Envía heartbeat al DNS General"""
        heartbeat_request = {
            "accion": "heartbeat",
            **server_info
        }
        
        return self._try_resolve(heartbeat_request, "dns_general")
    
    def get_global_file_list(self) -> Dict:
        """Obtiene la lista global de archivos del DNS General"""
        list_request = {"accion": "listar_archivos"}
        return self._try_resolve(list_request, "dns_general")
    
    def find_file_location(self, nombre_archivo: str) -> Dict:
        """Encuentra la ubicación de un archivo específico"""
        search_request = {
            "accion": "consultar",
            "nombre_archivo": nombre_archivo
        }
        
        return self._try_resolve(search_request, "dns_general")
    
    def resolve_with_multiple_dns(self, request: Dict, dns_list: List[str] = None) -> List[Dict]:
        """Resuelve con múltiples DNS y devuelve todas las respuestas"""
        if not dns_list:
            dns_list = list(self.dns_servers.keys())
        
        results = []
        for dns_id in dns_list:
            result = self._try_resolve(request, dns_id)
            results.append(result)
        
        return results
    
    def get_available_dns(self) -> List[Dict]:
        """Devuelve lista de DNS disponibles"""
        return [
            {
                "id": dns_id,
                "type": config.get("type"),
                "host": config["host"],
                "port": config["port"],
                "server_id": config.get("server_id"),
                "status": "available"
            }
            for dns_id, config in self.dns_servers.items()
        ]
    
    def test_connectivity(self, dns_id: str = None) -> Dict:
        """Prueba la conectividad con DNS específico o todos"""
        if dns_id:
            dns_list = [dns_id]
        else:
            dns_list = list(self.dns_servers.keys())
        
        test_request = {"accion": "consultar", "nombre_archivo": "connectivity_test"}
        results = {}
        
        for dns in dns_list:
            try:
                result = self._try_resolve(test_request, dns)
                results[dns] = {
                    "status": "connected" if result.get("status") != "ERROR" else "error",
                    "response_time": "< 5s",
                    "details": result
                }
            except Exception as e:
                results[dns] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results

# ==============================================================================
# ==                           FUNCIONES DE UTILIDAD                          ==
# ==============================================================================

def create_translator_for_server(server_id: str) -> DNSTranslatorIntegrated:
    """Crea un traductor configurado para un servidor específico"""
    config = {
        "dns_servers": [
            {
                "id": "dns_general",
                "type": "dns_general", 
                "host": DNS_GENERAL_IP,
                "port": DNS_GENERAL_PORT,
                "driver": "driver_dns_general",
                "server_id": "DNS_GENERAL"
            }
        ],
        "default_dns": "dns_general",
        "fallback_dns": []
    }
    
    translator = DNSTranslatorIntegrated(config)
    return translator

def create_translator_for_client() -> DNSTranslatorIntegrated:
    """Crea un traductor configurado para clientes"""
    # Usar configuración completa con todos los DNS
    translator = DNSTranslatorIntegrated()
    return translator

# ==============================================================================
# ==                               EJEMPLO DE USO                             ==
# ==============================================================================

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== Traductor DNS Integrado ===")
    print("Sistema distribuido con DNS General")
    
    # Crear traductor para cliente
    translator = create_translator_for_client()
    
    print(f"DNS disponibles: {len(translator.get_available_dns())}")
    for dns in translator.get_available_dns():
        print(f"  - {dns['id']}: {dns['host']}:{dns['port']} ({dns['type']})")
    
    # Ejemplo de consulta
    print("\nProbando consulta...")
    result = translator.resolve_for_client({
        "accion": "consultar", 
        "nombre_archivo": "test.txt"
    })
    print(f"Resultado: {result.get('status', 'ERROR')}")
    
    # Ejemplo de listado
    print("\nProbando listado...")
    result = translator.resolve_for_client({
        "accion": "listar_archivos"
    })
    print(f"Archivos encontrados: {len(result.get('archivos', []))}")
    
    # Prueba de conectividad
    print("\nProbando conectividad...")
    connectivity = translator.test_connectivity()
    for dns_id, status in connectivity.items():
        print(f"  - {dns_id}: {status['status']}")
    
    print("\n=== Traductor listo para uso ===")