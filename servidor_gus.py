import os
import json
import threading
import time
import socket
from datetime import datetime

# --- VALORES AJUSTADOS ---
# 1. El DNS ahora se inicializa y escucha en esta IP.
DNS_IP = "127.0.0.21"
DNS_PORT = 50000

# 2. La IP y Puerto que el DNS enviará en sus respuestas.
SERVER_IP = "127.0.0.10"
SERVER_PORT = 5007

# --- OTROS VALORES DE CONFIGURACIÓN ---
CONFIG_FILE = "file_permissions_config_gus.json"
LOG_FILE = "file_server.log"
UPDATE_INTERVAL = 300  # 5 minutos

lock = threading.Lock()

class FileEntry:
    def __init__(self, name, extension, ttl, can_publish):
        self.name = name
        self.extension = extension
        self.ttl = ttl
        self.can_publish = can_publish
    
    def to_dict(self):
        return {
            "name": self.name,
            "extension": self.extension,
            "ttl": self.ttl,
            "can_publish": self.can_publish
        }
    
    @staticmethod
    def from_dict(d):
        return FileEntry(d["name"], d["extension"], d["ttl"], d["can_publish"])

class FileServer:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.file_list = {}  # clave: name.ext -> FileEntry
        self.running = True
        self.load_config()
    
    def log(self, message):
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] {message}\n")
        print(message)
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                with lock:
                    self.file_list = {
                        key: FileEntry.from_dict(value)
                        for key, value in data.items()
                    }
                self.log(f"Configuración cargada desde {CONFIG_FILE}")
            except Exception as e:
                self.log(f"Error al cargar configuración: {e}")
                self.file_list = {}
        else:
            self.file_list = {}
            self.log("No existe archivo de configuración. Se creará uno nuevo.")
    
    def save_config(self):
        with lock:
            data = {key: fe.to_dict() for key, fe in self.file_list.items()}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=4)
        self.log(f"Configuración guardada en {CONFIG_FILE}")
    
    def scan_folder(self):
        files = set()
        try:
            for f in os.listdir(self.folder_path):
                full_path = os.path.join(self.folder_path, f)
                if os.path.isfile(full_path):
                    name, ext = os.path.splitext(f)
                    ext = ext.lstrip(".")
                    key = f"{name}.{ext}"
                    files.add(key)
        except Exception as e:
            self.log(f"Error al leer carpeta: {e}")
        return files
    
    def ask_user_for_file(self, filename, extension):
        while True:
            resp = input(f"¿El archivo '{filename}.{extension}' puede publicarse? (s/n): ").strip().lower()
            if resp in ("s", "n"):
                can_publish = resp == "s"
                break
            print("Por favor ingresa 's' o 'n'")
        while True:
            try:
                ttl = int(input(f"Indica TTL (segundos) para '{filename}.{extension}': ").strip())
                if ttl > 0:
                    break
                else:
                    print("TTL debe ser un número positivo")
            except:
                print("TTL debe ser un número entero")
        return can_publish, ttl
    
    def update_files(self):
        current_files = self.scan_folder()
        with lock:
            known_files = set(self.file_list.keys())

            new_files = current_files - known_files
            for f in new_files:
                name, ext = f.rsplit(".", 1)
                self.log(f"Nuevo archivo detectado: {f}")
                can_publish, ttl = self.ask_user_for_file(name, ext)
                self.file_list[f] = FileEntry(name, ext, ttl, can_publish)
                self.log(f"Archivo '{f}' agregado con permiso {can_publish} y TTL {ttl}")
            
            removed_files = known_files - current_files
            for f in removed_files:
                self.log(f"Archivo eliminado detectado: {f}")
                del self.file_list[f]
                self.log(f"Archivo '{f}' removido de la lista")
        
        self.save_config()
    
    def update_loop(self):
        while self.running:
            try:
                self.update_files()
            except Exception as e:
                self.log(f"Error en actualización: {e}")
            time.sleep(UPDATE_INTERVAL)
    
    def udp_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # CORRECCIÓN: Usar la IP y Puerto del DNS para inicializar
        sock.bind((DNS_IP, DNS_PORT))
        self.log(f"Servidor DNS iniciado y escuchando en {DNS_IP}:{DNS_PORT}")
        
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                msg = data.decode("utf-8")
                try:
                    req = json.loads(msg)

                    if req.get("action") == "get_server_info":
                        resp = {
                            "status": "ACK",
                            "ip": SERVER_IP,
                            "port": SERVER_PORT
                        }
                    elif req.get("action") == "list_all_files":
                        with lock:
                            all_files = [fe.to_dict() for fe in self.file_list.values()]
                        resp = {
                            "status": "ACK",
                            "files": all_files
                        }
                    elif req.get("type") == "check":
                        filename = req.get("filename")
                        extension = req.get("extension")
                        if not filename or not extension:
                            resp = {"response": "NACK", "reason": "Faltan 'filename' o 'extension'"}
                        else:
                            key = f"{filename}.{extension}"
                            with lock:
                                fe = self.file_list.get(key)
                            if fe and fe.can_publish:
                                resp = {"response": "ACK",
                                        "ip": SERVER_IP,
                                        "port": SERVER_PORT}
                            else:
                                resp = {"response": "NACK",
                                        "ip": SERVER_IP,
                                        "port": SERVER_PORT}
                    
                    else:
                        resp = {"response": "NACK", "reason": "Solicitud no válida"}
                        
                except json.JSONDecodeError:
                    resp = {"response": "NACK", "reason": "JSON inválido"}
                    
                resp_bytes = json.dumps(resp).encode("utf-8")
                sock.sendto(resp_bytes, addr)
                
            except Exception as e:
                self.log(f"Error en servidor UDP: {e}")
    
    def start(self):
        self.log("Iniciando servidor de nombres de recursos de archivo.")
        self.log(f"Este DNS anunciará la IP del servidor de archivos: {SERVER_IP}:{SERVER_PORT}")
        self.update_files()
        
        thread_update = threading.Thread(target=self.update_loop, daemon=True)
        thread_udp = threading.Thread(target=self.udp_server, daemon=True)
        
        thread_update.start()
        thread_udp.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log("Terminando proceso...")
            self.running = False
            thread_update.join()
            thread_udp.join()


if __name__ == "__main__":
    folder = input("Introduce la ruta absoluta de la carpeta a monitorear: ").strip()
    if not os.path.isdir(folder):
        print("La carpeta no existe o no es válida.")
        exit(1)
    server = FileServer(folder)
    server.start()