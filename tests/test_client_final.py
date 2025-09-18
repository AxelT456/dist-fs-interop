# /tests/test_client_final.py

import socket
import json
import random
import sys
import os
import time

# Añade la carpeta raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.security import SecureSession

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080 # Asegúrate que coincida con tu config.json
SADDR = (SERVER_HOST, SERVER_PORT)

def jsend(sock, msg, addr):
    sock.sendto((json.dumps(msg) + "\n").encode("utf-8"), addr)

def run_final_client_test():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5.0)

    try:
        # --- El handshake de transporte es el mismo ---
        cid = random.randint(1000, 9999)
        syn = {"type": "SYN", "seq": cid}
        jsend(sock, syn, SADDR)
        print("-> SYN enviado...")

        data, _ = sock.recvfrom(65535)
        msg = json.loads(data.decode("utf-8").splitlines()[0])
        
        if msg.get("type") == "SYN-ACK":
            sid = msg['seq']
            print("<- SYN-ACK recibido.")
            ack = {"type": "ACK", "ack": sid + 1, "cid": cid, "sid": sid}
            jsend(sock, ack, SADDR)
            print("-> Conexión de transporte establecida.")

            # --- PREPARAMOS LA SESIÓN SEGURA ---
            session = SecureSession()
            mock_shared_secret = 123456789
            mock_server_nonce = b'server_nonce'
            session.derive_keys(mock_shared_secret, mock_server_nonce)

            # --- ENVIAMOS UN MENSAJE DE APLICACIÓN REAL ---
            request_payload = {
                "type": "GET_FILE_COPY",
                # IMPORTANTE: Este archivo debe existir en el servidor para que la prueba funcione.
                # Por ahora, el servidor no tiene archivos locales. Vamos a pedir uno que no existe para probar el flujo.
                "fileName": "archivo_inexistente.txt",
                "requestingServer": "test-client"
            }
            print(f"-> Preparando para enviar solicitud: {request_payload['type']}")

            encrypted_request = session.encrypt(json.dumps(request_payload).encode('utf-8'))
            
            data_packet = {
                "type": "DATA",
                "seq": sid + 1,
                "payload": encrypted_request
            }
            jsend(sock, data_packet, SADDR)
            print("-> Solicitud de archivo cifrada enviada.")

            # --- BUCLE DE ESCUCHA MEJORADO ---
            print("\n   ... Esperando respuesta del servidor ...\n")
            
            while True: # Bucle para ignorar mensajes no deseados
                response_data, _ = sock.recvfrom(65535)
                response_msg = json.loads(response_data.decode("utf-8").splitlines()[0])

                if response_msg.get("type") == "DATA":
                    # ¡Esta es la respuesta que nos interesa!
                    encrypted_response = response_msg.get("payload")
                    decrypted_response = session.decrypt(encrypted_response)
                    print("✅ ¡Respuesta de la aplicación recibida y descifrada!")
                    print(json.loads(decrypted_response.decode('utf-8')))
                    break # Salimos del bucle
                elif response_msg.get("type") == "ACK":
                    # Ignoramos los ACKs de la capa de transporte
                    print("(ACK de transporte recibido, esperando datos de la aplicación...)")
                    continue
                else:
                    print(f"Respuesta inesperada recibida: {response_msg}")
                    break
        else:
            print("Error: No se recibió SYN-ACK.")
    except socket.timeout:
        print("❌ Error: Timeout esperando respuesta del servidor.")
    finally:
        sock.close()


if __name__ == "__main__":
    run_final_client_test()