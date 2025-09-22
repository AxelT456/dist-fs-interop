import os
import json
import threading
import time
import socket
import logging
import sys

CONFIG_FILE = 'config.json'
LOG_FILE = 'server.log'
UDP_IP = "127.0.0.2"  
UDP_PORT = 50000
UPDATE_INTERVAL_SECONDS = 300  #segundos
SERVER_IP="127.0.0.3"
SERVER_PORT=5002

# --- Variables Globales ---
lista_archivos = []
lista_archivos_lock = threading.Lock()
folder_path = ""

# --- Configuración del Logging ---
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

# --- Funciones de Gestión de Archivos y Configuración ---
def cargar_configuracion():
    """Carga la configuración y la ruta de la carpeta desde el archivo JSON."""
    global folder_path
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                # La configuración contiene la ruta y la lista de archivos
                folder_path = data.get('folder_path', '')
                return data.get('files', [])
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"No se pudo leer el archivo de configuración: {e}")
            return []
    return []

def guardar_configuracion():
    """Guarda la lista de archivos actual y la ruta en el archivo JSON."""
    with lista_archivos_lock:
        try:
            with open(CONFIG_FILE, 'w') as f:
                # Guardamos tanto la ruta como la lista de archivos
                config_data = {
                    'folder_path': folder_path,
                    'files': lista_archivos
                }
                json.dump(config_data, f, indent=4)
            logging.info("Configuración guardada exitosamente en config.json")
        except IOError as e:
            logging.error(f"Error al guardar la configuración: {e}")

def escanear_y_actualizar(primera_vez=False):
    """
    Escanea la carpeta, compara con la lista en memoria y actualiza.
    Pregunta al usuario sobre nuevos archivos.
    """
    global lista_archivos
    logging.info(f"Iniciando escaneo de la carpeta: {folder_path}")
    
    try:
        archivos_en_disco = {f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))}
    except FileNotFoundError:
        logging.error(f"La carpeta '{folder_path}' no fue encontrada. El hilo de actualización se detendrá.")
        return # Salir si la carpeta no existe

    # Usamos un lock para garantizar la consistencia de los datos
    with lista_archivos_lock:
        archivos_conocidos = {f['nombre_archivo'] for f in lista_archivos}
        
        # --- Detección de archivos nuevos ---
        archivos_nuevos = archivos_en_disco - archivos_conocidos
        if archivos_nuevos:
            logging.info(f"Archivos nuevos detectados: {', '.join(archivos_nuevos)}")
            for archivo in archivos_nuevos:
                nombre, extension = os.path.splitext(archivo)
                
                publicar = input(f"  -> Se encontró '{archivo}'. ¿Desea publicarlo? (s/n): ").lower()
                if publicar == 's':
                    while True:
                        try:
                            ttl = int(input(f"     Ingrese el TTL en segundos para '{archivo}': "))
                            break
                        except ValueError:
                            print("     Por favor, ingrese un número entero válido.")
                    
                    nuevo_objeto = {
                        "nombre_archivo": archivo,
                        "extension": extension,
                        "publicado": True,
                        "ttl": ttl
                    }
                    lista_archivos.append(nuevo_objeto)
                    logging.warning(f"ARCHIVO AÑADIDO: '{archivo}' ha sido añadido a la lista y publicado.")
                else:
                    nuevo_objeto = {
                        "nombre_archivo": archivo,
                        "extension": extension,
                        "publicado": False,
                        "ttl": 0
                    }
                    lista_archivos.append(nuevo_objeto)
                    logging.info(f"ARCHIVO REGISTRADO: '{archivo}' ha sido añadido a la lista como no publicado.")

        # --- Detección de archivos eliminados ---
        archivos_eliminados = archivos_conocidos - archivos_en_disco
        if archivos_eliminados:
            # Reconstruimos la lista excluyendo los archivos eliminados
            lista_archivos[:] = [f for f in lista_archivos if f['nombre_archivo'] not in archivos_eliminados]
            for archivo in archivos_eliminados:
                logging.warning(f"ARCHIVO ELIMINADO: '{archivo}' fue eliminado de la carpeta y de la lista.")

    # Guardar cambios si hubo alguna modificación
    if archivos_nuevos or archivos_eliminados or primera_vez:
        guardar_configuracion()

# --- Lógica de los Hilos ---
def hilo_actualizador():
    """Función que se ejecuta en un hilo para actualizar la lista periódicamente."""
    while True:
        time.sleep(UPDATE_INTERVAL_SECONDS)
        escanear_y_actualizar()

