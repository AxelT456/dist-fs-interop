# /src/network/transport.py

import socket
import json
import random
import time
from typing import Dict, Tuple, Any, Optional

# ... (constantes y jsend no cambian) ...
RTO = 1.0
CLEANUP_IDLE = 60
FAST_RETX_DUPS = 3

def jsend(sock: socket.socket, msg: Dict, addr: Tuple[str, int]):
    sock.sendto((json.dumps(msg) + "\n").encode("utf-8"), addr)

class ConnectionState:
    # ... (esta clase no cambia) ...
    def __init__(self, addr: Tuple[str, int], cid: int, sid: int = 0):
        self.addr = addr
        self.cid = cid
        self.sid = sid
        self.state = "SYN_SENT" if sid == 0 else "SYN_RCVD"
        self.expected_final_ack = sid + 1 if sid != 0 else 0
        self.next_seq_to_send = sid + 1 if sid != 0 else cid
        self.waiting_ack_for = None
        self.last_sent_payload = None
        self.last_send_time = 0.0
        self.dup_ack_count = 0
        self.last_ack_val = None
        self.last_activity = time.time()
        self.fin_sent = False
        self.fin_acked = False

class ReliableTransport:
    # ... (el __init__ no cambia) ...
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(0.2)
        self.connections: Dict[Tuple[str, int], ConnectionState] = {}
        print(f"[Transport]   Servidor escuchando en {host}:{port}")

    # --- NUEVO MÉTODO PARA EL CLIENTE ---
    def connect(self, addr: Tuple[str, int]) -> bool:
        """Inicia el handshake de transporte (lado cliente)."""
        if addr in self.connections:
            return True # Ya conectado

        cid = random.randint(1000, 999999)
        st = ConnectionState(addr, cid)
        self.connections[addr] = st
        
        print(f"[Transport] Enviando SYN a {addr} con CID={cid}")
        syn_msg = {"type": "SYN", "seq": cid}
        jsend(self.sock, syn_msg, addr)
        st.last_activity = time.time()
        
        # Esperar por el SYN-ACK
        start_time = time.time()
        while time.time() - start_time < RTO * 3: # Esperar un tiempo razonable
            try:
                data, _ = self.sock.recvfrom(65535)
                msg = json.loads(data.decode("utf-8").strip())
                if msg.get("type") == "SYN-ACK" and msg.get("ack") == cid + 1:
                    st.state = "ESTABLISHED"
                    st.sid = msg["sid"]
                    st.next_seq_to_send = msg["ack"]
                    ack_msg = {"type": "ACK", "ack": msg["seq"] + 1, "cid": cid, "sid": st.sid}
                    jsend(self.sock, ack_msg, addr)
                    print(f"[Transport] ✅ Conexión establecida con {addr}")
                    return True
            except (socket.timeout, json.JSONDecodeError):
                continue
        
        print(f"❌ Timeout estableciendo conexión de transporte con {addr}")
        del self.connections[addr]
        return False

    # --- MÉTODOS EXISTENTES (con pequeñas correcciones) ---
    def _get_or_create_connection(self, addr: Tuple[str, int], msg: Dict) -> ConnectionState:
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
        ack = msg.get("ack")
        if ack is None: return
        st.last_activity = time.time()

        if st.state == "SYN_RCVD" and ack == st.expected_final_ack:
            st.state = "ESTABLISHED"
            print(f"[Transport] ✅ Conexión establecida con {st.addr}")
            return

        if st.state == "ESTABLISHED" and st.waiting_ack_for is not None:
            if ack >= st.waiting_ack_for:
                st.waiting_ack_for = None
                st.last_sent_payload = None
                st.dup_ack_count = 0
                st.last_ack_val = ack

    def send_data(self, payload: Dict, addr: Tuple[str, int]):
        st = self.connections.get(addr)
        if not st or st.state != "ESTABLISHED":
            print(f"❌ [Transport] Error: Conexión con {addr} no está establecida. Estado: {st.state if st else 'N/A'}")
            return
            
        msg = {
            "type": "DATA",
            "seq": st.next_seq_to_send,
            "cid": st.cid,
            "sid": st.sid,
            "payload": payload
        }
        jsend(self.sock, msg, addr)
        
        st.last_sent_payload = payload
        st.waiting_ack_for = st.next_seq_to_send + 1 # Esperamos ACK para este paquete
        st.next_seq_to_send += len(json.dumps(payload)) # Simulación de tamaño de paquete
        st.last_send_time = time.time()
        st.last_activity = st.last_send_time

    def listen(self) -> Tuple[Optional[Dict], Optional[Tuple[str, int]]]:
        try:
            data, addr = self.sock.recvfrom(65535)
        except socket.timeout:
            self._check_timeouts()
            return None, None
        except OSError:
            return None, None

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
                ack_msg = {"type": "ACK", "ack": msg["seq"] + len(json.dumps(msg.get("payload"))), "cid": st.cid, "sid": st.sid}
                jsend(self.sock, ack_msg, addr)
                return msg.get("payload"), addr
        return None, None

    def _check_timeouts(self):
        # ... (este método no necesita cambios) ...
        pass
    
    def stop(self):
        print("[Transport] Cerrando el socket.")
        if self.sock:
            self.sock.close()
            self.sock = None