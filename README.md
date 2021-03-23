# p2p-file-sharing

### Summary
File transfer protocol on a P2P local network written in Python using the sockets library.
Host announces themselfs (and offered files) over the newtork via UDP broadcast, specifically sending one datagram every 30 seconds. Clients can also speed up this process by sending a special UDP broadcast datagram when running the script (works like a WiFi probe request)

Files are sended over TCP connections by all available peers that have the file that the "peer client" requested, each connection creates a new thread that will be responsible of downloading and writing into the memory a chunk of the requested file.


# Instructions

1 - Modify the file settings/config.py

2 - Run the file main.py

3 - To enter the commands to the system, establish a connection with telnet using port 2025 (by default)


# Commands
- **list**

  *List all files available to be downloaded, i.e. *
  *lists the files that other system users are sharing. *

- **offer < filename >**

  * Add the file <filename> to the list of shared files. *
  * All files that want to be shared must be in the *
  * shared folder that was set for the system. *

- **offering**

  * List all shared own files *

- **share**

  * Share all files found in shared folder *

- **get < fileid >**

  * Start downloading the file with id fileid <fileid>. When the *
  * download is completed the file is automatically shared to other peers. *
