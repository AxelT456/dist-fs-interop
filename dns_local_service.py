import os
import json
import threading
import time
import socket
import logging
import sys
import argparse

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class DNSLocalServer:
    def __init__(self, server_id, config_file='network_config.json'):
        self.server_id = server_id
        self.lista_archivos = []
        self.lista_archivos_lock = threading.Lock()
        
        # Cargar configuración de red
        with open(config_file, 'r') as f:
            self.net_config = json.load(f)
            
        if server_id not in self.net_config['peers']:
            raise ValueError(f"ID de servidor '{server_id}' no encontrado en configuración.")
            
        self.peer_config = self.net_config['peers'][server_id]
        
        self.udp_ip = "0.0.0.0"
        self.udp_port = self.peer_config['dns_port']
        self.server_ip = self.peer_config['server_ip'] or "127.0.0.1"
        self.server_port = self.peer_config['server_port']
        
        # Carpeta a monitorear
        self.folder_path = f"archivos_{server_id.lower()}"
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

        # Archivo de persistencia local (ej. config_SERVER1.json)
        self.local_config_file = f"config_{server_id}.json"
        self.load_local_persistence()

    def load_local_persistence(self):
        if os.path.exists(self.local_config_file):
            try:
                with open(self.local_config_file, 'r') as f:
                    data = json.load(f)
                    self.lista_archivos = data.get('files', [])
            except Exception as e:
                logging.error(f"Error cargando persistencia: {e}")

    def save_local_persistence(self):
        with self.lista_archivos_lock:
            try:
                with open(self.local_config_file, 'w') as f:
                    json.dump({'files': self.lista_archivos}, f, indent=4)
            except Exception as e:
                logging.error(f"Error guardando persistencia: {e}")

    def scan_and_update(self):
        """Escanea la carpeta y actualiza la lista de archivos."""
        try:
            files_on_disk = {f for f in os.listdir(self.folder_path) 
                           if os.path.isfile(os.path.join(self.folder_path, f))}
        except FileNotFoundError:
            return

        with self.lista_archivos_lock:
            known_files = {f['nombre_archivo'] for f in self.lista_archivos}
            
            # Nuevos
            new_files = files_on_disk - known_files
            for f in new_files:
                # Por defecto auto-publicamos para simplificar la ejecución desatendida
                self.lista_archivos.append({
                    "nombre_archivo": f,
                    "extension": os.path.splitext(f)[1],
                    "publicado": True,
                    "ttl": 3600
                })
                logging.info(f"Nuevo archivo detectado y publicado: {f}")
            
            # Eliminados
            deleted_files = known_files - files_on_disk
            if deleted_files:
                self.lista_archivos = [f for f in self.lista_archivos 
                                     if f['nombre_archivo'] not in files_on_disk]
                logging.info(f"Archivos eliminados: {deleted_files}")
                
            if new_files or deleted_files:
                self.save_local_persistence()

    def udp_listener(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.udp_ip, self.udp_port))
        logging.info(f"DNS Local ({self.server_id}) escuchando en puerto {self.udp_port}")

        while True:
            try:
                data, addr = sock.recvfrom(4096)
                req = json.loads(data.decode('utf-8'))
                
                resp = {"status": "ERROR", "mensaje": "Accion no soportada"}
                
                if req.get('accion') == 'listar_archivos':
                    with self.lista_archivos_lock:
                        resp = {
                            "status": "ACK",
                            "archivos": self.lista_archivos,
                            "ip": self.server_ip,
                            "puerto": self.server_port
                        }
                
                sock.sendto(json.dumps(resp, default=str).encode('utf-8'), addr)
                
            except Exception as e:
                logging.error(f"Error UDP: {e}")

    def start(self):
        # Hilo de escaneo periódico
        def updater_loop():
            while True:
                self.scan_and_update()
                time.sleep(10) # Escaneo cada 10s
        
        t_updater = threading.Thread(target=updater_loop, daemon=True)
        t_updater.start()
        
        # Listener UDP (Bloqueante)
        self.udp_listener()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("server_id", help="ID del servidor en network_config.json (ej. SERVER1)")
    args = parser.parse_args()
    
    server = DNSLocalServer(args.server_id)
    server.start()