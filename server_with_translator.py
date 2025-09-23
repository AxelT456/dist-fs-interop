# server_with_translator.py - Servidor que usa el traductor integrado
import sys
import os
from typing import Dict, Optional, Tuple, List
# Agregar rutas necesarias
sys.path.append('src/network/dns_translator')
sys.path.append('src/network')

# Importar el servidor base y el traductor
from server_distributed import ServidorDistribuido
from translator_integrated import create_translator_for_server

class ServidorConTraductor(ServidorDistribuido):
    """Servidor distribuido que usa el traductor integrado"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inicializar traductor para este servidor
        self.translator = create_translator_for_server(self.server_id)
        self.log("Traductor DNS integrado inicializado")
    
    def _consultar_dns_general_via_translator(self, request: Dict) -> Dict:
        """Consulta el DNS General usando el traductor"""
        try:
            return self.translator.resolve_for_server(request, self.server_id)
        except Exception as e:
            self.log(f"Error usando traductor: {e}")
            return {"status": "ERROR", "mensaje": str(e)}
    
    def _find_file_location(self, nombre_archivo: str) -> Dict:
        """Encuentra ubicación de archivo usando traductor"""
        # Primero buscar localmente
        with self.local_files_lock:
            for archivo in self.local_files:
                if archivo["nombre_archivo"] == nombre_archivo:
                    return {
                        "found": True,
                        "local": True,
                        "server_id": self.server_id,
                        "ip": self.host,
                        "port": self.port
                    }
        
        # Buscar vía traductor
        try:
            result = self.translator.find_file_location(nombre_archivo)
            if result.get("status") == "ACK":
                return {
                    "found": True,
                    "local": False,
                    "server_id": result["server_id"],
                    "ip": result["ip"],
                    "port": result["puerto"]
                }
            else:
                return {"found": False}
        except Exception as e:
            self.log(f"Error buscando archivo via traductor: {e}")
            return {"found": False, "error": str(e)}
    
    def _register_with_dns_general(self):
        """Registra servidor usando traductor"""
        try:
            server_info = {
                "server_id": self.server_id,
                "ip": self.host,
                "port": self.port,
                "archivos": self.local_files
            }
            
            result = self.translator.register_server_with_general(server_info)
            
            if result.get("status") == "ACK":
                self.log("Registrado exitosamente vía traductor")
            else:
                self.log(f"Error en registro vía traductor: {result}")
                
        except Exception as e:
            self.log(f"Error registrando vía traductor: {e}")
    
    def _send_heartbeat(self):
        """Envía heartbeat usando traductor"""
        try:
            result = self.translator.send_heartbeat({"server_id": self.server_id})
            if result.get("status") != "ACK":
                self.log(f"Error en heartbeat: {result}")
        except Exception as e:
            self.log(f"Error enviando heartbeat vía traductor: {e}")
    
    def _handle_listar_archivos(self) -> Dict:
        """Lista archivos usando traductor"""
        try:
            result = self.translator.get_global_file_list()
            if result.get("status") == "ACK":
                return result
            else:
                # Fallback a archivos locales
                with self.local_files_lock:
                    return {
                        "status": "ACK",
                        "archivos": self.local_files.copy(),
                        "total": len(self.local_files),
                        "fuente": "local_only"
                    }
        except Exception as e:
            self.log(f"Error listando archivos vía traductor: {e}")
            # Fallback a archivos locales
            with self.local_files_lock:
                return {
                    "status": "ACK",
                    "archivos": self.local_files.copy(),
                    "total": len(self.local_files),
                    "fuente": "local_only",
                    "error": str(e)
                }
    
    def _request_remote_action(self, server_id: str, accion: str, nombre_archivo: str, contenido: str = None) -> Dict:
        """Solicita acción remota usando traductor"""
        try:
            action_request = {
                "accion": accion,
                "nombre_archivo": nombre_archivo,
                "origen_server_id": self.server_id
            }
            
            if contenido is not None:
                action_request["contenido"] = contenido
                
            return self.translator.request_remote_action(server_id, action_request)
            
        except Exception as e:
            self.log(f"Error en acción remota vía traductor: {e}")
            return {"status": "ERROR", "mensaje": str(e)}

# Función para crear servidores con traductor
def crear_servidor_con_traductor(config_name: str):
    """Crea un servidor con traductor integrado"""
    configs = {
        "server1": {
            "server_id": "SERVER1",
            "host": "127.0.0.3",
            "port": 5002,
            "dns_local_ip": "127.0.0.2",
            "dns_local_port": 50000,
            "folder_path": "archivos_server1"
        },
        "server2": {
            "server_id": "SERVER2", 
            "host": "127.0.0.4",
            "port": 5003,
            "dns_local_ip": "127.0.0.12",
            "dns_local_port": 50000,
            "folder_path": "archivos_server2"
        },
        "server3": {
            "server_id": "SERVER3",
            "host": "127.0.0.6", 
            "port": 5004,
            "dns_local_ip": "127.0.0.7",
            "dns_local_port": 50001,
            "folder_path": "archivos_server3"
        }
    }
    
    if config_name not in configs:
        print(f"Configuración '{config_name}' no encontrada. Disponibles: {list(configs.keys())}")
        return None
    
    config = configs[config_name]
    return ServidorConTraductor(**config)

if __name__ == "__main__":
    print("=== Servidor Distribuido con Traductor ===")
    print("DNS General integrado para comunicación entre servidores")
    print("Traductor automático para diferentes tipos de DNS")
    print("Ctrl+C para detener\n")
    
    if len(sys.argv) != 2:
        print("Uso: python server_with_translator.py <server1|server2|server3>")
        print("Ejemplo: python server_with_translator.py server1")
        sys.exit(1)
    
    config_name = sys.argv[1]
    server = crear_servidor_con_traductor(config_name)
    
    if server:
        server.start()
    else:
        sys.exit(1)