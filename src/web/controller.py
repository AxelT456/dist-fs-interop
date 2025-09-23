# /src/web/controller.py

from flask import Flask, render_template, request, redirect, url_for
import os

# --- ¡CAMBIO CLAVE AQUÍ! ---
# Le decimos a Flask dónde encontrar tus archivos HTML y CSS.
# Basado en tu imagen, están en la carpeta 'view' junto a este archivo.
view_folder = os.path.join(os.path.dirname(__file__), 'view')

# Le pasamos las rutas personalizadas a Flask.
app = Flask(__name__, template_folder=view_folder, static_folder=view_folder)


# --- Variables globales para acceder a la lógica de negocio ---
catalog_manager = None
file_handler = None

# --- Definición de Rutas Web ---

@app.route('/')
def index():
    """Página principal que muestra el catálogo de archivos."""
    # En un sistema real, aquí llamarías a tu lógica de negocio.
    # master_catalog = catalog_manager.get_master_catalog()
    master_catalog_ejemplo = {
        "LibroA.txt": {"server": "server-A"},
        "LibroB.pdf": {"server": "server-A"},
        "LibroC.docx": {"server": "server-B"}
    }
    return render_template('index.html', files=master_catalog_ejemplo)

@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_file(filename):
    """Página para ver y editar el contenido de un archivo."""
    if request.method == 'POST':
        new_content = request.form['content']
        print(f"-> Guardando nuevo contenido para {filename}...")
        # Lógica de guardado: file_handler.update_file(filename, new_content)
        return redirect(url_for('index'))

    print(f"-> Solicitando copia de {filename} para editar...")
    # Lógica de lectura: content = file_handler.get_file_copy(filename)
    content_ejemplo = f"Este es el contenido de ejemplo para el archivo {filename}."
    return render_template('edit_file.html', filename=filename, content=content_ejemplo)


def start_web_server(cat_manager_instance, file_handler_instance):
    """Función que el main_server llamará para iniciar el servidor web."""
    global catalog_manager, file_handler
    catalog_manager = cat_manager_instance
    file_handler = file_handler_instance
    
    print("🚀 Iniciando servidor WEB en http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)