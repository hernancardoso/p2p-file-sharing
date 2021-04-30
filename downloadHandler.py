import socket
import time
import threading
import sys
import lib.common as utils
import lib.variables as variables
import settings.config as config

serverSocket = ""
threadError = {}


def init():
    global serverSocket

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind((config.data["ip"], config.data["tcp_port"]))
    serverSocket.listen()
    print("TCP socket started")

    while True:
        print("Waiting for download request...")
        connectionSock, addr = serverSocket.accept()
        # A new thread is created for each download request
        threading.Thread(target=serveClient, args=(connectionSock, addr,),).start()


def serveClient(clientSock, addr):
    print("New download request from " + addr[0])

    read, remaining = utils.read_line(clientSock, "")
    if read == "DOWNLOAD":

        md5Code, remaining = utils.read_line(clientSock, remaining)
        if md5Code == "CLOSED": return False

        reqStart, remaining = utils.read_line(clientSock, remaining)
        if reqStart == "CLOSED": return False

        reqSize, remaining = utils.read_line(clientSock, remaining)
        if reqSize == "CLOSED": return False

        if md5Code not in variables.myFiles:
            # The requested file could not be found on this device
            clientSock.sendall("DOWNLOAD FAILURE\nMISSING\n".encode())
            return False

        if (
            not reqSize.isnumeric()
            or not reqStart.isnumeric()
            or int(reqStart) > int(variables.myFiles[md5Code]["fileSize"])
        ):
            clientSock.sendall("DOWNLOAD FAILURE\nBAD REQUEST\n".encode())
            print("Error 1 - Bad request from client.")
            return False

        if int(reqStart) + int(reqSize) > int(variables.myFiles[md5Code]["fileSize"]):
            clientSock.sendall("DOWNLOAD FAILURE\nBAD REQUEST\n".encode())
            print("Error 2 - Offset + requested size exceeds the original file size")
            return False

        f = open(config.data["shared_folder"] + "\\" + variables.myFiles[md5Code]["fileName"], "rb")
        f.seek(int(reqStart))

        buffer = "DOWNLOAD OK\n".encode()
        buffer += f.read(int(reqSize))
        print("Sending " + str(sys.getsizeof(buffer)) + " bytes")
        clientSock.sendall(buffer)

        f.close()

    clientSock.shutdown(socket.SHUT_RDWR)
    clientSock.close()


def startDownload(md5Code):
    fileSize = int(variables.availableFiles[md5Code]["fileSize"])
    timeNow = int(round(time.time() * 1000))

    # Filter servers and get only the ones that "still alive"
    variables.availableFiles[md5Code]["servers"] = { k: v for (k, v) in variables.availableFiles[md5Code]["servers"].items() if timeNow - v <= 90000 }

    if len(variables.availableFiles[md5Code]["servers"]) == 0: #There are no servers for that file
        #If there are no servers to download the file, then the file should not be listed as available
        variables.availableFiles = {k: v for (k, v) in variables.availableFiles.items() if k != md5Code}
        variables.errorDownloading = "The requested file is no longer available"
        return

    # shortcut for availableServers
    availableServers = variables.availableFiles[md5Code]["servers"]
    totalServers = len(availableServers)

    # The chunks size is divided by the number of available server
    chunkSize = int(fileSize / totalServers)
 
    # for each available server a new thread is created and stored in this array (t)
    # this will be used later to do a fork-join of the threads
    t = []
    
    # an index to iterate over t[] array
    i = 0  

    # Index of the actualServer to which i'm requesting the chunk
    actualServer = 0
    for ip in availableServers:
        startingByte = chunkSize * actualServer

    
        # if fileSize is 5 bytes and 2 servers are available 5/2 = 2 bytes per server, so 1 byte is missing
        # the remaining of the division will be charged to the last server on the available lsit
        if actualServer == totalServers - 1:
            chunkSize += fileSize % totalServers

        t[i] = threading.Thread(target=downloadChunk, args=(ip, md5Code, startingByte, chunkSize))
        t[i].start()
        print("Chunk requested to " + ip + "\n")
        
        i += 1
        actualServer += 1

    # Wait for all threads to end
    for i in t:
        t[i].join()


def downloadChunk(ip, md5Code, reqByte, reqSize):
    global threadError

    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.settimeout(8)

    try:
        clientSocket.connect((ip, config.data["tcp_port"]))
    except:
        variables.errorDownloading = "Download failure, a server has disconnected, try again"

        del variables.availableFiles[md5Code]["servers"][ip]
        if len(variables.availableFiles[md5Code]["servers"]) == 0:
            del variables.availableFiles[md5Code]
        return

    print("Connected to " + ip)

    request = "DOWNLOAD\n" + md5Code + "\n" + str(reqByte) + "\n" + str(reqSize) + "\n"
    clientSocket.sendall(request.encode())
    
    fileName = variables.availableFiles[md5Code]["fileNames"][0]
    downloadedSize = 0

    f = open(config.data["shared_folder"] + "\\" + fileName, "wb+")
    f.seek(reqByte)  # seek the pointer to start writing in starting byte

    # Repeat until header of DOWNLOAD PROTOCOL is obtained
    answer = clientSocket.recv(config.data["tcp_rcv_pkt_max_size"])
    while len(answer) < 12:
        try:
            answer += clientSocket.recv(config.data["tcp_rcv_pkt_max_size"])
        except:
            variables.errorDownloading = "Download failure, a server has disconnected, try again"
            f.close()
            clientSocket.close()
            return

    if answer[:12].decode().find("DOWNLOAD OK\n") != -1:
        answer = answer[12:]
        downloadedSize += len(answer)
        print("Got", str(len(answer)), "-", str(downloadedSize), "/", str(reqSize), " (", str(int(downloadedSize * 100 / reqSize)), ")%")
        f.write(answer)

        while downloadedSize < reqSize:

            if variables.errorDownloading != "":
                # thread returned an error
                f.close()
                clientSocket.close()
                return

            try:
                answer = clientSocket.recv(config.data["tcp_rcv_pkt_max_size"])
            except:
                variables.errorDownloading = "Download failure, a server has disconnected, try again"
                f.close()
                clientSocket.close()
                return

            downloadedSize += len(answer)
            print("Got", str(len(answer)), "-", str(downloadedSize), "/", str(reqSize), " (", str(int(downloadedSize * 100 / reqSize)), ")%")

            f.write(answer)

        print("Download completed")

    else:
        # else if the message was not DOWNLOAD OK then the message received was DOWNLOAD FAILURE
        print(answer.decode())
        while answer.decode().count("\n") < 2:
            answer += clientSocket.recv(config.data["tcp_rcv_pkt_max_size"])
            if answer == 0:
                break

        variables.errorDownloading = answer.split("\n")[1]

    f.close()
    clientSocket.close()