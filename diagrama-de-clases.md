```mermaid
classDiagram
    class WebController {
        +app: Flask
        +catalog_manager: CatalogManager
        +file_handler: FileHandler
        +serve_pages()
        +handle_edits()
    }

    class MainServer {
        +catalog_manager: CatalogManager
        +file_handler: FileHandler
        +transport: ReliableTransport
        +session: SecureSession
        +run()
        +process_message()
    }

    class CatalogManager {
        -catalog: dict
        +publish_file(file_info)
        +find_file_owner(filename)
    }

    class FileHandler {
        -local_files: dict
        -cache: dict
        +get_file_content(filename)
        +update_file(filename, content, timestamp)
        +last_write_wins(local_ts, remote_ts)
    }

    class PeerConnector {
        -transport: ReliableTransport
        -session: SecureSession
        -translator: Translator
        +request_file(filename, owner)
        +send_update(filename, owner)
    }

    class Translator {
        -dns_drivers: list
        +resolve(peer_id)
    }

    class ReliableTransport {
        +send_data(data, destination)
        +listen()
    }

    class SecureSession {
        +encrypt(plaintext)
        +decrypt(ciphertext)
    }

    MainServer o-- CatalogManager
    MainServer o-- FileHandler
    MainServer o-- ReliableTransport
    MainServer o-- SecureSession
    WebController o-- MainServer
    PeerConnector o-- ReliableTransport
    PeerConnector o-- SecureSession
    PeerConnector o-- Translator
    ```
