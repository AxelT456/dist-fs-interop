```mermaid
graph TD
    subgraph Sistema Distribuido de Archivos
        UC1(Listar Archivos)
        UC2(Ver y Editar Archivo)
        UC3(Guardar Cambios)
        UC4(Consultar Ubicación de Archivo)
        UC5(Pedir Copia de Archivo)
        UC6(Propagar Actualización)
    end

    Usuario --|> UC1
    Usuario --|> UC2
    Usuario --|> UC3

    UC3 -- Desencadena --> UC6

    Servidor_Par --|> UC4
    Servidor_Par --|> UC5
    Servidor_Par --|> UC6

    style Usuario fill:#bbf,stroke:#333,stroke-width:2px
    style Servidor_Par fill:#f9f,stroke:#333,stroke-width:2px
    ```
