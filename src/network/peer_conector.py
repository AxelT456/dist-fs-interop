# /src/network/peer_conector.py

import json
import secrets
from typing import Dict, Tuple, Optional, Callable

# --- Importaciones ---
from .transport import ReliableTransport
from .security import SecureSession, dh_generate_private_key, dh_generate_public_key, dh_calculate_shared_secret

class PeerConnector:
    def __init__(self, transport_layer: ReliableTransport, server_id: str, on_message_callback: Callable):
        self.transport = transport_layer
        self.server_id = server_id
        self.sessions: Dict[Tuple[str, int], SecureSession] = {}
        self.pending_handshakes: Dict[Tuple[str, int], int] = {}
        self.on_message_callback = on_message_callback

    def connect_and_secure(self, peer_addr: Tuple[str, int]):
        """Inicia un handshake de seguridad con un peer cuya dirección ya conocemos."""
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
            self.transport.send_data(hello_msg, peer_addr)
        except Exception as e:
            print(f"❌ Error al iniciar el handshake: {e}")

    def handle_incoming_packet(self, payload: Dict, addr: Tuple[str, int]):
        """Punto de entrada que delega los paquetes entrantes."""
        msg_type = payload.get("type")

        if msg_type == "HANDSHAKE_HELLO":
            self._handle_handshake_hello(payload, addr)
        elif msg_type == "HANDSHAKE_REPLY":
            self._handle_handshake_reply(payload, addr)
        else:
            self._process_application_message(payload, addr)

    def _handle_handshake_hello(self, payload: Dict, addr: Tuple[str, int]):
        """Manejador para el lado servidor del handshake."""
        print(f"[PeerConnector] Recibido HANDSHAKE_HELLO de {addr}")
        try:
            private_key = dh_generate_private_key()
            public_key = dh_generate_public_key(private_key)
            shared_secret = dh_calculate_shared_secret(payload["public_key"], private_key)
            
            session = SecureSession()
            session.derive_keys(shared_secret, b'demo_nonce1', b'demo_nonce2')
            self.sessions[addr] = session
            
            reply_msg = {
                "type": "HANDSHAKE_REPLY",
                "server_id": self.server_id,
                "public_key": public_key
            }
            self.transport.send_data(reply_msg, addr)
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr} (lado servidor).")
        except Exception as e:
            print(f"❌ Error en handshake (servidor): {e}")

    def _handle_handshake_reply(self, payload: Dict, addr: Tuple[str, int]):
        """Manejador para el lado cliente del handshake."""
        print(f"[PeerConnector] Recibido HANDSHAKE_REPLY de {addr}")
        if addr not in self.pending_handshakes:
            return

        try:
            private_key = self.pending_handshakes.pop(addr)
            shared_secret = dh_calculate_shared_secret(payload["public_key"], private_key)
            
            session = SecureSession()
            session.derive_keys(shared_secret, b'demo_nonce1', b'demo_nonce2')
            self.sessions[addr] = session
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr} (lado cliente).")
        except Exception as e:
            print(f"❌ Error en handshake (cliente): {e}")

    def _process_application_message(self, encrypted_payload: Dict, addr: Tuple[str, int]):
        """Descifra y delega el mensaje de aplicación al MainServer."""
        session = self.sessions.get(addr)
        if not session:
            return

        try:
            plaintext_bytes = session.decrypt(encrypted_payload)
            request = json.loads(plaintext_bytes.decode('utf-8'))
            if self.on_message_callback:
                self.on_message_callback(request, addr)
        except Exception as e:
            print(f"❌ Error al descifrar mensaje de {addr}: {e}")

    def send_message(self, message: Dict, peer_addr: Tuple[str, int]):
        """Cifra y envía un mensaje de aplicación."""
        session = self.sessions.get(peer_addr)
        if not session:
            print(f"❌ No hay sesión segura con {peer_addr}.")
            return

        try:
            message_bytes = json.dumps(message).encode('utf-8')
            encrypted_payload = session.encrypt(message_bytes)
            self.transport.send_data(encrypted_payload, peer_addr)
        except Exception as e:
            print(f"❌ Error al enviar mensaje cifrado: {e}")

    def stop(self):
        """Detiene la capa de transporte subyacente."""
        if self.transport:
            self.transport.stop()