def hilo_servidor_udp():
    """Función que se ejecuta en un hilo para escuchar peticiones UDP."""
    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    servidor_socket.bind((UDP_IP, UDP_PORT))
    logging.info(f"Servidor UDP escuchando en el puerto {UDP_PORT}")

    while True:
        try:
            data, addr = servidor_socket.recvfrom(1024) # Buffer de 1024 bytes
            peticion = json.loads(data.decode('utf-8'))
            logging.info(f"Petición recibida de {addr}: {peticion}")

            if peticion.get('accion') == 'consultar':
                nombre_buscado = peticion.get('nombre_archivo')
                respuesta_obj = None

                with lista_archivos_lock:
                    # Buscamos el archivo en la lista
                    for archivo in lista_archivos:
                        if archivo['nombre_archivo'] == nombre_buscado and archivo['publicado']:
                            respuesta_obj = {
                            "status": "ACK",
                            "nombre_archivo": archivo['nombre_archivo'],
                            "ttl": archivo['ttl'],
                            "ip": SERVER_IP,        # IP del servidor de archivos
                            "puerto": SERVER_PORT            # Puerto donde escucha PeerConnector
                        }
                            break
                
                if not respuesta_obj:
                    respuesta_obj = {
                        "status": "NACK",
                        "mensaje": "Archivo no encontrado o no publicado.",
                        "ip": SERVER_IP,        # IP del servidor de archivos
                        "puerto": SERVER_PORT            # Puerto donde escucha PeerConnector
                    }
                
                respuesta_json = json.dumps(respuesta_obj).encode('utf-8')
                servidor_socket.sendto(respuesta_json, addr)
            elif peticion.get("accion") == "listar_archivos":
                # NUEVA FUNCIONALIDAD: Listar todos los archivos
                with lista_archivos_lock:
                    respuesta_obj = {
                        "status": "ACK",
                        "archivos": lista_archivos,
                        "total": len(lista_archivos),
                        "ip": SERVER_IP,        # IP del servidor de archivos
                        "puerto": SERVER_PORT            # Puerto donde escucha PeerConnector
                    }
                
                respuesta_json = json.dumps(respuesta_obj, default=str).encode('utf-8')
                servidor_socket.sendto(respuesta_json, addr)
                logging.info(f"Enviada lista de {len(lista_archivos)} archivos a {addr}")
                
        except (json.JSONDecodeError, UnicodeDecodeError):
            logging.error(f"Error al decodificar la petición de {addr}.")
        except Exception as e:
            logging.error(f"Ocurrió un error en el servidor UDP: {e}")

# --- Función Principal ---
def main():
    """Función principal que orquesta el inicio del servidor."""
    global lista_archivos, folder_path
    setup_logging()
    logging.info("Iniciando el servidor de nombres de recursos...")

    # Cargar configuración existente o inicializar
    lista_archivos = cargar_configuracion()
    
    if not folder_path or not os.path.isdir(folder_path):
        logging.warning("No se encontró una ruta válida en la configuración.")
        while True:
            folder_path = input("Por favor, introduce la ruta completa de la carpeta a monitorear: ")
            if os.path.isdir(folder_path):
                break
            else:
                print("La ruta no es válida o no es un directorio. Inténtalo de nuevo.")

    # Realizar el primer escaneo y actualización al arrancar
    escanear_y_actualizar(primera_vez=True)
    
    # Iniciar el hilo que actualiza la carpeta periódicamente
    hilo_updater = threading.Thread(target=hilo_actualizador, name="ActualizadorCarpeta", daemon=True)
    hilo_updater.start()

    # Iniciar el hilo del servidor UDP
    hilo_udp = threading.Thread(target=hilo_servidor_udp, name="ServidorUDP", daemon=True)
    hilo_udp.start()

    print("\n" + "="*50)
    print("Servidor de Nombres iniciado correctamente.")
    print(f"Monitoreando la carpeta: {folder_path}")
    print("Presiona Ctrl+C para detener el servidor.")
    print("IP : ",UDP_IP)
    print("PORT : ",UDP_PORT)
    print("="*50 + "\n")

    try:
        # Mantenemos el hilo principal vivo para que los hilos daemon puedan correr
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Deteniendo el servidor...")
        print("\nServidor detenido por el usuario. ¡Adiós!")

if __name__ == '__main__':
    main()