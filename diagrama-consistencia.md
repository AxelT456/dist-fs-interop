```mermaid
sequenceDiagram
    participant C as Cliente
    participant S1 as Servidor 1
    participant DNS as DNS General
    participant SO as Servidor Original (dueño del archivo)

    C->>S1: Quiero editar "archivo.txt"
    S1->>DNS: Solicitar Checkout de "archivo.txt"
    DNS->>SO: (Reenvía petición)
    SO-->>DNS: OK, aquí está el contenido
    DNS-->>S1: **Checkout exitoso**, contenido recibido
    Note over S1: Crea copia temporal y la bloquea
    S1-->>C: Puedes editar el archivo

    C->>S1: Envía nuevo contenido (Check-in)
    S1->>DNS: Solicitar Check-in de "archivo.txt"
    DNS->>SO: Actualiza el archivo con el nuevo contenido
    SO-->>DNS: Escritura exitosa
    DNS-->>S1: **Check-in exitoso**
    Note over S1: Destruye copia temporal y desbloquea
    S1-->>C: Cambios guardados correctamente
