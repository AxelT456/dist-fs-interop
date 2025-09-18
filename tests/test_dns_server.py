# /tests/test_dns_server.py (Versión Corregida)

import sys
import os
import json
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.dns_translator.translator import DNSTranslator

class DNSServer:
    """
    Un servidor DNS de prueba que escucha en un puerto y responde a las consultas.
    """
    def __init__(self, host="127.0.0.1", port=8053):
        self.host = host
        self.port = port
        
        # --- ¡CAMBIO CLAVE AQUÍ! ---
        # Creamos una configuración simulada para pasarle al DNSTranslator.
        # Aunque este servidor DNS no necesita la configuración para sí mismo,
        # la clase DNSTranslator ahora la requiere para ser instanciada.
        mock_config = {
            "dns_servers": [{
                "id": "dns_de_prueba",
                "host": "127.0.0.1",
                "port": 8053,
                "driver": "driver_prueba"
            }]
        }
        self.dns = DNSTranslator(mock_config)
        
        # Base de datos del DNS: qué dirección devolver para cada nombre de servidor
        self.records = {
            "server-A": {"ip": "127.0.0.1", "port": 8080},
            "server-B": {"ip": "127.0.0.1", "port": 8081},
            "server-C": {"ip": "127.0.0.1", "port": 8082},
            "server-D": {"ip": "127.0.0.1", "port": 8083},
            "server-E": {"ip": "127.0.0.1", "port": 8084}
        }
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        print(f"✅ Servidor DNS de prueba escuchando en {self.host}:{self.port}")

    def serve(self):
        """Bucle infinito para atender peticiones."""
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                req = json.loads(data.decode("utf-8"))
                print(f"<- [DNS] Consulta recibida de {addr}: {req}")
                
                # Asumimos que la consulta es para el "nombre del servidor"
                # basado en los drivers que definimos.
                name = req.get("nombre_servidor") or req.get("server")
                
                record = self.records.get(name, {"ip": "0.0.0.0", "port": 0})
                
                resp = json.dumps(record).encode("utf-8")
                self.sock.sendto(resp, addr)
                print(f"-> [DNS] Respuesta enviada: {record}")

            except KeyboardInterrupt:
                print("\n🛑 Servidor DNS detenido.")
                break
            except Exception as e:
                print(f"❌ [DNS] Error procesando consulta: {e}")

if __name__ == "__main__":
    server = DNSServer()
    server.serve()