# /src/network/dns_translator/translator.py (Versión Mejorada para Sistema Distribuido)

import json
import socket
import logging
from typing import Dict, Optional, Tuple, List

# ==============================================================================
# ==                            DRIVERS ESPECÍFICOS                           ==
# ==============================================================================

def driver_servidor_nombres(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """
    Driver para servidor_nombres.py (tu servidor original)
    Traduce peticiones estándar a formato específico de servidor_nombres
    """
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                # Formato: {"accion": "consultar", "nombre_archivo": "filename"}
                dns_request = {
                    "accion": "consultar",
                    "nombre_archivo": request.get("nombre_archivo", "server_info")
                }
            elif accion == "listar_archivos":
                # Formato: {"accion": "listar_archivos"}
                dns_request = {"accion": "listar_archivos"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            # Enviar petición
            sock.sendto(json.dumps(dns_request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(4096)
            response = json.loads(data.decode('utf-8'))
            
            return response
            
    except Exception as e:
        logging.error(f"Error en driver_servidor_nombres: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

def driver_servidor_christian(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """
    Driver para servidor_christian.py 
    Traduce peticiones estándar a formato de Christian
    """
    accion = request.get("accion")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            if accion == "consultar":
                # Formato Christian: {"filename": "name", "extension": "ext", "type": "check"}
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
                # Formato Christian: {"type": "list"}
                dns_request = {"type": "list"}
            else:
                return {"status": "ERROR", "mensaje": f"Acción {accion} no soportada"}
            
            # Enviar petición
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
                            "ttl": 3600,  # TTL por defecto
                            "bandera": 0,
                            "ip_origen": response.get("ip", "127.0.0.12")
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

def driver_dns_general(request: Dict, dns_address: Tuple[str, int]) -> Dict:
    """
    Driver para DNS General (sistema distribuido)
    Maneja comunicación directa con el DNS General
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            
            # El DNS General ya usa formato estándar, solo pasamos la petición
            sock.sendto(json.dumps(request).encode('utf-8'), dns_address)
            data, addr = sock.recvfrom(8192)  # Buffer más grande para listas
            response = json.loads(data.decode('utf-8'))
            
            return response
            
    except Exception as e:
        logging.error(f"Error en driver_dns_general: {e}")
        return {"status": "ERROR", "mensaje": str(e)}

# ==============================================================================
# ==                           CLASE DNSTranslator MEJORADA                   ==
# ==============================================================================

class DNSTranslator:
    """
    Traductor DNS mejorado que permite comunicación uniforme con diferentes
    tipos de servidores DNS manteniendo compatibilidad total.
    """
    
    def __init__(self, config_file: str = None, config_dict: Dict = None):
        """
        Inicializa el traductor con configuración desde archivo o diccionario
        """
        if config_file:
            self.config = self._load_config_from_file(config_file)
        elif config_dict:
            self.config = config_dict
        else:
            # Configuración por defecto
            self.config = self._get_default_config()
        
        self.dns_servers = {dns["id"]: dns for dns in self.config.get("dns_servers", [])}
        self.drivers = self._register_drivers()
        
        logging.info(f"DNSTranslator inicializado con {len(self.drivers)} drivers")
    
    def _load_config_from_file(self, config_file: str) -> Dict:
        """Carga configuración desde archivo JSON"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error cargando configuración: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Configuración por defecto del sistema"""
        return {
            "dns_servers": [
                {
                    "id": "servidor_nombres",
                    "type": "servidor_nombres",
                    "host": "127.0.0.2",
                    "port": 50000,
                    "driver": "driver_servidor_nombres"
                },
                {
                    "id": "servidor_christian", 
                    "type": "servidor_christian",
                    "host": "127.0.0.12",
                    "port": 50000,
                    "driver": "driver_servidor_christian"
                },
                {
                    "id": "dns_general",
                    "type": "dns_general", 
                    "host": "127.0.0.5",
                    "port": 50005,
                    "driver": "driver_dns_general"
                }
            ],
            "default_dns": "servidor_nombres",
            "fallback_dns": ["dns_general", "servidor_christian"]
        }
    
    def _register_drivers(self) -> Dict:
        """Registra todos los drivers disponibles"""
        return {
            "driver_servidor_nombres": driver_servidor_nombres,
            "driver_servidor_christian": driver_servidor_christian,
            "driver_dns_general": driver_dns_general
        }
    
    def resolve(self, request: Dict, dns_id: str = None, use_fallback: bool = True) -> Dict:
        """
        Resuelve una petición usando el DNS especificado
        
        Args:
            request: Petición estándar {"accion": "consultar|listar_archivos", "nombre_archivo": "..."}
            dns_id: ID del DNS a usar (None para usar el por defecto)
            use_fallback: Si usar DNS de respaldo en caso de fallo
            
        Returns:
            Respuesta estándar del DNS
        """
        # Usar DNS por defecto si no se especifica
        if not dns_id:
            dns_id = self.config.get("default_dns", "servidor_nombres")
        
        # Intentar resolución con DNS principal
        result = self._try_resolve(request, dns_id)
        
        # Si falla y está habilitado el fallback, intentar con otros DNS
        if result.get("status") == "ERROR" and use_fallback:
            fallback_dns_list = self.config.get("fallback_dns", [])
            for fallback_dns in fallback_dns_list:
                if fallback_dns != dns_id:  # No repetir el mismo DNS
                    logging.info(f"Intentando fallback con {fallback_dns}")
                    result = self._try_resolve(request, fallback_dns)
                    if result.get("status") != "ERROR":
                        result["fallback_used"] = fallback_dns
                        break
        
        return result
    
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
            
            return result
            
        except Exception as e:
            logging.error(f"Error en resolución con {dns_id}: {e}")
            return {"status": "ERROR", "mensaje": str(e)}
    
    def resolve_with_multiple_dns(self, request: Dict, dns_list: List[str] = None) -> List[Dict]:
        """
        Resuelve con múltiples DNS y devuelve todas las respuestas
        Útil para comparar resultados o hacer búsquedas amplias
        """
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
                "status": "available"
            }
            for dns_id, config in self.dns_servers.items()
        ]
    
    def test_dns_connectivity(self, dns_id: str = None) -> Dict:
        """Prueba la conectividad con un DNS específico"""
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
                    "response_time": "< 5s",  # Simplificado
                    "details": result
                }
            except Exception as e:
                results[dns] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results