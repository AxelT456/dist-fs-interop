# /tests/test_client.py

import socket
import json
import random
import sys
import os

# Añade la carpeta raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ahora importamos la capa de seguridad
from src.network.security import SecureSession

# ... (el resto de la configuración no cambia) ...
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
SADDR = (SERVER_HOST, SERVER_PORT)

def jsend(sock, msg, addr):
    sock.sendto((json.dumps(msg) + "\n").encode("utf-8"), addr)

def run_test_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)

    try:
        # Los pasos 1, 2 y 3 (handshake) son iguales
        cid = random.randint(1000, 9999)
        syn = {"type": "SYN", "seq": cid}
        jsend(sock, syn, SADDR)
            print("SYN enviado...")

        data, _ = sock.recvfrom(65535)
        msg = json.loads(data.decode("utf-8").splitlines()[0])
        
        if msg.get("type") == "SYN-ACK":
            sid = msg['seq']
            print("SYN-ACK recibido.")
            ack = {"type": "ACK", "ack": sid + 1, "cid": cid, "sid": sid}
            jsend(sock, ack, SADDR)
            print("ACK final enviado. Conexión establecida.")

            # --- NUEVO PASO: CIFRAR EL PAYLOAD ---
            # 4. Crear una sesión de seguridad
            session = SecureSession()
            # Para esta prueba, simularemos que el handshake TLS ya ocurrió
            # y que ambas partes mágicamente tienen las mismas claves.
            mock_shared_secret = 123456789
            mock_server_nonce = b'server_nonce'
            session.derive_keys(mock_shared_secret, mock_server_nonce)

            # 5. Cifrar el mensaje
            plaintext_payload = b"hola mundo seguro y cifrado!"
            encrypted_record = session.encrypt(plaintext_payload)
            print(f"Payload cifrado: {encrypted_record}")

            # 6. Enviar el payload cifrado
            data_packet = {
                "type": "DATA",
                "seq": sid + 1,
                "payload": encrypted_record # Enviamos el diccionario cifrado
            }
            jsend(sock, data_packet, SADDR)
            print("Paquete de datos cifrado enviado.")
            print("\nPrueba del cliente finalizada con éxito.")
        else:
            print("Error: No se recibió SYN-ACK.")
    except socket.timeout:
        print("Error: Timeout esperando respuesta del servidor.")
    finally:
        sock.close()

if __name__ == "__main__":
    run_test_client()