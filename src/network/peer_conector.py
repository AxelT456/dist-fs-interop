# /src/network/peer_conector.py

import json
import secrets
from typing import Dict, Tuple, Optional

# Importamos las clases base que tú (Ing. 2) creaste
from .transport import ReliableTransport
from .security import SecureSession, dh_generate_private_key, dh_generate_public_key, dh_calculate_shared_secret

# Asumimos que el módulo del Ing. 3 está en esta ruta
from .dns_translator.translator import Translator

class PeerConnector:
    """
    Orquesta la comunicación con otros servidores (peers).
    Utiliza ReliableTransport para la conexión y SecureSession para el cifrado.
    """
    def __init__(self, transport_layer: ReliableTransport, server_id: str):
        self.transport = transport_layer
        self.server_id = server_id
        self.sessions: Dict[Tuple[str, int], SecureSession] = {}
        # El DNS Translator se encargará de encontrar las IPs
        self.dns_translator = Translator() # Asume una configuración por defecto

    def _perform_security_handshake(self, addr: Tuple[str, int]) -> Optional[SecureSession]:
        """
        Realiza el handshake de seguridad (TLS simulado) sobre una conexión ya establecida.
        """
        try:
            print(f"[PeerConnector] Iniciando handshake de seguridad con {addr}...")
            
            # 1. Generar y enviar nuestro TLS-HELLO con la clave pública DH
            private_key = dh_generate_private_key()
            public_key = dh_generate_public_key(private_key)
            nonce = secrets.token_bytes(12)
            
            hello_msg = {
                "type": "HANDSHAKE_HELLO",
                "server_id": self.server_id,
                "public_key": public_key,
                "nonce": nonce.hex()
            }
            # Enviamos el primer mensaje del handshake
            self.transport.send_data(hello_msg, addr)

            # 2. Esperar la respuesta del peer
            #    NOTA: El transport.listen() debería ser modificado para poder
            #    escuchar respuestas de un peer específico. Por ahora, asumimos que lo hace.
            response_payload, _ = self.transport.listen_for_address(addr) # Método hipotético
            
            if response_payload.get("type") != "HANDSHAKE_REPLY":
                print("❌ Falla en handshake: Respuesta inesperada.")
                return None

            # 3. Calcular el secreto compartido y derivar claves
            peer_public_key = response_payload["public_key"]
            peer_nonce = bytes.fromhex(response_payload["nonce"])
            
            shared_secret = dh_calculate_shared_secret(peer_public_key, private_key)
            
            session = SecureSession()
            session.derive_keys(shared_secret, nonce, peer_nonce)
            
            self.sessions[addr] = session
            print(f"[PeerConnector] ✅ Handshake de seguridad completado con {addr}")
            return session

        except Exception as e:
            print(f"❌ Error durante el handshake de seguridad: {e}")
            return None

    def connect_and_secure(self, peer_id: str) -> Optional[Tuple[str, int]]:
        """
        Resuelve el DNS de un peer, se conecta y establece una sesión segura.
        """
        # 1. Usar el DNS Translator para obtener la dirección
        print(f"[PeerConnector] Resolviendo DNS para '{peer_id}'...")
        address = self.dns_translator.resolve(peer_id)
        if not address:
            print(f"❌ No se pudo resolver la dirección para '{peer_id}'")
            return None
        
        peer_addr = (address['ip'], address['port'])

        # 2. Si ya tenemos una sesión, no hacemos nada más
        if peer_addr in self.sessions:
            return peer_addr

        # 3. La conexión de transporte (SYN/ACK) es manejada implícitamente por transport.send_data().
        #    Solo necesitamos realizar el handshake de seguridad.
        if self._perform_security_handshake(peer_addr):
            return peer_addr
        
        return None

    def send_message(self, message: Dict, peer_addr: Tuple[str, int]):
        """
        Cifra un mensaje y lo envía a un peer a través de la capa de transporte.
        """
        if peer_addr not in self.sessions:
            print(f"❌ Error: No hay sesión segura establecida con {peer_addr}. Conecte primero.")
            return

        session = self.sessions[peer_addr]
        
        try:
            # Cifrar el mensaje (convertido a bytes)
            message_bytes = json.dumps(message).encode('utf-8')
            encrypted_payload = session.encrypt(message_bytes)
            
            # Enviar a través de la capa de transporte
            self.transport.send_data(encrypted_payload, peer_addr)
            print(f"[PeerConnector] -> Mensaje '{message.get('type')}' enviado a {peer_addr}")
        except Exception as e:
            print(f"❌ Error al enviar mensaje cifrado: {e}")