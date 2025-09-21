#!/usr/bin/env python3
# test_key_sync.py - Verificar que las claves se generen igual en ambos lados

import sys
sys.path.append('src/network')

from src.network.security import SecureSession, dh_generate_private_key, dh_generate_public_key, dh_calculate_shared_secret
import json

def test_key_derivation():
    print("=== PRUEBA DE DERIVACIÓN DE CLAVES ===\n")
    
    # Simular handshake Diffie-Hellman
    client_private = dh_generate_private_key()
    server_private = dh_generate_private_key()
    
    client_public = dh_generate_public_key(client_private)
    server_public = dh_generate_public_key(server_private)
    
    # Calcular secreto compartido (debe ser igual en ambos lados)
    client_shared = dh_calculate_shared_secret(server_public, client_private)
    server_shared = dh_calculate_shared_secret(client_public, server_private)
    
    print(f"Secreto compartido (cliente): {client_shared}")
    print(f"Secreto compartido (servidor): {server_shared}")
    print(f"Secretos iguales: {client_shared == server_shared}\n")
    
    if client_shared != server_shared:
        print("ERROR: Los secretos compartidos no coinciden!")
        return False
    
    # Simular derivación de claves en ambos lados
    client_id = "127.0.0.1:49210"
    server_id = "127.0.0.3:5002"
    
    # Cliente deriva claves
    client_session = SecureSession()
    client_session.derive_keys(client_shared, client_id, server_id, is_client=True)
    
    # Servidor deriva claves  
    server_session = SecureSession()
    server_session.derive_keys(server_shared, client_id, server_id, is_client=False)
    
    # Comparar claves generadas
    print("CLAVES GENERADAS:")
    print(f"Cliente - key_enc: {client_session.keys['key_enc'].hex()[:32]}...")
    print(f"Servidor- key_enc: {server_session.keys['key_enc'].hex()[:32]}...")
    print(f"Claves de cifrado iguales: {client_session.keys['key_enc'] == server_session.keys['key_enc']}")
    
    print(f"Cliente - key_mac: {client_session.keys['key_mac'].hex()[:32]}...")
    print(f"Servidor- key_mac: {server_session.keys['key_mac'].hex()[:32]}...")
    print(f"Claves MAC iguales: {client_session.keys['key_mac'] == server_session.keys['key_mac']}")
    
    print(f"Cliente - nonce: {client_session.keys['nonce_base'].hex()}")
    print(f"Servidor- nonce: {server_session.keys['nonce_base'].hex()}")
    print(f"Nonces iguales: {client_session.keys['nonce_base'] == server_session.keys['nonce_base']}\n")
    
    # Verificar que todas las claves coincidan
    keys_match = (
        client_session.keys['key_enc'] == server_session.keys['key_enc'] and
        client_session.keys['key_mac'] == server_session.keys['key_mac'] and
        client_session.keys['nonce_base'] == server_session.keys['nonce_base']
    )
    
    if not keys_match:
        print("ERROR: Las claves no coinciden!")
        return False
    
    print("✅ Todas las claves coinciden correctamente\n")
    
    # Prueba de cifrado/descifrado
    test_message = {"accion": "listar_archivos", "timestamp": 1632345678}
    message_bytes = json.dumps(test_message).encode('utf-8')
    
    print("=== PRUEBA DE CIFRADO/DESCIFRADO ===")
    print(f"Mensaje original: {test_message}")
    
    # Cliente cifra
    encrypted = client_session.encrypt(message_bytes)
    print(f"Mensaje cifrado: {encrypted}")
    
    # Servidor descifra
    try:
        decrypted_bytes = server_session.decrypt(encrypted)
        decrypted_message = json.loads(decrypted_bytes.decode('utf-8'))
        print(f"Mensaje descifrado: {decrypted_message}")
        
        if decrypted_message == test_message:
            print("✅ Cifrado/descifrado funciona correctamente")
            return True
        else:
            print("ERROR: El mensaje descifrado no coincide")
            return False
            
    except Exception as e:
        print(f"ERROR en descifrado: {e}")
        return False

if __name__ == "__main__":
    success = test_key_derivation()
    if success:
        print("\n🎉 TODAS las pruebas pasaron correctamente")
        print("Las claves se sincronizan correctamente entre cliente y servidor")
    else:
        print("\n❌ Algunas pruebas fallaron")
        print("Hay problemas en la sincronización de claves")
    
    exit(0 if success else 1)