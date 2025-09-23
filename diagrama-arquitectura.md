```mermaid
graph TD
    subgraph Red_de_Servidores_P2P
        S1[Servidor 1: Archivos A, B]
        S2[Servidor 2: Archivos C, D]
        SM[Servidor Marco: Archivos E, F]
    end

    DNS[DNS General: Índice Global]
    Cliente[Cliente Distribuido]

    S1 -->|1. Registro y Heartbeat| DNS
    S2 -->|1. Registro y Heartbeat| DNS
    SM -->|1. Registro y Heartbeat| DNS

    Cliente -->|2. Conexión Segura| S1
    S1 -->|3. Consulta Archivo F| DNS
    DNS -->|4. Responde: F en Servidor Marco| S1
    S1 -->|5. Petición P2P Archivo F| SM
    SM -->|6. Envía Archivo F| S1
    S1 -->|7. Entrega Archivo F| Cliente

    style DNS fill:#d4edda,stroke:#155724,stroke-width:2px
    style Cliente fill:#cce5ff,stroke:#004085,stroke-width:2px
