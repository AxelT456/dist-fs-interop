# /src/network/peer_conector.py
import socket
import threading
import json
import os
import sys
import time
import random
from typing import Callable, Dict, Tuple, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ..network.security import SecureSession

class PeerConnector:
    def __init__(self, local_ip: str, local_port: int, on_message: Callable = None):
        self.local_ip = local_ip
        self.local_port = local_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.local_ip, self.local_port))
        self.sock.settimeout(1.0)
        self.running = True
        self.on_message = on_message
        self.connections: Dict[Tuple[str, int], Dict] = {}
        self.sessions: Dict[Tuple[str, int], SecureSession] = {}
        
        # Iniciar hilo de escucha
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        print(f"[PeerConnector] Escuchando en {self.local_ip}:{self.local_port}")

    def _listen(self):
        """Escucha mensajes entrantes"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(65535)
                if data:
                    for line in data.decode("utf-8").splitlines():
                        if line.strip():
                            try:
                                payload = json.loads(line)
                                self._process_message(payload, addr)
                            except json.JSONDecodeError:
                                print(f"[PeerConnector] Error decodificando JSON de {addr}")
                                continue
                pass
            except socket.timeout:
                # Limpiar conexiones antiguas en cada timeout
                self._cleanup_old_connections()
                continue
            except Exception as e:
                if self.running:
                    print(f"[PeerConnector] Error al recibir: {e}")

    def _process_message(self, payload: Dict, addr: Tuple[str, int]):
        """Procesa diferentes tipos de mensajes"""
        try:
            if payload.get("type") == "SYN":
                self._handle_syn(payload, addr)
            elif payload.get("type") == "SYN-ACK":
                self._handle_syn_ack(payload, addr)
            elif payload.get("type") == "ACK":
                self._handle_ack(payload, addr)
            elif payload.get("type") == "HANDSHAKE":
                self._handle_handshake(payload, addr)
            elif payload.get("type") == "HANDSHAKE_RESPONSE":
                self._handle_handshake_response(payload, addr)
            elif payload.get("type") == "HANDSHAKE_COMPLETE":  # Nuevo handler
                self._handle_handshake_complete(payload, addr)
            elif payload.get("type") == "FIN":
                self._handle_fin(payload, addr)
            elif isinstance(payload, dict) and "ct" in payload:
                self._handle_encrypted_data(payload, addr)
            elif self.on_message:
                self.on_message(payload, addr)
            else:
                print(f"[PeerConnector] Mensaje no manejado de {addr}: {payload}")
        except Exception as e:
            print(f"[PeerConnector] Error procesando mensaje de {addr}: {e}")
            
    def _handle_fin(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja mensaje FIN de cierre de conexión"""
        print(f"[PeerConnector] FIN recibido de {addr}")
        if addr in self.connections:
            del self.connections[addr]
        if addr in self.sessions:
            del self.sessions[addr]
        print(f"[PeerConnector] Sesión con {addr} cerrada")
    
    def _handle_handshake_complete(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja finalización de handshake (lado cliente)"""
        if addr not in self.connections:
            return
            
        conn = self.connections[addr]
        server_nonce = bytes.fromhex(payload.get("server_nonce", ""))
        
        if not server_nonce:
            print(f"[PeerConnector] Handshake complete inválido de {addr}")
            return
        
        # Calcular secreto compartido
        from ..network.security import dh_calculate_shared_secret
        shared_secret = dh_calculate_shared_secret(conn["server_public"], conn["client_private"])
        
        # Crear y almacenar sesión
        session = SecureSession()
        session.derive_keys(shared_secret, server_nonce)
        self.sessions[addr] = session
        
        conn["state"] = "SECURE_ESTABLISHED"
        conn["last_activity"] = time.time()
        print(f"[PeerConnector] ✅ Sesión segura establecida con {addr}")

    def _handle_syn(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja handshake SYN (lado servidor)"""
        cid = payload.get("seq")
        sid = random.randint(1000, 9999)
        
        # Guardar información de conexión
        self.connections[addr] = {
            "state": "SYN_RCVD",
            "cid": cid,
            "sid": sid,
            "last_activity": time.time()
        }
        
        # Responder con SYN-ACK
        syn_ack_msg = {
            "type": "SYN-ACK", 
            "seq": sid, 
            "ack": cid + 1
        }
        self.send(syn_ack_msg, addr)
        print(f"[PeerConnector] SYN-ACK enviado a {addr}")

    def _handle_syn_ack(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja handshake SYN-ACK (lado cliente)"""
        if addr not in self.connections:
            print(f"[PeerConnector] No hay conexión para {addr}")
            return
            
        conn = self.connections[addr]
        sid = payload.get("seq")
        ack = payload.get("ack")
        
        if ack == conn["cid"] + 1:
            conn["state"] = "SYN_ACK_RCVD"
            conn["sid"] = sid
            conn["last_activity"] = time.time()
            
            # Enviar ACK final
            ack_msg = {
                "type": "ACK", 
                "ack": sid + 1, 
                "cid": conn["cid"], 
                "sid": sid
            }
            self.send(ack_msg, addr)
            print(f"[PeerConnector] ACK final enviado a {addr}")
            
            # CORRECCIÓN: NO iniciar handshake Diffie-Hellman aquí
            # El servidor debe iniciar el handshake después de establecer la conexión
            conn["state"] = "ESTABLISHED"
            print(f"[PeerConnector] ✅ Conexión establecida con {addr}")

    def _handle_ack(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja ACK (completa handshake)"""
        if addr not in self.connections:
            return
            
        conn = self.connections[addr]
        ack = payload.get("ack")
        
        # Lado servidor: confirmar handshake completo
        if conn["state"] == "SYN_RCVD" and ack == conn["sid"] + 1:
            conn["state"] = "ESTABLISHED"
            conn["last_activity"] = time.time()
            print(f"[PeerConnector] ✅ Conexión establecida con {addr}")
            
            # Ahora iniciar handshake Diffie-Hellman (lado servidor)
            self._initiate_handshake(addr)


    def _initiate_handshake(self, addr: Tuple[str, int]):
        """Inicia handshake Diffie-Hellman (lado que inició la conexión)"""
        if addr not in self.connections:
            return
            
        conn = self.connections[addr]
        
        # Solo iniciar handshake si la conexión está establecida
        if conn["state"] != "ESTABLISHED":
            print(f"[PeerConnector] Conexión no establecida para handshake con {addr}")
            return
        
        # Usar Diffie-Hellman real en lugar de toy
        from ..network.security import dh_generate_private_key, dh_generate_public_key
        
        # CORRECCIÓN: Cambiar "client_private" a "server_private" para consistencia
        server_private = dh_generate_private_key()
        server_public = dh_generate_public_key(server_private)
        
        # CORRECCIÓN: Almacenar como server_private en lugar de client_private
        conn["server_private"] = server_private
        conn["state"] = "HANDSHAKE_SENT"
        
        handshake_msg = {
            "type": "HANDSHAKE", 
            "client_public": server_public  # Enviar la public key del servidor como "client_public"
        }
        self.send(handshake_msg, addr)
        print(f"[PeerConnector] Handshake Diffie-Hellman enviado a {addr}")

    def _handle_handshake(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja handshake Diffie-Hellman (lado cliente)"""
        # Solo el cliente debería recibir mensajes HANDSHAKE del servidor
        if addr not in self.connections:
            print(f"[PeerConnector] Handshake de {addr} pero no hay conexión registrada")
            return
            
        conn = self.connections[addr]
        server_public = payload.get("client_public")  # El servidor envía su public key como "client_public"
        
        if not server_public:
            print(f"[PeerConnector] Handshake inválido de {addr}")
            return
        
        print(f"[PeerConnector] Handshake recibido de servidor {addr}")
        
        # Generar nuestra clave privada y pública si no existe
        if "client_private" not in conn:
            from ..network.security import dh_generate_private_key, dh_generate_public_key
            conn["client_private"] = dh_generate_private_key()
            conn["client_public"] = dh_generate_public_key(conn["client_private"])
        
        # Almacenar la public key del servidor
        conn["server_public"] = server_public
        conn["state"] = "HANDSHAKE_RECEIVED"
        conn["last_activity"] = time.time()
        
        # Enviar nuestra public key al servidor como respuesta
        handshake_response = {
            "type": "HANDSHAKE_RESPONSE",
            "client_public": conn["client_public"]
        }
        self.send(handshake_response, addr)
        print(f"[PeerConnector] Handshake response enviado al servidor {addr}")
            

    def _handle_handshake_response(self, payload: Dict, addr: Tuple[str, int]):
        """Maneja respuesta de handshake (tanto lado servidor como cliente)"""
        if addr not in self.connections:
            return
            
        conn = self.connections[addr]
        
        # Determinar si somos el servidor (recibimos client_public) o el cliente (recibimos server_public)
        if "client_public" in payload:
            # Somos el servidor: recibimos la public key del cliente
            client_public = payload.get("client_public")
            
            if not client_public:
                print(f"[PeerConnector] Handshake response inválido de {addr}")
                return
            
            print(f"[PeerConnector] Handshake response recibido de cliente {addr}")
            
            # CORRECCIÓN: Usar server_private en lugar de conn["server_private"]
            if "server_private" not in conn:
                print(f"[PeerConnector] No hay server_private para {addr}")
                return
                
            # Calcular secreto compartido
            from ..network.security import dh_calculate_shared_secret
            shared_secret = dh_calculate_shared_secret(client_public, conn["server_private"])
            
            # Generar nonce y crear sesión
            server_nonce = os.urandom(12)
            session = SecureSession()
            session.derive_keys(shared_secret, server_nonce)
            self.sessions[addr] = session
            
            # Enviar el nonce al cliente
            nonce_response = {
                "type": "HANDSHAKE_COMPLETE",
                "server_nonce": server_nonce.hex()
            }
            self.send(nonce_response, addr)
            print(f"[PeerConnector] Handshake completo, nonce enviado a {addr}")
            
            conn["state"] = "SECURE_ESTABLISHED"
            conn["last_activity"] = time.time()
            
        elif "server_public" in payload:
            # Somos el cliente: recibimos la public key del servidor (esto ya no debería pasar)
            server_public = payload.get("server_public")
            server_nonce = bytes.fromhex(payload.get("server_nonce", ""))
            
            if not server_public or not server_nonce:
                print(f"[PeerConnector] Handshake response inválido de {addr}")
                return
            
            # Calcular secreto compartido usando Diffie-Hellman real
            from ..network.security import dh_calculate_shared_secret
            shared_secret = dh_calculate_shared_secret(server_public, conn["client_private"])
            
            # Crear y almacenar sesión
            session = SecureSession()
            session.derive_keys(shared_secret, server_nonce)
            self.sessions[addr] = session
            
            conn["state"] = "SECURE_ESTABLISHED"
            conn["last_activity"] = time.time()
            print(f"[PeerConnector] ✅ Sesión segura establecida con {addr}")
        
    def _handle_encrypted_data(self, encrypted_payload: Dict, addr: Tuple[str, int]):
        """Maneja datos cifrados"""
        
        print(f"[PeerConnector] Datos cifrados recibidos de {addr}")
        session = self.sessions.get(addr)
        if not session:
            print(f"[PeerConnector] No hay sesión para {addr}")
            return
        
        try:
            # Descifrar el payload
            decrypted_data = session.decrypt(encrypted_payload)
            
            # Parsear el JSON descifrado
            mensaje = json.loads(decrypted_data.decode('utf-8'))
            print(f"[PeerConnector] Datos descifrados de {addr}: {mensaje}")
            
            # IMPORTANTE: Procesar el mensaje descifrado a través del sistema normal
            # en lugar de solo pasararlo al callback
            self._process_message(mensaje, addr)
            
        except Exception as e:
            print(f"[PeerConnector] Error al procesar datos cifrados: {e}")

    def connect(self, remote_ip: str, remote_port: int) -> bool:
        """Establece conexión con un peer remoto"""
        addr = (remote_ip, remote_port)
        
        # Verificar si ya existe conexión segura
        if addr in self.sessions:
            print(f"[PeerConnector] Ya hay una sesión segura con {addr}")
            return True
            
        # Verificar si ya existe conexión establecida
        if addr in self.connections and self.connections[addr]["state"] == "ESTABLISHED":
            print(f"[PeerConnector] Ya hay una conexión establecida con {addr}")
            return True
        
        # Iniciar handshake de 3 vías
        cid = random.randint(1000, 9999)
        
        self.connections[addr] = {
            "state": "SYN_SENT",
            "cid": cid,
            "last_activity": time.time()
        }
        
        # Enviar SYN
        syn_msg = {"type": "SYN", "seq": cid}
        self.send(syn_msg, addr)
        print(f"[PeerConnector] SYN enviado a {addr}")
        
        # Esperar conexión establecida con timeout
        start_time = time.time()
        while time.time() - start_time < 10.0:
            if addr in self.connections:
                state = self.connections[addr]["state"]
                if state == "ESTABLISHED":
                    return True
                elif state == "SECURE_ESTABLISHED":
                    return True
            time.sleep(0.1)
        
        print(f"[PeerConnector] Timeout estableciendo conexión con {addr}")
        if addr in self.connections:
            del self.connections[addr]
        return False

    def send(self, message: Dict, addr: Tuple[str, int]):
        """Envía un mensaje a una dirección"""
        try:
            msg_bytes = (json.dumps(message) + "\n").encode("utf-8")
            self.sock.sendto(msg_bytes, addr)
            print(f"[PeerConnector] Mensaje enviado a {addr}: {message.get('type')}")
        except Exception as e:
            print(f"[PeerConnector] Error enviando mensaje a {addr}: {e}")

    def send_encrypted(self, message: Dict, addr: Tuple[str, int]) -> bool:
        """Envía un mensaje cifrado a una dirección"""
        # Verificar si hay sesión segura
        if addr not in self.sessions:
            print(f"[PeerConnector] No hay sesión segura para {addr}")
            
            # Intentar establecer conexión si no existe
            if self.connect(addr[0], addr[1]):
                # Esperar a que la sesión segura se establezca
                start_time = time.time()
                while time.time() - start_time < 5.0:
                    if addr in self.sessions:
                        break
                    time.sleep(0.1)
                
                if addr not in self.sessions:
                    print(f"[PeerConnector] No se pudo establecer sesión segura con {addr}")
                    return False
        
        session = self.sessions[addr]
        
        try:
            encrypted_msg = session.encrypt(json.dumps(message).encode('utf-8'))
            self.send(encrypted_msg, addr)
            return True
        except Exception as e:
            print(f"[PeerConnector] Error enviando mensaje cifrado: {e}")
            return False

    def disconnect(self, addr: Tuple[str, int]):
        """Cierra conexión con un peer"""
        try:
            # Enviar mensaje FIN
            fin_msg = {"type": "FIN"}
            self.send(fin_msg, addr)
        except:
            pass
        finally:
            if addr in self.connections:
                del self.connections[addr]
            if addr in self.sessions:
                del self.sessions[addr]
            print(f"[PeerConnector] Desconectado de {addr}")

    def stop(self):
        """Detiene el connector"""
        self.running = False
        # Desconectar todas las conexiones
        for addr in list(self.connections.keys()):
            self.disconnect(addr)
        self.sock.close()
        print("[PeerConnector] Detenido")

    def send_and_wait_response(self, message: Dict, addr: Tuple[str, int], timeout: float = 5.0) -> Optional[Dict]:
        """Envía un mensaje y espera una respuesta con timeout"""
        if not self.connect(addr[0], addr[1]):
            return None
        
        # Crear un identificador único para esta solicitud
        request_id = random.randint(1000, 9999)
        message["request_id"] = request_id
        
        # Variable para almacenar la respuesta
        response_received = None
        
        # Función temporal para capturar la respuesta
        def temp_on_message(msg, response_addr):
            nonlocal response_received
            if msg.get("request_id") == request_id and response_addr == addr:
                response_received = msg
        
        # Guardar el manejador original y establecer el temporal
        original_handler = self.on_message
        self.on_message = temp_on_message
        
        # Enviar el mensaje
        if not self.send_encrypted(message, addr):
            self.on_message = original_handler
            return None
        
        # Esperar la respuesta
        start_time = time.time()
        while time.time() - start_time < timeout:
            if response_received is not None:
                break
            time.sleep(0.1)
        
        # Restaurar el manejador original
        self.on_message = original_handler
        
        return response_received

    def _cleanup_old_connections(self):
        """Limpia conexiones antiguas"""
        current_time = time.time()
        to_remove = []
        
        for addr, conn in list(self.connections.items()):
            if current_time - conn["last_activity"] > 60.0:  # 60 segundos de inactividad
                to_remove.append(addr)
        
        for addr in to_remove:
            if addr in self.connections:
                del self.connections[addr]
            if addr in self.sessions:
                del self.sessions[addr]
            print(f"[PeerConnector] Conexión con {addr} limpiada por inactividad")