# /tests/init_data.py
import os
import json

def inicializar_datos():
    # Crear estructura de directorios
    base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    servidor1_dir = os.path.join(base_dir, 'servidor1')
    servidor2_dir = os.path.join(base_dir, 'servidor2')
    
    os.makedirs(servidor1_dir, exist_ok=True)
    os.makedirs(servidor2_dir, exist_ok=True)
    
    # Crear libros para servidor1
    with open(os.path.join(servidor1_dir, 'LibroA.txt'), 'w') as f:
        f.write("Contenido del Libro A\nEste es un libro de ejemplo para el servidor 1.")
    
    with open(os.path.join(servidor1_dir, 'LibroB.pdf'), 'w') as f:
        f.write("Contenido PDF del Libro B\nEjemplo de formato PDF.")
    
    # Crear libros para servidor2
    with open(os.path.join(servidor2_dir, 'LibroC.docx'), 'w') as f:
        f.write("Contenido DOCX del Libro C\nEjemplo de documento Word.")
    
    # Crear metadata
    metadata_servidor1 = {
        "LibroA": {
            "formato": "txt",
            "tamaño": 65,
            "descripcion": "Libro de ejemplo A",
            "autor": "Autor Desconocido"
        },
        "LibroB": {
            "formato": "pdf", 
            "tamaño": 45,
            "descripcion": "Libro de ejemplo B",
            "autor": "Otro Autor"
        }
    }
    
    metadata_servidor2 = {
        "LibroC": {
            "formato": "docx",
            "tamaño": 55,
            "descripcion": "Libro de ejemplo C",
            "autor": "Tercer Autor"
        }
    }
    
    with open(os.path.join(servidor1_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata_servidor1, f, indent=2)
    
    with open(os.path.join(servidor2_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata_servidor2, f, indent=2)
    
    print("✅ Estructura de datos inicializada")
    print("📁 Directorio data/ creado con archivos de ejemplo")

if __name__ == "__main__":
    inicializar_datos()