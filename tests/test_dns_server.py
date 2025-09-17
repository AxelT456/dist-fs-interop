# /tests/test_dns_server.py

import sys
import os
import json
import socket

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.dns_translator.translator import DNSTranslator

def basic_driver():
    return {
        "encode": lambda req: {"query": req["name"]},
        "decode": lambda resp: resp["ip"]
    }

class DNSServer:
    def __init__(self, host="127.0.0.1", port=8053):
        self.host = host
        self.port = port
        self.dns = DNSTranslator()
        self.dns.registrar_driver(1, basic_driver())
        # Ahora cada registro tiene IP y puerto
        self.records = {
            "servidor1": {"ip": "127.0.0.1", "port": 8080},
            "servidor2": {"ip": "127.0.0.1", "port": 8081}
        }
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        print(f"DNS Server escuchando en {self.host}:{self.port}")

    def serve(self):
        while True:
            data, addr = self.sock.recvfrom(4096)
            try:
                req = json.loads(data.decode("utf-8"))
                print(f"Consulta recibida de {addr}: {req}")
                name = req.get("query")
                record = self.records.get(name, {"ip": "0.0.0.0", "port": 0})
                resp = json.dumps(record).encode("utf-8")
                self.sock.sendto(resp, addr)
                print(f"Respuesta enviada: {record}")
            except Exception as e:
                print(f"Error procesando consulta: {e}")
            except KeyboardInterrupt:
                print("Servidor DNS detenido.")
                break
if __name__ == "__main__":
    server = DNSServer()
    server.serve()
