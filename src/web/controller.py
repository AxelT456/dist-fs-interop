# src/web/controller.py
import sys
import os
from flask import Flask, render_template, request, redirect, url_for, flash

# --- Configuración de Paths ---
# Agrega la raíz del proyecto para que Flask pueda encontrar 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
# --- Fin de Configuración de Paths ---

from src.client_logic import ClientLogic, DNS_SERVERS

# Inicializa la aplicación Flask
# Le decimos que las plantillas HTML están en la carpeta 'view'
app = Flask(__name__, template_folder='view')
# Se necesita una 'secret_key' para poder mostrar mensajes flash (opcional pero bueno)
app.secret_key = 'una-clave-secreta-muy-segura'

# --- Instancia Única del Cliente ---
# Creamos UNA SOLA instancia de nuestra lógica de cliente para toda la aplicación web.
# Esto mantiene el estado de la conexión.
client = ClientLogic()

# --- Definición de Rutas (las URLs de nuestra app) ---

@app.route('/')
def index():
    """
    Página principal. Muestra el estado de la conexión y la lista de libros,
    ahora agrupados por servidor de origen.
    """
    files_grouped = {} # Usaremos este diccionario para los archivos agrupados
    local_server_id = None

    if client.is_connected:
        # Obtenemos el ID del servidor al que estamos conectados para saber cuáles son "locales"
        # Asumimos que client.dns_info y client.server_info están disponibles tras la conexión
        if client.dns_info:
            # Buscamos el server_id correspondiente en la configuración de DNS
            for dns in DNS_SERVERS:
                if dns['id'] == client.dns_info['id']:
                    # Hacemos una búsqueda inversa para encontrar el server_id lógico
                    if dns.get('server_ip') == client.server_info[0] and dns.get('server_port') == client.server_info[1]:
                         local_server_id = dns.get('id').replace('DNS_', 'SERVER_') # Ej: 'DNS_GUS' -> 'SERVER_GUS'
                         if local_server_id == 'DNS1': local_server_id = 'SERVER1'
                         if local_server_id == 'DNS2': local_server_id = 'SERVER2'

        response = client.get_file_list()
        if response.get("status") == "ACK":
            files = response.get("archivos", [])
            
            # --- Lógica de Agrupación ---
            for file_info in files:
                server_id = file_info.get("servidor_principal", "Desconocido")
                
                # Si el archivo pertenece al servidor local, lo agrupamos en "Locales"
                if server_id == local_server_id:
                    group_key = "Locales"
                else:
                    group_key = f"Remotos ({server_id})"

                if group_key not in files_grouped:
                    files_grouped[group_key] = []
                
                files_grouped[group_key].append(file_info)

        else:
            flash(f"Error al listar archivos: {response.get('mensaje')}", 'danger')

    # Ordenamos los grupos para que "Locales" aparezca primero si existe
    sorted_files_grouped = dict(sorted(files_grouped.items(), key=lambda item: item[0] != 'Locales'))

    # Renderiza el template y le pasa el diccionario de archivos agrupados
    return render_template('index.html', 
                           is_connected=client.is_connected, 
                           files_grouped=sorted_files_grouped,
                           local_server_id=local_server_id)

@app.route('/connect', methods=['POST']) # <--- AÑADIR methods=['POST']
def connect():
    """
    Ruta para intentar conectar al sistema de archivos distribuido.
    Ahora solo responde a POST.
    """
    # ... (el interior de la función no cambia)
    if not client.is_connected:
        success, message = client.connect_randomly()
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    return redirect(url_for('index'))

@app.route('/disconnect', methods=['POST']) # <--- AÑADIR methods=['POST']
def disconnect():
    """
    Ruta para desconectar del sistema.
    Ahora solo responde a POST.
    """
    # ... (el interior de la función no cambia)
    client.disconnect()
    flash('Desconectado del servidor.', 'info')
    return redirect(url_for('index'))

@app.route('/edit/<filename>')
def edit_file(filename):
    """
    Página para ver y editar el contenido de un libro.
    """
    if not client.is_connected:
        flash('Necesitas estar conectado para editar un libro.', 'warning')
        return redirect(url_for('index'))

    content = ""
    response = client.read_file(filename)
    if response.get("status") == "EXITO":
        content = response.get("contenido", "")
    else:
        # Si el libro no existe, la 'lectura' falla, lo cual está bien.
        # Simplemente empezamos con el contenido vacío.
        flash(f"Creando nuevo libro: '{filename}'", 'info')

    return render_template('edit_file.html', filename=filename, content=content)

@app.route('/save', methods=['POST'])
def save_file():
    """
    Ruta que se activa cuando se envía el formulario de guardado.
    No es una página, sino una acción.
    """
    if not client.is_connected:
        flash('Necesitas estar conectado para guardar cambios.', 'warning')
        return redirect(url_for('index'))

    # Obtenemos los datos enviados desde el formulario HTML
    filename = request.form['filename']
    content = request.form['content']

    response = client.write_file(filename, content)
    if response.get("status") == "EXITO":
        flash(f"Libro '{filename}' guardado con éxito.", 'success')
    else:
        flash(f"Error al guardar '{filename}': {response.get('mensaje')}", 'danger')

    return redirect(url_for('index'))


# --- Punto de Entrada para Ejecutar el Servidor Web ---
if __name__ == '__main__':
    # debug=True hace que el servidor se reinicie automáticamente cuando guardas cambios en el código.
    app.run(host='0.0.0.0', port=5001, debug=True)