# dist-fs-interop
Un sistema de archivos distribuido peer-to-peer con interoperabilidad entre múltiples servicios DNS personalizados, implementado en Python.
//
Para la parte del test se ocupa hacer 
python initi_data.py                    //crea archivos simulados(no tan simulados)
python test_dns_server.py               //inicializa lo que serian los dns nuestros (dns por server)
python test_dns_server.py --server1     //server que compartiriamos creo
python test_dns_server2.py --server2
python test_dns_client.py               //inicializa un cliente que se conecta aleatoriamente a un server

El flujo de esto es 
Cliente -> DNS
DNS -> "mira ip's"
DNS -> regresa ip del server -> cliente
Cliente -> Conecta con server -> Server
Lo implementado fue el translator.py que lo que hace es ser un
traductor para los diferentes DNS, hace funciones que segun como sea la entrada que pide
el DNS acomoda para que regrese de esa forma 
peer_conector parecida a la parte de tranport.py hace la conexion con el cliente o server dependiendo de quien se conecte a donde
los test que pueden ayudar a haer el main, casos aplicados del uso de esas dos cosas
pide la ip a traves de que sabe un nombre, se conecte, hace sus cosas y poco mas
eso si, toca checar el como pide las cosas al server, mas que nada los metodos que faltan
tiene dentro un query <libro> que lo que hace es buscar el libro en el server actual y en otros servers
esto a traves de que el server se conecta con otros