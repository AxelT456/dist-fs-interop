import os
import json
import threading
import time
import socket
from datetime import datetime

CONFIG_FILE = "config_marco.json"
LOG_FILE = "server.log"

# --- CONFIGURACIÓN DE RED ---
# 1. IP y Puerto donde este DNS escuchará las peticiones.
DNS_IP = "127.0.0.20"
DNS_PORT = 50000

# 2. IP y Puerto del servidor de archivos que se anunciará en las respuestas.
SERVER_IP = "127.0.0.8"
SERVER_PORT = 5005


class FileEntry:
    def __init__(self, name, extension, ttl):
        self.name = name
        self.extension = extension
        self.ttl = ttl
        self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "name": self.name,
            "extension": self.extension,
            "ttl": self.ttl,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_valid(self):
        """Comprueba si el TTL del archivo no ha expirado."""
        elapsed = (datetime.now() - self.timestamp).total_seconds()
        return elapsed <= self.ttl


class FileManager:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.files = {}  # clave: filename.ext, valor: FileEntry
        self.lock = threading.Lock()
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    for entry in data:
                        fe = FileEntry(entry["name"], entry["extension"], entry["ttl"])
                        fe.timestamp = datetime.fromisoformat(entry["timestamp"])
                        self.files[f"{fe.name}.{fe.extension}"] = fe
            except (json.JSONDecodeError, KeyError):
                print("Error al leer config.json, se creará uno nuevo.")

    def save_config(self):
        with self.lock:
            data = [fe.to_dict() for fe in self.files.values()]
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=4)

    def log(self, message):
        with open(LOG_FILE, "a") as log:
            log.write(f"[{datetime.now().isoformat()}] {message}\n")

    def scan_folder(self):
        """Escanea la carpeta y actualiza la lista de archivos."""
        try:
            current_files_on_disk = set(os.listdir(self.folder_path))
        except FileNotFoundError:
            print(f"ERROR: La carpeta '{self.folder_path}' no existe. El monitor no puede continuar.")
            return

        with self.lock:
            for fname in current_files_on_disk:
                if fname not in self.files:
                    name, ext = os.path.splitext(fname)
                    ext = ext.lstrip(".")
                    publish = input(f"-> Archivo nuevo '{fname}'. ¿Desea publicarlo? (s/n): ").lower()
                    if publish == "s":
                        while True:
                            try:
                                ttl_str = input(f"   Ingrese el TTL en segundos para '{fname}': ")
                                ttl = int(ttl_str)
                                if ttl > 0:
                                    break
                                print("   El TTL debe ser un número positivo.")
                            except ValueError:
                                print("   Por favor, ingrese un número entero válido.")
                        
                        fe = FileEntry(name, ext, ttl)
                        self.files[fname] = fe
                        self.log(f"ARCHIVO AGREGADO: {fname} con TTL={ttl}")

            known_files = set(self.files.keys())
            deleted_files = known_files - current_files_on_disk
            for fname in deleted_files:
                self.log(f"ARCHIVO ELIMINADO: {fname} fue removido de la carpeta.")
                del self.files[fname]

        self.save_config()

    def monitor(self):
        """Hilo que escanea la carpeta periódicamente."""
        while True:
            print("\nIniciando escaneo periódico de la carpeta...")
            self.scan_folder()
            print("Escaneo finalizado. Esperando 30 segundos...")
            time.sleep(30)

    def get_available_file(self, name, ext):
        """Busca un archivo específico y comprueba si está disponible (TTL válido)."""
        fname = f"{name}.{ext}"
        with self.lock:
            if fname in self.files:
                file_entry = self.files[fname]
                if file_entry.is_valid():
                    return file_entry
        return None

    def get_all_available_files(self):
        """Devuelve una lista de todos los archivos cuyo TTL es válido."""
        available = []
        with self.lock:
            for file_entry in self.files.values():
                if file_entry.is_valid():
                    available.append(file_entry)
        return available


class UDPServer(threading.Thread):
    def __init__(self, file_manager, server_ip, server_port):
        super().__init__(daemon=True)
        self.file_manager = file_manager
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # CAMBIO: Usar las constantes DNS para el bind
        self.sock.bind((DNS_IP, DNS_PORT))

    def run(self):
        print(f"Servidor DNS escuchando en {DNS_IP}:{DNS_PORT}...")
        while True:
            data, addr = self.sock.recvfrom(1024)
            response = {}
            try:
                request = json.loads(data.decode())
                action = request.get("accion")
                
                print(f"Petición recibida de {addr}: {request}")

                if action == "consultar":
                    name = request.get("name")
                    ext = request.get("extension")
                    file_entry = self.file_manager.get_available_file(name, ext)
                    
                    if file_entry:
                        response = {
                            "status": "ACK",
                            "ip": self.server_ip,
                            "port": self.server_port,
                            "ttl": file_entry.ttl
                        }
                    else:
                        response = {"status": "NACK", "error": "Archivo no encontrado o TTL expirado"}

                elif action == "listar_archivos":
                    files = self.file_manager.get_all_available_files()
                    response = {
                        "status": "ACK",
                        "ip": self.server_ip,
                        "port": self.server_port,
                        "files": [f.to_dict() for f in files]
                    }
                else:
                    response = {"status": "ERROR", "message": "Acción no reconocida"}

            except Exception as e:
                response = {"status": "ERROR", "message": str(e)}
            
            self.sock.sendto(json.dumps(response).encode(), addr)


class Server:
    def __init__(self, folder_path, server_ip, server_port):
        self.file_manager = FileManager(folder_path)
        self.server_ip = server_ip
        self.server_port = server_port

    def start(self):
        print("--- Servidor de Nombres de Archivos ---")
        self.file_manager.scan_folder()

        threading.Thread(target=self.file_manager.monitor, name="MonitorCarpeta", daemon=True).start()

        udp_server = UDPServer(self.file_manager, self.server_ip, self.server_port)
        udp_server.start()

        print(f"\nServidor iniciado. Anunciando IP del servidor de archivos: {self.server_ip}:{self.server_port}")
        print("Presione Ctrl+C para salir.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nCerrando servidor...")


if __name__ == "__main__":
    carpeta_a_monitorear = "archivos_server_marco"
    
    server = Server(carpeta_a_monitorear, SERVER_IP, SERVER_PORT)
    server.start()