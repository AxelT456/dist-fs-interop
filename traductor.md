```mermaid
graph TD
    subgraph Sistema_Principal
        A[Solicitud Estándar<br>Acción: listar_archivos]
    end

    B[Traductor de Protocolos]

    subgraph Servidores_Propietarios
        C[Servidor Christian<br>Espera: type=list]
        D[Servidor Gus<br>Espera: action=list_all_files]
        E[Servidor Nombres<br>Espera: accion=listar_archivos]
    end

    A -->|Paso 2| B
    B -->|Paso 3: Driver Christian| C
    B -->|Paso 4: Driver Gus| D
    B -->|Paso 5: Driver Nombres| E

    style B fill:#fff3cd,stroke:#856404,stroke-width:2px;
