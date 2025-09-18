### Diagrama de Casos de Uso

```mermaid
graph TD
    subgraph Sistema Distribuido de Archivos
        UC1[Listar Archivos]
        UC2[Ver y Editar Archivo]
        UC3[Guardar Cambios]
        UC4[Consultar Ubicación de Archivo]
        UC5[Pedir Copia de Archivo]
        UC6[Propagar Actualización]
    end

    A[Usuario] --> UC1
    A[Usuario] --> UC2
    A[Usuario] --> UC3
    UC3 -->|Desencadena| UC6
    B[Servidor_Par] --> UC4
    B[Servidor_Par] --> UC5
    B[Servidor_Par] --> UC6

    style A fill:#bbf,stroke:#333,stroke-width:2px
    style B fill:#f9f,stroke:#333,stroke-width:2px
```
