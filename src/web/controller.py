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
    if 'locked_file' in session and session['locked_file']:
        client.release_lock(session['locked_file'])
        session.pop('locked_file', None)
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

    # 1. Intentamos solicitar el bloqueo
    lock_response = client.request_lock(filename)

    if lock_response.get("status") != "BLOQUEO_CONCEDIDO":
        # --- NUEVA LÓGICA INTELIGENTE ---
        # Si el bloqueo falla, comprobamos por qué
        check_response = client.check_lock_status(filename)
        
        # Identificamos nuestro propio server_id para la comparación
        current_server_id = next((d['server_id'] for d in DNS_SERVERS if client.dns_info and d['id'] == client.dns_info['id']), None)

        # Si el archivo está bloqueado, pero por NOSOTROS, permitimos la entrada
        if check_response.get("bloqueado") and check_response.get("bloqueado_por") == current_server_id:
            flash(f"Reingresando a la edición de '{filename}', que ya tenías bloqueado.", "info")
            # Continuamos al paso 3
        else:
            # Si está bloqueado por otro, mostramos el error y redirigimos
            flash(f"No se puede editar: {lock_response.get('mensaje', 'El archivo está bloqueado por otro usuario.')}", 'danger')
            return redirect(url_for('list_files'))
    else:
        # Si el bloqueo fue exitoso la primera vez, lo guardamos en la sesión
        session['locked_file'] = filename
        flash(f"Has bloqueado '{filename}' para edición.", 'info')

    # 3. Leemos el contenido del archivo (este código ahora se ejecuta en ambos casos)
    read_response = client.read_file(filename)
    content = ""
    if read_response.get("status") == "EXITO":
        content = read_response.get("contenido", "")
    else:
        flash(f"Advertencia: No se pudo cargar el contenido previo. {read_response.get('mensaje', '')}", 'warning')

    # 4. Renderizamos la plantilla de edición
    return render_template('edit_file.html', filename=filename, content=content)

@app.route('/save', methods=['POST'])
def save_file():
    if not client.is_connected or 'locked_file' not in session:
        return redirect(url_for('index'))
    filename = request.form['filename']
    content = request.form['content']
    if session['locked_file'] != filename:
        flash('Error: Intentando guardar un archivo para el que no tienes bloqueo.', 'danger')
        return redirect(url_for('list_files'))
    response = client.write_file(filename, content)
    if response.get("status") == "EXITO":
        flash(f"'{filename}' guardado con éxito.", 'success')
    else:
        flash(f"Error al guardar: {response.get('mensaje')}", 'danger')
    client.release_lock(filename)
    session.pop('locked_file', None)
    return redirect(url_for('list_files'))

@app.route('/cancel_edit/<filename>', methods=['GET', 'POST'])
def cancel_edit(filename):
    # El resto de la función no necesita cambios
    if 'locked_file' in session and session['locked_file'] == filename:
        client.release_lock(filename)
        session.pop('locked_file', None)
        # No mostramos mensaje flash en la petición beacon para no generar errores
        if request.method == 'GET':
            flash(f"Edición de '{filename}' cancelada y bloqueo liberado.", 'info')
    
    if request.method == 'GET':
        return redirect(url_for('list_files'))
    else:
        # Para la petición beacon, devolvemos una respuesta vacía
        return ('', 204)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)