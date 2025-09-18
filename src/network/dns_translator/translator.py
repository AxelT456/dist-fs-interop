# /src/network/dns_translator/translator.py
import logging
import socket

class DNSTranslator:
    def __init__(self):
        self.dns_drivers = {}  # id_dns -> driver_func

    def registrar_driver(self, id_dns: int, driver_func):
        self.dns_drivers[id_dns] = driver_func
        logging.info(f"Driver para DNS-{id_dns} registrado.")
    
    def registrar_drivers(self, drivers_list: list[dict]):
        for entry in drivers_list:
            self.dns_drivers[entry["id"]] = entry["driver"]
        logging.info(f"Drivers registrados: {[entry['id'] for entry in drivers_list]}")

    def traducir(self, json_cliente: dict, dns_config: dict) -> str:
        """
        json_cliente: petición del cliente
        dns_config: {"id": 1, "ip": "192.168.0.10", "driver": driver_dns_basico}
        
        Devuelve la IP traducida (ej. "192.168.0.55")
        """
        id_dns = dns_config["id"]
        if id_dns not in self.dns_drivers:
            raise ValueError(f"No existe un driver registrado para el DNS {id_dns}")
        
        driver_func = self.dns_drivers[id_dns]

        # 1. Convertir consulta al formato del DNS
        consulta = driver_func["encode"](json_cliente)

        # 2. Enviar la consulta al DNS remoto (simulación UDP por ejemplo)
        ip_dns = dns_config["ip"]
        respuesta_raw = self._enviar_consulta(ip_dns, consulta)

        # 3. Interpretar la respuesta usando el driver
        ip_resultado = driver_func["decode"](respuesta_raw)

        return ip_resultado

    def _enviar_consulta(self, ip: str, consulta: dict) -> dict:
        """
        Simula el envío de una consulta a un servidor DNS real.
        Aquí puedes usar socket UDP/TCP, o incluso HTTP si ese DNS lo requiere.
        """
        logging.info(f"Enviando consulta a {ip}: {consulta}")
        
        # DEMO: devolver respuesta fija
        return {"status": "ok", "ip": "192.168.0.55"}


# DNS básico
driver_dns_basico = {
    "encode": lambda json_cliente: {
        "accion": "consultar",
        "nombre_archivo": json_cliente.get("archivo")
    },
    "decode": lambda resp: resp.get("ip")  # extraer IP del DNS
}

# DNS v2
driver_dns_v2 = {
    "encode": lambda json_cliente: {
        "type": "lookup",
        "file": json_cliente.get("archivo"),
        "options": {"recursive": False}
    },
    "decode": lambda resp: resp.get("ip")
}

'''
FLUJO ESPERADO

dns_servers = [
    {"id": 1, "ip": "192.168.0.10", "driver": driver_dns_basico},
    {"id": 2, "ip": "192.168.0.11", "driver": driver_dns_v2},
    {"id": 3, "ip": "192.168.0.12", "driver": driver_dns_basico},
]

traductor = DNSTranslator()
traductor.registrar_drivers(dns_servers)

# Cliente pide archivo
json_cliente = {"accion": "consultar", "archivo": "reporte.pdf"}

# Preguntamos al DNS-2
ip_resultado = traductor.traducir(json_cliente, dns_servers[1])
print(f"IP obtenida desde DNS-2: {ip_resultado}")

# Ahora PeerConnector se encarga de conectarse a esa IP

'''