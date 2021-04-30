data = {

    # Settings of service IP and port
    "ip": "127.0.0.1",
    "udp_port": 2020,
    "tcp_port": 2020,
    "telnet_port": 2025,
    
    # UDP maximum datagram size
        # Note: offering many files makes the announce message size bigger
        # if is bigger than udp_dgram_max_size size then the original message will
        # be splitted into smaller chunks
    "udp_dgram_max_size": 1024,

    # The UDP announce message can also be splitted into smaller chunks
    # if it exceeds max_announce_lines lines
    "max_announce_lines": 2,
    
    # TCP receive maximum data size
        # The maximum amount of data to be received at once is specified by 
        # tcp_rcv_pkt_max_size (4096 for best match with hardware and network realities
    "tcp_rcv_pkt_max_size": 4096,

    # Folder in which shared and downloaded files will be located
    "shared_folder": "C:\\Users\\Redes\\SharedFolder",

    # verbose mode
    "debugging": False,
}
