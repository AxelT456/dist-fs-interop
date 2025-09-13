# /src/network/transport.py
import socket
import json
import random
import time
from typing import Dict, Tuple, Any

# Constantes de configuración del transporte
RTO = 1.0  # Tiempo de espera para retransmisión (1 segundo)
CLEANUP_IDLE = 60 # Tiempo de inactividad para limpiar una conexión (60 segundos)
FAST_RETX_DUPS = 3 # Número de ACKs duplicados para una retransmisión rápida

def jsend(sock: socket.socket, msg: Dict, addr: Tuple[str, int]):
    """Codifica un diccionario a JSON y lo envía por el socket."""
    # print(f"[Transport] -> Enviando {msg.get('type')} a {addr}") # Descomentar para depuración
    sock.sendto((json.dumps(msg) + "\n").encode("utf-8"), addr)

class ConnectionState:
    """
    Gestiona el estado de una conexión individual (versión simplificada de ClientState).
    """
    def __init__(self, addr: Tuple[str, int], cid: int, sid: int):
        self.addr = addr
        self.cid = cid
        self.sid = sid
        self.state = "SYN_RCVD" # Estados: SYN_RCVD, ESTABLISHED, FIN_WAIT, CLOSING, CLOSED
        
        # Gestión de secuencia y ACK
        self.expected_final_ack = sid + 1
        self.next_seq_to_send = sid + 1
        self.waiting_ack_for = None
        
        # Gestión de timeouts y retransmisión
        self.last_sent_payload = None
        self.last_send_time = 0.0
        self.dup_ack_count = 0
        self.last_ack_val = None
        
        # Gestión del estado de la conexión
        self.last_activity = time.time()
        self.fin_sent = False
        self.fin_acked = False

class ReliableTransport:
    """
    Provee una capa de transporte confiable sobre UDP, simulando a TCP.
    """
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(0.2)
        self.connections: Dict[Tuple[str, int], ConnectionState] = {}
        print(f"[Transport]  транспорт Servidor escuchando en {host}:{port}")

    def _get_or_create_connection(self, addr: Tuple[str, int], msg: Dict) -> ConnectionState:
        """Obtiene una conexión existente o inicia el handshake para una nueva."""
        if addr in self.connections:
            return self.connections[addr]
        
        if msg.get("type") == "SYN":
            cid = msg.get("seq")
            if cid is None: return None
            
            sid = random.randint(1000, 999999)
            st = ConnectionState(addr, cid, sid)
            self.connections[addr] = st
            
            print(f"[Transport] SYN recibido de {addr}, CID={cid}, generando SID={sid}")
            synack = {"type": "SYN-ACK", "seq": sid, "ack": cid + 1, "cid": cid, "sid": sid}
            jsend(self.sock, synack, addr)
            st.last_activity = time.time()
            return st
        return None

    def _handle_ack(self, st: ConnectionState, msg: Dict):
        """Procesa los mensajes ACK para el handshake y la transferencia de datos."""
        ack = msg.get("ack")
        if ack is None: return
        st.last_activity = time.time()

        # Completa el handshake de 3 vías
        if st.state == "SYN_RCVD" and ack == st.expected_final_ack:
            st.state = "ESTABLISHED"
            print(f"[Transport] ✅ Conexión establecida con {st.addr}")
            return

        # Procesa ACK de paquetes de datos
        if st.state == "ESTABLISHED" and st.waiting_ack_for is not None:
            if ack == st.waiting_ack_for:
                # ACK correcto, podemos enviar el siguiente paquete
                st.waiting_ack_for = None
                st.last_sent_payload = None
                st.dup_ack_count = 0
                st.last_ack_val = ack
            else:
                # ACK duplicado
                if st.last_ack_val == ack:
                    st.dup_ack_count += 1
                else:
                    st.dup_ack_count = 1
                    st.last_ack_val = ack
                
                if st.dup_ack_count >= FAST_RETX_DUPS and st.last_sent_payload is not None:
                    print(f"[Transport] 🔁 Fast Retransmit a {st.addr}")
                    self.send_data(st.last_sent_payload, st.addr) # Llama al método público de envío
                    st.dup_ack_count = 0

    def _check_timeouts(self):
        """Verifica y maneja los timeouts para retransmisiones y limpieza de conexiones."""
        current_time = time.time()
        to_remove = []
        for addr, st in self.connections.items():
            # Timeout de retransmisión de datos
            if st.state == "ESTABLISHED" and st.waiting_ack_for is not None:
                if (current_time - st.last_send_time) >= RTO:
                    print(f"[Transport] ⏰ Timeout, retransmitiendo a {st.addr}")
                    self.send_data(st.last_sent_payload, st.addr)

            # Timeout de inactividad de la conexión
            if (current_time - st.last_activity) > CLEANUP_IDLE:
                print(f"[Transport] 🧹 Limpiando conexión inactiva de {addr}")
                to_remove.append(addr)
        
        for addr in to_remove:
            del self.connections[addr]

    def send_data(self, payload: Dict, addr: Tuple[str, int]):
        """
        Envía un paquete de datos de forma confiable a una dirección.
        Este método es usado tanto externamente como para retransmisiones.
        """
        st = self.connections.get(addr)
        if not st or st.state != "ESTABLISHED":
            print(f"[Transport] Error: Intento de enviar datos a una conexión no establecida con {addr}")
            return
            
        # El payload ya debe ser un diccionario listo para ser JSON-serializado
        # que contiene el contenido cifrado de la capa de seguridad.
        msg = {
            "type": "DATA",
            "seq": st.next_seq_to_send,
            "cid": st.cid,
            "sid": st.sid,
            "payload": payload # El payload cifrado se anida aquí
        }
        jsend(self.sock, msg, addr)
        
        # Guardar estado para posible retransmisión
        st.last_sent_payload = payload
        st.waiting_ack_for = st.next_seq_to_send + 1
        st.last_send_time = time.time()
        st.last_activity = st.last_send_time

    def listen(self) -> Tuple[Dict, Tuple[str, int]]:
        """
        Bucle principal de escucha. Procesa paquetes de control internamente y
        devuelve los paquetes de datos de la aplicación a la capa superior.
        """
        while True:
            try:
                data, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                self._check_timeouts()
                continue

            for line in data.decode("utf-8").splitlines():
                if not line.strip(): continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                mtype = msg.get("type")
                st = self._get_or_create_connection(addr, msg)
                if not st: continue
                
                if mtype == "ACK":
                    self._handle_ack(st, msg)
                elif mtype == "DATA":
                    # Aquí es donde se entrega el payload a la capa superior.
                    # El ACK se envía para confirmar la recepción.
                    ack_msg = {"type": "ACK", "ack": msg["seq"] + 1, "cid": st.cid, "sid": st.sid}
                    jsend(self.sock, ack_msg, addr)
                    
                    # (Opcional) Verificación de secuencia para entrega ordenada
                    # if msg["seq"] == st.expected_seq_from_peer:
                    return msg.get("payload"), addr
                # La lógica de FIN/ACK-FIN se puede añadir aquí si es necesaria.