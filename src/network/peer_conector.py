# /src/network/peer_conector.py

import json
from typing import Dict, Tuple, Callable
from .transport import ReliableTransport
from .security import SecureSession, dh_generate_private_key, dh_generate_public_key, dh_calculate_shared_secret

class PeerConnector:
    def __init__(self, transport_layer: ReliableTransport, server_id: str, on_message_callback: Callable):
        self.transport = transport_layer
        self.server_id = server_id
        self.sessions: Dict[Tuple[str, int], SecureSession] = {}
        # Guarda la clave privada del cliente durante el handshake
        self.pending_handshakes: Dict[Tuple[str, int], int] = {} 
        self.on_message_callback = on_message_callback

    def connect_and_secure(self, peer_addr: Tuple[str, int]) -> bool:
        if not self.transport.connect(peer_addr):
            print(f"Fallo al establecer la conexión de transporte con {peer_addr}")
            return False
        
        print(f"[PeerConnector] Transporte OK. Iniciando handshake de seguridad con {peer_addr}...")
        try:
            private_key = dh_generate_private_key()
            public_key = dh_generate_public_key(private_key)
            
            # Guarda la clave privada para usarla al recibir la respuesta
            self.pending_handshakes[peer_addr] = private_key
            
            hello_msg = {
                "type": "HANDSHAKE_HELLO",
                "server_id": self.server_id,
                "public_key": public_key
            }
            self.transport.send_data(hello_msg, peer_addr)
            return True
        except Exception as e:
            print(f"Error al iniciar el handshake de seguridad: {e}")
            return False

    def handle_incoming_packet(self, payload: Dict, addr: Tuple[str, int]):
        msg_type = payload.get("type")
        if msg_type == "HANDSHAKE_HELLO":
            self._handle_handshake_hello(payload, addr)
        elif msg_type == "HANDSHAKE_REPLY":
            self._handle_handshake_reply(payload, addr)
        elif addr in self.sessions:
            self._process_application_message(payload, addr)

    def _handle_handshake_hello(self, payload: Dict, addr: Tuple[str, int]):
        print(f"[PeerConnector] Recibido HANDSHAKE_HELLO de {addr}")
        try:
            server_private_key = dh_generate_private_key()
            server_public_key = dh_generate_public_key(server_private_key)
            shared_secret = dh_calculate_shared_secret(payload["public_key"], server_private_key)
            
            client_id, server_id = payload["server_id"], self.server_id
            
            session = SecureSession()
            session.derive_keys(shared_secret, client_id, server_id)
            self.sessions[addr] = session
            
            reply_msg = { "type": "HANDSHAKE_REPLY", "server_id": self.server_id, "public_key": server_public_key }
            self.transport.send_data(reply_msg, addr)
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr} (lado servidor).")
        except Exception as e:
            print(f"Error en handshake (servidor): {e}")

    def _handle_handshake_reply(self, payload: Dict, addr: Tuple[str, int]):
        print(f"[PeerConnector] Recibido HANDSHAKE_REPLY de {addr}")
        if addr not in self.pending_handshakes:
            return

        try:
            # ¡Usa la clave privada original que guardamos!
            client_private_key = self.pending_handshakes.pop(addr)
            shared_secret = dh_calculate_shared_secret(payload["public_key"], client_private_key)

            client_id, server_id = self.server_id, payload["server_id"]
            
            session = SecureSession()
            session.derive_keys(shared_secret, client_id, server_id)
            self.sessions[addr] = session
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr} (lado cliente).")
        except Exception as e:
            print(f"Error en handshake (cliente): {e}")

    def _process_application_message(self, encrypted_payload: Dict, addr: Tuple[str, int]):
        session = self.sessions.get(addr)
        if not session: return
        try:
            plaintext_bytes = session.decrypt(encrypted_payload)
            request = json.loads(plaintext_bytes.decode('utf-8'))
            self.on_message_callback(request, addr)
        except Exception as e:
            print(f"Error al descifrar mensaje: {e}")

    def send_message(self, message: Dict, peer_addr: Tuple[str, int]):
        session = self.sessions.get(peer_addr)
        if not session: return
        try:
            message_bytes = json.dumps(message).encode('utf-8')
            encrypted_payload = session.encrypt(message_bytes)
            self.transport.send_data(encrypted_payload, peer_addr)
        except Exception as e:
            print(f"Error al enviar mensaje cifrado: {e}")

    def stop(self):
        if self.transport:
            self.transport.stop()