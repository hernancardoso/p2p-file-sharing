import socket
import time
import threading
import random
import sys
import lib.common as utils
import lib.variables as variables
import settings.config as config

UDPServerSocket = ""


def init():
    global UDPServerSocket

    # Create a datagram socket
    UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    # Enable broadcast ip
    UDPServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    # Bind to address and ip
    UDPServerSocket.bind((config.data["ip"], config.data["udp_port"]))

    print("UDP socket started\n")
    # Start a thread to send ANNOUNCES each 30 seconds
    threading.Thread(target=periodicAnnounce).start()
    UDPServerSocket.sendto(
        "REQUEST\n".encode(), ("<broadcast>", config.data["udp_port"])
    )
    listen() #start listening for new ANNOUNCES or REQUEST solicitations



# Given a start position this function will attemt to construct an ANNOUNCE message with some restrictions
# 1. One ANNOUNCE message must contain at least MAX_ANNOUNCE_LINES lines.
# 2. One ANNOUNCE message must be contained in an MSS (must have less bytes than defined in settings: udp_dgram_max_size)
# If an ANNOUNCE satisfies both conditions and can include all files that the user is sharing it returns TRUE,
# otherwise returns false and createAnnounce should be called again with another value of startPosition
def createAnnounce(startPosition):
    message = "ANNOUNCE\n"
    i = 0
    myFiles = {}
    temp = 0

    for files in variables.myFiles:
        myFiles[temp] = [files, variables.myFiles[files]["fileName"]]
        temp += 1


    for i in range(startPosition, min(int(config.data["max_announce_lines"]) + startPosition, len(variables.myFiles))):

        filePath = config.data["shared_folder"] + "\\" + myFiles[i][1]
        tempMessage = (
            myFiles[i][1]
            + "\t"
            + utils.getFileSize(filePath)
            + "\t"
            + utils.md5(filePath)
            + "\n")

        #Check if last line added passes the maximum datagram size, if it does then rollback that action
        if sys.getsizeof((message + tempMessage).encode()) > int(config.data["udp_dgram_max_size"]):
            i -= 1
            break
        
        message += tempMessage

    #If all files were included on the announce return True
    if i == len(variables.myFiles) - 1:
        return True, startPosition, message

    startPosition = i + 1
    return False, startPosition, message


# Announcing shared files could be completed in more than one ANNOUNCE message.
# This functions ensures that all shared files are announced.
def announce(address):
    announceCompleted = False
    startPosition = 0

    while (not announceCompleted) and len(variables.myFiles) > 0:
        announceCompleted, startPosition, message = createAnnounce(
            startPosition)

        UDPServerSocket.sendto(message.encode(), address)
        time.sleep(random.randint(50, 100) / 100)  # 0.5 a 1


# Announce every 30 + [0,1] seconds all the shared files
def periodicAnnounce():
    while True:
        announce(("<broadcast>", config.data["udp_port"]))
        time.sleep(30 + random.randint(0, 100) / 100)  # 0 a 1

def listen():
    # Listen for incoming datagrams
    while True:
        read, address = UDPServerSocket.recvfrom(
            config.data["udp_dgram_max_size"])

        read = read.decode()
        if address[0] != config.data["ip"]:  # Ignore self datagrams

            if config.data["debugging"]:
                print("\nNew UDP message\n" + str(read))

            if read.find("ANNOUNCE") != -1:
                read = read[8:]  # remove ANNOUNCE from read
                for line in read.split("\n"):
                    if line == "":
                        continue

                    item = line.split("\t")
                    fileName = item[0]
                    fileSize = item[1]
                    fileMD5 = item[2]
                    timestamp = int(round(time.time() * 1000))
                    if fileMD5 not in variables.availableFiles:
                        # new file arrived
                        variables.availableFiles[fileMD5] = {
                            "fileNames": [fileName],
                            "fileSize": fileSize,
                            "servers": {address[0]: timestamp},
                        }
                    else:
                        # known file arrived, update or create server IP and timestamp
                        variables.availableFiles[fileMD5]["servers"][address[0]
                                                             ] = timestamp
                        if fileName not in variables.availableFiles[fileMD5]["fileNames"]:
                            variables.availableFiles[fileMD5]["fileNames"].append(
                                fileName)

                if config.data["debugging"]:
                    print("\nAvailable Files:\n" +
                          str(variables.availableFiles) + "\n")
            else:
                # If is not ANNOUNCE then is (or could be) REQUEST
                x = threading.Thread(target=announce, args=(address,))
                x.start()