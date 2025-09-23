```mermaid
sequenceDiagram
    participant S1 as Servidor 1 (Activo)
    participant S2 as Servidor 2 (Copia)
    participant DNS as DNS General

    loop Heartbeats
        S1->>DNS: Heartbeat (estoy vivo)
        S2->>DNS: Heartbeat (estoy vivo)
    end

    Note over S1: ❌ El Servidor 1 se desconecta

    DNS->>DNS: Detecta que no hay heartbeat de S1
    DNS->>S2: Consulta: ¿Aún tienes copia del Archivo A?
    S2-->>DNS: Respuesta: Sí, tengo el Archivo A

    Note over DNS: Reasigna la propiedad del Archivo A al Servidor 2
    DNS->>DNS: Actualiza Índice: Archivo A --> Servidor 2
