# /tests/test_server.py

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network.transport import ReliableTransport
from src.network.security import SecureSession # Importamos la capa de seguridad

HOST = "0.0.0.0"
PORT = 8080

def run_test_server():
    transport = ReliableTransport(HOST, PORT)
    print(f"Servidor de prueba escuchando en {HOST}:{PORT}...")

    while True: # Bucle para poder reiniciar la prueba sin reiniciar el script
        print("\nEsperando una conexión de cliente...")
        encrypted_payload, client_addr = transport.listen()
        print(f"Paquete de datos recibido de {client_addr}")

        # --- NUEVO PASO: DESCIFRAR EL PAYLOAD ---
        # 1. Crear la sesión de seguridad con las mismas claves mágicas
        session = SecureSession()
        mock_shared_secret = 123456789
        mock_server_nonce = b'server_nonce'
        session.derive_keys(mock_shared_secret, mock_server_nonce)

        # 2. Descifrar el payload
        try:
            decrypted_payload = session.decrypt(encrypted_payload)
            
            # 3. Mostrar el resultado
            print(f"\nÉxito! Payload descifrado correctamente.")
            print(f"   Contenido: {decrypted_payload.decode('utf-8')}")
            print(f"   Desde: {client_addr}")

        except Exception as e:
            print(f"Error al descifrar el payload: {e}")

if __name__ == "__main__":
    run_test_server()