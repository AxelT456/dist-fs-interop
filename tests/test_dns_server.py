# /tests/test_dns_server.py

import sys
import os
import json
import socket

# Añade la carpeta src al path si es necesario
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.dns_translator.translator import DNSTranslator

def basic_driver():
    """Un driver simple para el DNS de prueba."""
    return {
        "encode": lambda req: {"query": req["name"]},
        "decode": lambda resp: resp["ip"]
    }

class DNSServer:
    """
    Un servidor DNS simple que escucha en un puerto y responde a las consultas.
    """
    def __init__(self, host="127.0.0.1", port=8053):
        self.host = host
        self.port = port
        self.dns = DNSTranslator()
        self.dns.registrar_driver(1, basic_driver())
        # Base de datos del DNS: qué dirección devolver para cada nombre de servidor
        self.records = {
            "server-A": {"ip": "127.0.0.1", "port": 8080},
            "server-B": {"ip": "127.0.0.1", "port": 8081}
        }
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        print(f"✅ Servidor DNS escuchando en {self.host}:{self.port}")

    def serve(self):
        """Bucle infinito para atender peticiones."""
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
                req = json.loads(data.decode("utf-8"))
                print(f"<- [DNS] Consulta recibida de {addr}: {req}")
                
                name = req.get("query")
                # Devuelve el registro o una dirección nula si no se encuentra
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