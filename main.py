import socket
import threading
import lib.common as utils
import anuncios  # receives UDP announces
import descargas
import time
import lib.variables as v
import settings.config as config
import os


def main():
    v.init()  # start global variable

    # start thread for UDP send/receive initializer
    threading.Thread(target=anuncios.init).start()
    # start thread for TCP download request/response initializer
    threading.Thread(target=descargas.init).start()

    telnetReceiver()


def telnetReceiver():

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind((config.data["ip"], config.data["telnet_port"]))
    serverSocket.listen()
    print("Telnet socket started")

    while True:
        connectionSock, addr = serverSocket.accept()
        read = ""
        while read != "CLOSED" or read != "EXIT":
            read, remaining = utils.read_line(connectionSock, "")
            utils.println("Telnet (RECV): " + read)

            response = ""
            read = read[:-1]
            args = read.split(" ")  # list param

            if(args[0] == "list"):

                timeNow = int(round(time.time() * 1000))
                for file in v.availableFiles:
                    v.availableFiles[file]["servers"] = {k: v for (
                        k, v) in v.availableFiles[file]["servers"].items() if timeNow - v <= 90000}

                    if(len(v.availableFiles[file]["servers"]) == 0):
                        v.availableFiles = {
                            k: v for (k, v) in v.availableFiles.items() if k != file}
                    else:
                        response += file + "\t" + v.availableFiles[file]["fileSize"] + "\t" + str(
                            v.availableFiles[file]["fileNames"]) + "\n\r"

                if (len(v.availableFiles) == 0):
                    response = "No hay nada para descargar"

            elif (args[0] == "offer"):

                path = config.data["shared_folder"]
                file = args[1]
                if(os.path.isfile(path + "\\" + file)):
                    v.myFiles[utils.md5(path + "\\" + file)] = {
                        "fileName": file, "fileSize": utils.getFileSize(path + "\\" + file)}
                    response = "El archivo fue agregado"
                else:
                    response = "El archivo no existe"

            elif(args[0] == "offering"):

                response = ""
                for file in v.myFiles:
                    response += file + "\t" + \
                        v.myFiles[file]["fileSize"] + "\t" + \
                        v.myFiles[file]["fileName"] + "\n\r"
                if (len(v.myFiles) == 0):
                    response = "No estas ofreciendo nada"

            elif (args[0] == "share"):
                path = config.data["shared_folder"]
                files = utils.listFolder(config.data["shared_folder"])
                for file in files:
                    v.myFiles[utils.md5(path + "\\" + file)] = {
                        "fileName": file, "fileSize": utils.getFileSize(path + "\\" + file)}
                response = "Estas compartiendo toda la carpeta"

            elif (args[0] == "get"):

                if(args[1] not in v.availableFiles):
                    response = "Error: codigo invalido"
                else:
                    startTime = int(round(time.time() * 1000))
                    v.errorDownloading = ""
                    x = threading.Thread(
                        target=descargas.startDownload, args=(args[1],))
                    x.start()
                    x.join()
                    if(v.errorDownloading == ""):
                        endTime = int(round(time.time() * 1000))
                        fileSize = int(v.availableFiles[args[1]]["fileSize"])
                        fileName = v.availableFiles[args[1]]["fileNames"][0]
                        path = config.data["shared_folder"]
                        v.myFiles[utils.md5(path + "\\" + fileName)] = {
                            "fileName": fileName,
                            "fileSize": utils.getFileSize(path + "\\" + fileName)
                        }
                        response = "El archivo " + args[0] + " fue descargado a un promedio de " + str(
                            int(fileSize / ((endTime - startTime)/1000))) + " Bps"
                    else:
                        response = "\nError: " + v.errorDownloading

            else:
                response = ""

            connectionSock.sendall((response + "\n\r").encode())

        connectionSock.shutdown(socket.SHUT_RDWR)
        connectionSock.close()

    serverSocket.close()


main()
