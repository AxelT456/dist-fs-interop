# /src/network/peer_conector.py

import json
import secrets
from typing import Dict, Tuple, Optional, Callable

# --- Importaciones de tus Módulos ---
from .transport import ReliableTransport
from .security import SecureSession, dh_generate_private_key, dh_generate_public_key, dh_calculate_shared_secret
# from .dns_translator.translator import DNSTranslator # Descomenta si usas el traductor DNS

class PeerConnector:
    """
    Orquesta la comunicación con otros servidores (peers).
    Utiliza ReliableTransport para la conexión y SecureSession para el cifrado.
    Delega el procesamiento de mensajes de aplicación a través de un callback.
    """
    
    def __init__(self, transport_layer: ReliableTransport, server_id: str, on_message_callback: Callable):
        self.transport = transport_layer
        self.server_id = server_id
        self.sessions: Dict[Tuple[str, int], SecureSession] = {}
        # Almacena claves privadas temporales durante el handshake del lado cliente
        self.pending_handshakes: Dict[Tuple[str, int], int] = {}
        # Guarda la función que el MainServer le pasó para llamarla después
        self.on_message_callback = on_message_callback

    def connect_and_secure(self, peer_addr: Tuple[str, int]):
        """
        Inicia un handshake de seguridad con un peer.
        Esta función es para el lado que comienza la comunicación (cliente).
        """
        if peer_addr in self.sessions:
            print(f"[PeerConnector] Ya existe una sesión segura con {peer_addr}.")
            return

        try:
            print(f"[PeerConnector] Iniciando handshake de seguridad con {peer_addr}...")
            private_key = dh_generate_private_key()
            public_key = dh_generate_public_key(private_key)
            self.pending_handshakes[peer_addr] = private_key
            
            hello_msg = {
                "type": "HANDSHAKE_HELLO",
                "server_id": self.server_id,
                "public_key": public_key
            }
            # El envío ahora se hace a través de la capa de transporte
            self.transport.send_data(hello_msg, peer_addr)
        except Exception as e:
            print(f"❌ Error al iniciar el handshake: {e}")

    def handle_incoming_packet(self, payload: Dict, addr: Tuple[str, int]):
        """
        Punto de entrada principal para paquetes.
        Decide si es un handshake o un mensaje de aplicación.
        """
        msg_type = payload.get("type")

        if msg_type == "HANDSHAKE_HELLO":
            self._handle_handshake_hello(payload, addr)
        elif msg_type == "HANDSHAKE_REPLY":
            self._handle_handshake_reply(payload, addr)
        else:
            self.process_application_message(payload, addr)

    def _handle_handshake_hello(self, payload: Dict, addr: Tuple[str, int]):
        """Manejador para cuando se recibe una petición de handshake (lado servidor)."""
        print(f"[PeerConnector] Recibido HANDSHAKE_HELLO de {addr}")
        try:
            private_key = dh_generate_private_key()
            public_key = dh_generate_public_key(private_key)
            
            peer_public_key = payload["public_key"]
            shared_secret = dh_calculate_shared_secret(peer_public_key, private_key)
            
            session = SecureSession()
            session.derive_keys(shared_secret, b'server_nonce_demo', b'client_nonce_demo')
            self.sessions[addr] = session
            
            reply_msg = {
                "type": "HANDSHAKE_REPLY",
                "server_id": self.server_id,
                "public_key": public_key
            }
            self.transport.send_data(reply_msg, addr)
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr} (lado servidor).")
        except Exception as e:
            print(f"❌ Error manejando HANDSHAKE_HELLO: {e}")

    def _handle_handshake_reply(self, payload: Dict, addr: Tuple[str, int]):
        """Manejador para cuando se recibe una respuesta de handshake (lado cliente)."""
        print(f"[PeerConnector] Recibido HANDSHAKE_REPLY de {addr}")
        if addr not in self.pending_handshakes:
            print(f"⚠️ Recibido un REPLY para un handshake no iniciado desde {addr}.")
            return

        try:
            private_key = self.pending_handshakes.pop(addr)
            peer_public_key = payload["public_key"]
            shared_secret = dh_calculate_shared_secret(peer_public_key, private_key)
            
            session = SecureSession()
            session.derive_keys(shared_secret, b'server_nonce_demo', b'client_nonce_demo')
            self.sessions[addr] = session
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr} (lado cliente).")
        except Exception as e:
            print(f"❌ Error manejando HANDSHAKE_REPLY: {e}")

    def process_application_message(self, encrypted_payload: Dict, addr: Tuple[str, int]):
        """Descifra un mensaje de aplicación y lo pasa al MainServer a través del callback."""
        session = self.sessions.get(addr)
        if not session:
            print(f"⚠️ Mensaje de {addr} sin una sesión segura. Ignorando.")
            return

        try:
            plaintext_bytes = session.decrypt(encrypted_payload)
            request = json.loads(plaintext_bytes.decode('utf-8'))
            
            if self.on_message_callback:
                self.on_message_callback(request, addr)

        except Exception as e:
            print(f"❌ Error al descifrar o procesar mensaje de {addr}: {e}")

    def send_message(self, message: Dict, peer_addr: Tuple[str, int]):
        """Cifra un mensaje de aplicación y lo envía."""
        session = self.sessions.get(peer_addr)
        if not session:
            print(f"❌ Error: No hay sesión segura establecida con {peer_addr}. Conecte primero.")
            return

        try:
            message_bytes = json.dumps(message).encode('utf-8')
            encrypted_payload = session.encrypt(message_bytes)
            self.transport.send_data(encrypted_payload, peer_addr)
            print(f"[PeerConnector] -> Mensaje '{message.get('type')}' enviado a {peer_addr}")
        except Exception as e:
            print(f"❌ Error al enviar mensaje cifrado: {e}")

    def stop(self):
        """Detiene la capa de transporte subyacente."""
        if self.transport:
            self.transport.stop()