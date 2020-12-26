import socket
import time
import lib.common as utils
import threading
import lib.variables as v
import settings.config as config
import sys

serverSocket = ""
threadError = {}


def init():
    global serverSocket

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind((config.data["ip"], config.data["tcp_port"]))
    serverSocket.listen()
    utils.println("TCP socket started")

    while True:
        print("Waiting for connection...\n")
        connectionSock, addr = serverSocket.accept()
        threading.Thread(
            target=serveClient,
            args=(
                connectionSock,
                addr,
            ),
        ).start()


def serveClient(clientSock, addr):
    print("New thread - TCP connection with " + addr[0] + "\n")

    read, remaining = utils.read_line(clientSock, "")
    if read == "DOWNLOAD":

        md5Code, remaining = utils.read_line(clientSock, remaining)
        if md5Code == "CLOSED":
            return False

        reqStart, remaining = utils.read_line(clientSock, remaining)
        if reqStart == "CLOSED":
            return False

        reqSize, remaining = utils.read_line(clientSock, remaining)
        if reqSize == "CLOSED":
            return False

        if md5Code not in v.myFiles:
            # client doesnt have requested file in shared_folder
            clientSock.sendall("DOWNLOAD FAILURE\nMISSING\n".encode())
            return False

        if (
            not reqSize.isnumeric()
            or not reqStart.isnumeric()
            or int(reqStart) > int(v.myFiles[md5Code]["fileSize"])
        ):
            clientSock.sendall("DOWNLOAD FAILURE\nBAD REQUEST\n".encode())
            print("error 1")
            return False

        if int(reqStart) + int(reqSize) > int(v.myFiles[md5Code]["fileSize"]):
            clientSock.sendall("DOWNLOAD FAILURE\nBAD REQUEST\n".encode())
            print("error 2")
            return False

        reqSize = int(reqSize)
        reqStart = int(reqStart)

        f = open(
            config.data["shared_folder"] + "\\" + v.myFiles[md5Code]["fileName"], "rb"
        )
        f.seek(reqStart)

        buffer = "DOWNLOAD OK\n".encode()
        buffer += f.read(reqSize)
        print("SENDING DATA WITH SIZE " + str(sys.getsizeof(buffer)))
        clientSock.sendall(buffer)

        f.close()

    clientSock.shutdown(socket.SHUT_RDWR)
    clientSock.close()


def startDownload(md5Code):

    fileSize = int(v.availableFiles[md5Code]["fileSize"])
    timeNow = int(round(time.time() * 1000))

    # Filter servers and get only ones that are "still alive"
    v.availableFiles[md5Code]["servers"] = {
        k: v
        for (k, v) in v.availableFiles[md5Code]["servers"].items()
        if timeNow - v <= 90000
    }
    if len(v.availableFiles[md5Code]["servers"]) == 0:
        v.availableFiles = {k: v for (k, v) in v.availableFiles.items() if k != md5Code}
        v.errorDownloading = "El archivo no esta disponible para descargar"
        return

    # shortcut for availableServers
    availableServers = v.availableFiles[md5Code]["servers"]

    totalServers = len(availableServers)

    actualServer = 0
    # The chunks size is divided by the number of available server
    chunkSize = int(fileSize / totalServers)

    t = {}  # for each available server a new thread is created and stored in this array
    i = 0  # an index to iterate over t[] array

    for ip in availableServers:
        startingByte = chunkSize * actualServer

        if actualServer == totalServers - 1:
            # if fileSize is 5 and 2 servers are available 5/2 = 2 and 1 is remaining, the remaining bytes are added to latest server in the array
            chunkSize += fileSize % totalServers

        print("New thread, downloading from " + ip + "\n")
        t[i] = threading.Thread(
            target=downloadChunk, args=(ip, md5Code, startingByte, chunkSize)
        )
        t[i].start()
        i += 1
        actualServer += 1

    # Wait for all threads to end
    for i in t:
        t[i].join()


def downloadChunk(ip, md5Code, reqByte, reqSize):
    global threadError

    clientSocket = socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.settimeout(8)

    try:
        clientSocket.connect((ip, config.data["tcp_port"]))
    except:
        v.errorDownloading = "Un servidor se desconecto"

        del v.availableFiles[md5Code]["servers"][ip]
        if len(v.availableFiles[md5Code]["servers"]) == 0:
            del v.availableFiles[md5Code]
        return

    utils.println("Connected to " + ip)

    request = "DOWNLOAD\n" + md5Code + "\n" + str(reqByte) + "\n" + str(reqSize) + "\n"
    clientSocket.sendall(request.encode())
    print("Sended:\n" + request)

    fileName = v.availableFiles[md5Code]["fileNames"][0]
    downloadedSize = 0

    f = open(config.data["shared_folder"] + "\\" + fileName, "wb+")
    f.seek(reqByte)  # position in starting byte

    answer = clientSocket.recv(config.data["tcp_pckt_max_size"])
    # Repeat until header is obtained
    while len(answer) < 12:
        try:
            answer += clientSocket.recv(config.data["tcp_pckt_max_size"])
        except:
            v.errorDownloading = (
                "un servidor cerro la conexion, es necesario descargar de nuevo"
            )
            f.close()
            clientSocket.close()
            return

    if answer[:12].decode().find("DOWNLOAD OK\n") != -1:
        answer = answer[12:]
        downloadedSize += len(answer)
        utils.println(
            "Got "
            + str(len(answer))
            + " - "
            + str(downloadedSize)
            + "/"
            + str(reqSize)
            + " ("
            + str(int(downloadedSize * 100 / reqSize))
            + ")%"
        )
        f.write(answer)

        while downloadedSize < reqSize:

            if v.errorDownloading != "":
                # thread returned an error
                f.close()
                clientSocket.close()
                return

            try:
                answer = clientSocket.recv(config.data["tcp_pckt_max_size"])
            except:
                v.errorDownloading = (
                    "un servidor cerro la conexion, es necesario descargar de nuevo"
                )
                f.close()
                clientSocket.close()
                return

            downloadedSize += len(answer)
            utils.println(
                "Got "
                + str(len(answer))
                + " - "
                + str(downloadedSize)
                + "/"
                + str(reqSize)
                + " ("
                + str(int(downloadedSize * 100 / reqSize))
                + ")%"
            )
            f.write(answer)

        print("DOWNLOADED")

    else:
        # else if the message was not DOWNLOAD OK then the message received was DOWNLOAD FAILURE
        print(answer.decode())
        while answer.decode().count("\n") < 2:
            answer += clientSocket.recv(config.data["tcp_pckt_max_size"])
            if answer == 0:
                break

        v.errorDownloading = answer.split("\n")[1]

    f.close()
    clientSocket.close()
