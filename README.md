# p2p-file-sharing

### Resumen
Protocolo de transferencia de archivos en una red local P2P escrito en Python utilizando la librería sockets.

- Cada 30 segundos se ofrecen los archivos publicados por el usuario al resto de los peers mediante anuncios UDP.
- Al descargar un archivo se crea una conexión TCP con cada uno de los seeders posibles, paralelizando la descarga del archivo.

# Instrucciones

1 - Modificar el archivo  settings/config.py

2 - Ejecutar el archivo main.py

3 - Para ingresar los comandos al sistema, establecer conexión con telnet utilizando el puerto 2025 (por defecto)


# Comandos
- **list**

  *Lista todos los archivos disponibles para ser descargados, es decir,*
  *lista los archivos que otros usuarios del sistema están compartiendo.*

- **offer < filename >**

  *Agrega el archivo < filename > a la lista de archivos compartidos.*
  *Todos los archivos que quieren ser compartidos deben estar en la*
  *carpeta compartida que fue establecida para el sistema).*

- **offering**

  *Lista todos los archivos propios compartidos*

- **share**

  *Comparte todos los archivos que se encuentran en la carpeta*
  *compartida.*

- **get < fileid >**

  *Comienza la descarga del archivo < fileid > . Cuando finaliza la*
  *descarga el archivo se comparte automáticamente.*
