# src/web/controller.py (Versión Reestructurada)
import sys
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.client_logic import ClientLogic, DNS_SERVERS

app = Flask(__name__, template_folder='view', static_folder='static')
app.secret_key = 'una-clave-secreta-muy-segura'
client = ClientLogic()

@app.context_processor
def inject_dns_servers():
    return dict(dns_servers=DNS_SERVERS)

@app.route('/')
def index():
    # La página principal ahora solo muestra el estado, no carga archivos
    return render_template('index.html', is_connected=client.is_connected)

@app.route('/list_files')
def list_files():
    if not client.is_connected:
        flash('Necesitas estar conectado para listar los libros.', 'warning')
        return redirect(url_for('index'))

    # 1. Obtenemos listas de archivos y bloqueos
    active_locks = client.get_all_locks().get("locks", {})
    file_response = client.get_file_list()

    if file_response.get("status") != "ACK":
        flash(f"Error al listar archivos: {file_response.get('mensaje')}", 'danger')
        return render_template('index.html', is_connected=client.is_connected)

    # 2. Identificamos el servidor actual para la agrupación
    current_server_id = None
    for dns in DNS_SERVERS:
        if client.dns_info and dns['id'] == client.dns_info['id']:
            current_server_id = dns['server_id']
            break

    # 3. Agrupamos los archivos en locales y externos
    local_files = []
    external_files = []
    
    for file_info in file_response.get("archivos", []):
        fname = file_info.get("nombre_archivo")
        file_info["is_locked"] = fname in active_locks
        if file_info["is_locked"]:
            file_info["locked_by"] = active_locks[fname]
        
        if file_info.get("servidor_principal") == current_server_id:
            local_files.append(file_info)
        else:
            external_files.append(file_info)

    return render_template('index.html', 
                           is_connected=client.is_connected, 
                           local_files=local_files,
                           external_files=external_files,
                           current_server_id=current_server_id)

@app.route('/search', methods=['POST'])
def search_file():
    if not client.is_connected:
        flash('Necesitas estar conectado para buscar.', 'warning')
        return redirect(url_for('index'))

    filename = request.form.get('filename')
    if not filename:
        flash('Por favor, introduce un nombre de archivo.', 'warning')
        return redirect(url_for('index'))

    response = client.get_file_info(filename)
    if response.get("status") == "ACK":
        msg = f"✅ '{filename}' SÍ EXISTE en el servidor {response.get('server_id')}."
        flash(msg, 'success')
    else:
        msg = f"❌ '{filename}' NO FUE ENCONTRADO en el sistema."
        flash(msg, 'danger')
    # Volvemos a la página principal después de la búsqueda
    return redirect(url_for('index'))

# --- EL RESTO DE RUTAS SE MANTIENEN IGUAL ---
# (connect, disconnect, view_file, edit_file, save_file, cancel_edit)
# La única diferencia es que al final redirigen a `index` o `list_files`
# para una mejor experiencia de usuario.

@app.route('/connect', methods=['POST'])
def connect():
    if client.is_connected: return redirect(url_for('index'))
    dns_choice = request.form.get('dns_choice')
    success, message = client.connect_to_specific_dns(dns_choice) if dns_choice != 'random' else client.connect_randomly()
    if success: flash(message, 'success')
    else: flash(message, 'danger')
    return redirect(url_for('index'))

@app.route('/disconnect', methods=['POST'])
def disconnect():
    # Limpiar cualquier sesión de edición sin liberar bloqueos
    # (Los bloqueos son manejados por el servidor, no por el cliente)
    session.pop('editing_file', None)
    client.disconnect()
    flash('Desconectado del servidor.', 'info')
    return redirect(url_for('index'))

@app.route('/view/<filename>')
def view_file(filename):
    if not client.is_connected: return redirect(url_for('index'))
    response = client.read_file(filename)
    if response.get("status") != "EXITO":
        flash(f"No se pudo leer: {response.get('mensaje')}", "danger")
        return redirect(url_for('list_files'))
    return render_template('view_file.html', filename=filename, content=response.get("contenido", ""))


# En src/web/controller.py

@app.route('/edit/<filename>', methods=['GET'])
def edit_file(filename):
    if not client.is_connected:
        flash('Necesitas estar conectado para editar.', 'warning')
        return redirect(url_for('index'))

    # NOTE: NO solicitamos bloqueo aquí. El bloqueo será manejado completamente por el servidor
    # al momento de escribir. Esto evita conflictos de bloqueo doble.
    
    # 1. Leemos el contenido del archivo
    read_response = client.read_file(filename)
    content = ""
    if read_response.get("status") == "EXITO":
        content = read_response.get("contenido", "")
    else:
        flash(f"Advertencia: No se pudo cargar el contenido. {read_response.get('mensaje', '')}", 'warning')

    # 2. Guardamos el nombre del archivo en sesión para validar en save_file
    session['editing_file'] = filename
    
    # 3. Renderizamos la plantilla de edición
    return render_template('edit_file.html', filename=filename, content=content)

@app.route('/save', methods=['POST'])
def save_file():
    if not client.is_connected:
        return redirect(url_for('index'))
    
    filename = request.form.get('filename')
    content = request.form.get('content', '')
    
    # Validar que el usuario esté editando este archivo
    if 'editing_file' not in session or session['editing_file'] != filename:
        flash('Error: Intentando guardar un archivo que no estabas editando.', 'danger')
        return redirect(url_for('list_files'))
    
    # El servidor maneja todo el bloqueo internamente al escribir
    # No necesitamos bloqueos del lado del cliente
    response = client.write_file(filename, content)
    
    if response.get("status") == "EXITO":
        flash(f"✅ '{filename}' guardado con éxito.", 'success')
    else:
        flash(f"❌ Error al guardar: {response.get('mensaje', 'Error desconocido')}", 'danger')
    
    # Limpiar la sesión de edición
    session.pop('editing_file', None)
    return redirect(url_for('list_files'))

@app.route('/cancel_edit/<filename>', methods=['GET', 'POST'])
def cancel_edit(filename):
    # Simplemente limpiar la sesión de edición
    # No hay bloqueo del cliente que liberar (es manejado por el servidor)
    if 'editing_file' in session and session['editing_file'] == filename:
        session.pop('editing_file', None)
        if request.method == 'GET':
            flash(f"Edición de '{filename}' cancelada.", 'info')
    
    if request.method == 'GET':
        return redirect(url_for('list_files'))
    else:
        # Para la petición beacon, devolvemos una respuesta vacía
        return ('', 204)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)