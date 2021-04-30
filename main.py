import os
import time
import socket
import threading
import announceHandler
import downloadHandler
import lib.common as utils
import lib.variables as variables
import settings.config as config


def main():
    # start global variables
    variables.init()
    # start thread for UDP send/receive initializer
    threading.Thread(target=announceHandler.init).start()
    # start thread for TCP download request/response initializer
    threading.Thread(target=downloadHandler.init).start()

    telnetReceiver()


def telnetReceiver():
    #Open socket for telnet connection
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
            args = read.split(" ")

            if args[0] == "list":

                timeNow = int(round(time.time() * 1000))
                for file in variables.availableFiles:
                    #Filter available files, remove old ones
                    variables.availableFiles[file]["servers"] = {
                        k: v
                        for (k, v) in variables.availableFiles[file]["servers"].items()
                        if timeNow - v <= 90000
                    }

                    if len(variables.availableFiles[file]["servers"]) == 0:
                        variables.availableFiles = { k: v for (k, v) in variables.availableFiles.items() if k != file }
                    else:
                        response += (
                            file
                            + "\t"
                            + variables.availableFiles[file]["fileSize"]
                            + "\t"
                            + str(variables.availableFiles[file]["fileNames"])
                            + "\n\r"
                        )

                if len(variables.availableFiles) == 0:
                    response = "There are no files available to download"

            elif args[0] == "offer":

                path = config.data["shared_folder"]
                file = args[1]
                if os.path.isfile(path + "\\" + file):
                    variables.myFiles[utils.md5(path + "\\" + file)] = {
                        "fileName": file,
                        "fileSize": utils.getFileSize(path + "\\" + file),
                    }
                    response = "File successfully shared"
                else:
                    response = "File does not exists"

            elif args[0] == "offering":

                response = ""
                for file in variables.myFiles:
                    response += (
                        file
                        + "\t"
                        + variables.myFiles[file]["fileSize"]
                        + "\t"
                        + variables.myFiles[file]["fileName"]
                        + "\n\r"
                    )
                if len(variables.myFiles) == 0:
                    response = "Not sharing anything"

            elif args[0] == "share":
                path = config.data["shared_folder"]
                files = utils.listFolder(config.data["shared_folder"])
                for file in files:
                    variables.myFiles[utils.md5(path + "\\" + file)] = {
                        "fileName": file,
                        "fileSize": utils.getFileSize(path + "\\" + file),
                    }
                response = "Now sharing all files in the folder"

            elif args[0] == "get":

                if args[1] not in variables.availableFiles:
                    response = "Error 3 - Invalid code"
                else:
                    startTime = int(round(time.time() * 1000))
                    variables.errorDownloading = ""
                    x = threading.Thread(target=downloadHandler.startDownload, args=(args[1],))
                    x.start()
                    x.join()
                    if variables.errorDownloading == "":
                        endTime = int(round(time.time() * 1000))
                        fileSize = int(variables.availableFiles[args[1]]["fileSize"])
                        fileName = variables.availableFiles[args[1]]["fileNames"][0]
                        path = config.data["shared_folder"]
                        variables.myFiles[utils.md5(path + "\\" + fileName)] = {
                            "fileName": fileName,
                            "fileSize": utils.getFileSize(path + "\\" + fileName),
                        }
                        response = "File " + args[0] + " was downloaded at a rate of " + str(int(fileSize / ((endTime - startTime) / 1000))) + " Bps"

                    else:
                        response = "\nError 4: " + variables.errorDownloading
            else:
                response = ""

            connectionSock.sendall((response + "\n\r").encode())

        connectionSock.shutdown(socket.SHUT_RDWR)
        connectionSock.close()

    serverSocket.close()

main()
