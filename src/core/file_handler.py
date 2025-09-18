# /src/core/file_handler.py
import json
import time
import base64
from typing import Dict, List, Optional, Tuple

class FileHandler:
    """
    Gestiona las operaciones de archivos en el sistema distribuido.
    Implementa la política de concurrencia y transferencia de archivos.
    """
    
    def __init__(self, server_id: str):
        self.server_id = server_id
        self.local_files = {}  # Archivos almacenados localmente
        self.temp_files = {}   # Archivos temporales durante transferencias
        
    def add_local_file(self, filename: str, content: str):
        """
        Almacena o actualiza un archivo en el sistema local.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.local_files[filename] = {
            "content": content,
            "timestamp": timestamp,
            "server_id": self.server_id
        }
        print(f"[FileHandler] Archivo local actualizado: {filename}")
    
    def get_local_file(self, filename: str) -> Optional[Dict]:
        """
        Recupera un archivo del almacenamiento local.
        """
        return self.local_files.get(filename)
    
    def remove_local_file(self, filename: str) -> bool:
        """
        Elimina un archivo del almacenamiento local.
        """
        if filename in self.local_files:
            del self.local_files[filename]
            print(f"[FileHandler] Archivo local removido: {filename}")
            return True
        return False
    
    def get_file_copy_request_message(self, filename: str) -> Dict:
        """
        Genera el mensaje de solicitud de copia de archivo.
        """
        return {
            "type": "GET_FILE_COPY",
            "fileName": filename,
            "requestingServer": self.server_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def process_file_copy_request(self, message: Dict) -> Optional[Dict]:
        """
        Procesa una solicitud de copia de archivo.
        Genera respuesta con el contenido del archivo si está disponible.
        """
        try:
            if message.get("type") != "GET_FILE_COPY":
                return None
            
            filename = message.get("fileName")
            requesting_server = message.get("requestingServer", "unknown")
            
            if not filename:
                return None
            
            # Buscar el archivo localmente
            local_file = self.get_local_file(filename)
            if not local_file:
                print(f"[FileHandler] Archivo no encontrado: {filename}")
                return None
            
            # Codificar contenido en base64 para envío
            content_b64 = base64.b64encode(local_file["content"].encode('utf-8')).decode('utf-8')
            
            response = {
                "type": "FILE_COPY_RESPONSE",
                "fileName": filename,
                "content": content_b64,
                "timestamp": local_file["timestamp"],
                "serverId": self.server_id
            }
            
            print(f"[FileHandler] Enviando copia de {filename} a {requesting_server}")
            return response
            
        except Exception as e:
            print(f"[FileHandler] Error procesando solicitud de copia: {e}")
            return None
    
    def process_file_copy_response(self, message: Dict) -> bool:
        """
        Procesa la respuesta que contiene una copia de archivo.
        """
        try:
            if message.get("type") != "FILE_COPY_RESPONSE":
                return False
            
            filename = message.get("fileName")
            content_b64 = message.get("content")
            timestamp = message.get("timestamp")
            server_id = message.get("serverId", "unknown")
            
            if not filename or not content_b64:
                return False
            
            # Decodificar contenido desde base64
            content = base64.b64decode(content_b64).decode('utf-8')
            
            # Guardar como archivo temporal
            self.temp_files[filename] = {
                "content": content,
                "timestamp": timestamp,
                "source_server": server_id
            }
            
            print(f"[FileHandler] Copia recibida: {filename} desde {server_id}")
            return True
            
        except Exception as e:
            print(f"[FileHandler] Error procesando respuesta de copia: {e}")
            return False
    
    def get_update_file_message(self, filename: str, content: str) -> Dict:
        """
        Genera el mensaje de actualización de archivo.
        """
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "type": "UPDATE_FILE",
            "fileName": filename,
            "content": content_b64,
            "timestamp": timestamp,
            "updatingServer": self.server_id
        }
    
    def process_update_file_request(self, message: Dict) -> Dict:
        """
        Procesa una solicitud de actualización de archivo.
        Aplica la política de concurrencia "Last Write Wins".
        """
        try:
            if message.get("type") != "UPDATE_FILE":
                return {"type": "UPDATE_CONFIRMATION", "status": "ERROR", "reason": "Invalid message type"}
            
            filename = message.get("fileName")
            content_b64 = message.get("content")
            new_timestamp = message.get("timestamp")
            updating_server = message.get("updatingServer", "unknown")
            
            if not filename or not content_b64 or not new_timestamp:
                return {"type": "UPDATE_CONFIRMATION", "status": "ERROR", "reason": "Missing required fields"}
            
            # Decodificar contenido
            content = base64.b64decode(content_b64).decode('utf-8')
            
            # Verificar si el archivo existe localmente
            local_file = self.get_local_file(filename)
            
            if local_file:
                # Comparar timestamps para "Last Write Wins"
                local_timestamp = local_file["timestamp"]
                if new_timestamp <= local_timestamp:
                    print(f"[FileHandler] Actualización rechazada: timestamp más antiguo para {filename}")
                    return {
                        "type": "UPDATE_CONFIRMATION",
                        "fileName": filename,
                        "status": "REJECTED",
                        "reason": "Older timestamp"
                    }
            
            # Aplicar la actualización
            self.add_local_file(filename, content)
            
            print(f"[FileHandler] Archivo actualizado: {filename} desde {updating_server}")
            return {
                "type": "UPDATE_CONFIRMATION",
                "fileName": filename,
                "status": "OK",
                "timestamp": new_timestamp
            }
            
        except Exception as e:
            print(f"[FileHandler] Error procesando actualización: {e}")
            return {"type": "UPDATE_CONFIRMATION", "status": "ERROR", "reason": str(e)}
    
    def commit_temp_file(self, filename: str) -> bool:
        """
        Confirma un archivo temporal como archivo local permanente.
        """
        if filename not in self.temp_files:
            return False
        
        temp_file = self.temp_files[filename]
        self.add_local_file(filename, temp_file["content"])
        del self.temp_files[filename]
        
        print(f"[FileHandler] Archivo temporal confirmado: {filename}")
        return True
    
    def discard_temp_file(self, filename: str) -> bool:
        """
        Elimina un archivo temporal sin confirmarlo.
        """
        if filename in self.temp_files:
            del self.temp_files[filename]
            print(f"[FileHandler] Archivo temporal descartado: {filename}")
            return True
        return False
    
    def get_local_files_list(self) -> List[str]:
        """
        Obtiene la lista de archivos almacenados localmente.
        """
        return list(self.local_files.keys())
    
    def get_temp_files_list(self) -> List[str]:
        """
        Obtiene la lista de archivos temporales pendientes.
        """
        return list(self.temp_files.keys())
    
    def get_file_status(self) -> Dict:
        """
        Obtiene el estado actual de los archivos para monitoreo.
        """
        return {
            "server_id": self.server_id,
            "local_files_count": len(self.local_files),
            "temp_files_count": len(self.temp_files),
            "local_files": list(self.local_files.keys()),
            "temp_files": list(self.temp_files.keys())
        }
    
    def print_file_summary(self):
        """
        Muestra un resumen del estado actual de los archivos.
        """
        print("\n" + "="*50)
        print("RESUMEN DE ARCHIVOS")
        print("="*50)
        print(f"Servidor: {self.server_id}")
        print(f"Archivos locales: {len(self.local_files)}")
        print(f"Archivos temporales: {len(self.temp_files)}")
        
        if self.local_files:
            print(f"\nArchivos locales:")
            for filename, file_info in self.local_files.items():
                print(f"  - {filename} (modificado: {file_info['timestamp']})")
        
        if self.temp_files:
            print(f"\nArchivos temporales:")
            for filename, file_info in self.temp_files.items():
                print(f"  - {filename} (desde: {file_info['source_server']})")
        
        print("="*50)
