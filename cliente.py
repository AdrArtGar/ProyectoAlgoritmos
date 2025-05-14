import socket
import struct
import os

OP_SEND = 0x02
OP_RELAY = 0x03
OP_RESPONSE = 0x04

def recv_all(sock, length):
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError("Socket cerrado antes de tiempo")
        data += more
    return data

def leer_confirmacion(sock):
    opcode = ord(recv_all(sock, 1))
    if opcode != OP_RESPONSE:
        print(f"[ERROR] Respuesta inesperada del servidor: opcode {opcode}")
        return

    codigo = ord(recv_all(sock, 1))
    largo_msg = struct.unpack('>I', recv_all(sock, 4))[0]
    mensaje = recv_all(sock, largo_msg).decode()

    if codigo == 0x00:
        print(f"[OK] Confirmación del servidor: {mensaje}")
    else:
        print(f"[ERROR] Servidor reportó error: {mensaje}")

def enviar_archivo(host, puerto, archivo):
    nombre = os.path.basename(archivo)
    tamano = os.path.getsize(archivo)
    datos = open(archivo, 'rb').read()

    with socket.create_connection((host, puerto)) as sock:
        print(f"[INFO] Conectado a {host}:{puerto}")
        header = struct.pack("!B I {}s Q".format(len(nombre)),
                             OP_SEND,
                             len(nombre),
                             nombre.encode(),
                             tamano)
        sock.sendall(header + datos)
        leer_confirmacion(sock)

def enviar_por_ruta(host, puerto, archivo, ruta):
    nombre = os.path.basename(archivo)
    nombre_bytes = nombre.encode()
    num_nodos = len(ruta)
    tamano = os.path.getsize(archivo)

    with open(archivo, 'rb') as f:
        datos = f.read()

    with socket.create_connection((host, puerto)) as sock:
        print(f"[INFO] Conectado a {host}:{puerto} para retransmisión")

        sock.sendall(struct.pack("!B", OP_RELAY))
        sock.sendall(struct.pack(">I", len(nombre_bytes)))
        sock.sendall(nombre_bytes)
        sock.sendall(struct.pack("B", num_nodos))

        for nodo in ruta:
            nodo_bytes = nodo.encode().ljust(22, b' ')
            sock.sendall(nodo_bytes)

        sock.sendall(struct.pack(">Q", tamano))
        sock.sendall(datos)

        leer_confirmacion(sock)