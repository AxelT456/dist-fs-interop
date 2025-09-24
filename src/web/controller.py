# src/web/controller.py
import sys
import os
from flask import Flask, render_template, request, redirect, url_for, flash

# --- Configuración de Paths ---
# Agrega la raíz del proyecto para que Flask pueda encontrar 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
# --- Fin de Configuración de Paths ---

from src.client_logic import ClientLogic

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
    Página principal. Muestra el estado de la conexión y la lista de libros.
    """
    files = []
    # Si estamos conectados, pedimos la lista de archivos
    if client.is_connected:
        response = client.get_file_list()
        if response.get("status") == "ACK":
            files = response.get("archivos", [])
        else:
            flash(f"Error al listar archivos: {response.get('mensaje')}", 'danger')

    # Renderiza el template 'index.html' y le pasa las variables
    return render_template('index.html', is_connected=client.is_connected, files=files)

@app.route('/connect')
def connect():
    """
    Ruta para intentar conectar al sistema de archivos distribuido.
    """
    if not client.is_connected:
        success, message = client.connect_randomly()
        if success:
            flash(message, 'success') # Muestra un mensaje de éxito
        else:
            flash(message, 'danger') # Muestra un mensaje de error
    # Redirige al usuario de vuelta a la página principal
    return redirect(url_for('index'))

@app.route('/disconnect')
def disconnect():
    """
    Ruta para desconectar del sistema.
    """
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