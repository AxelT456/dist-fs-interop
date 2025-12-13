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
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((host, port))
        self.sock.settimeout(0.1) # Timeout más corto para agilizar
        self.connections: Dict[Tuple[str, int], ConnectionState] = {}
        print(f"[Transport]   Servidor escuchando en {host}:{port}")

    def connect(self, addr: Tuple[str, int]) -> bool:
        """Inicia el handshake de transporte (lado cliente) y ESPERA a que se complete."""
        if addr in self.connections and self.connections[addr].state == "ESTABLISHED":
            return True

        cid = random.randint(1000, 999999)
        st = ConnectionState(addr, cid)
        self.connections[addr] = st
        
        syn_msg = {"type": "SYN", "seq": cid}
        
        # Intentar enviar SYN y esperar SYN-ACK varias veces
        for attempt in range(5): # 5 intentos
            print(f"[Transport] Enviando SYN a {addr} (Intento {attempt + 1})")
            jsend(self.sock, syn_msg, addr)
            
            start_time = time.time()
            while time.time() - start_time < 1.0: # Esperar 1 segundo por la respuesta
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

    def _get_or_create_connection(self, addr: Tuple[str, int], msg: Dict) -> Optional[ConnectionState]:
        if addr in self.connections:
            return self.connections[addr]
        
        if msg.get("type") == "SYN":
            cid = msg.get("seq")
            if cid is None: return None
            
            sid = random.randint(1000, 999999)
            st = ConnectionState(addr, cid, sid)
            self.connections[addr] = st
            
            synack = {"type": "SYN-ACK", "seq": sid, "ack": cid + 1, "cid": cid, "sid": sid}
            jsend(self.sock, synack, addr)
            return st
        return None

    def _handle_ack(self, st: ConnectionState, msg: Dict):
        ack = msg.get("ack")
        if ack is None: return

        if st.state == "SYN_RCVD" and ack == st.expected_final_ack:
            st.state = "ESTABLISHED"
            print(f"[Transport] ✅ Conexión establecida con {st.addr} (lado servidor)")
            return

        if st.state == "ESTABLISHED" and st.waiting_ack_for is not None:
            if ack >= st.waiting_ack_for:
                st.waiting_ack_for = None

    def send_data(self, payload: Dict, addr: Tuple[str, int]):
        st = self.connections.get(addr)
        # Verificación crucial: solo enviar si la conexión está ESTABLISHED
        if not st or st.state != "ESTABLISHED":
            if not self.connect(addr):
                 print(f"❌ [Transport] Fallo al conectar. No se puede enviar data a {addr}")
                 return
            st = self.connections.get(addr) # Re-obtener el estado de conexión

        msg = {
            "type": "DATA",
            "seq": st.next_seq_to_send,
            "cid": st.cid,
            "sid": st.sid,
            "payload": payload
        }
        jsend(self.sock, msg, addr)
        st.waiting_ack_for = st.next_seq_to_send + len(json.dumps(payload))
        st.next_seq_to_send = st.waiting_ack_for

    def listen(self) -> Tuple[Optional[Dict], Optional[Tuple[str, int]]]:
        try:
            data, addr = self.sock.recvfrom(65535)
        except socket.timeout:
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

    def stop(self):
        if self.sock:
            self.sock.close()
            self.sock = None