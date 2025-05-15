import socket
import struct
import threading
import os

# Opcodes
OP_REQUEST = 0x01
OP_SEND = 0x02
OP_RELAY = 0x03
OP_RESPONSE = 0x04

HOST = '0.0.0.0'
PORT = 3843


def recv_all(sock, length):
    data = b''
    while len(data) < length:
        more = sock.recv(length - len(data))
        if not more:
            raise EOFError('Socket closed prematurely')
        data += more
    return data


def handle_client(conn, addr):
    print(f"[+] Conectado: {addr}")
    try:
        while True:
            op = conn.recv(1)
            if not op:
                break
            op = ord(op)

            if op == OP_REQUEST:
                name_len = struct.unpack('>I', recv_all(conn, 4))[0]
                filename = recv_all(conn, name_len).decode()
                print(f"[*] Solicitud de archivo: {filename}")
                if os.path.exists(filename):
                    filesize = os.path.getsize(filename)
                    conn.sendall(struct.pack('B', OP_SEND))
                    conn.sendall(struct.pack('>I', len(filename)) + filename.encode())
                    conn.sendall(struct.pack('>Q', filesize))
                    with open(filename, 'rb') as f:
                        while chunk := f.read(4096):
                            conn.sendall(chunk)
                else:
                    msg = f"Archivo no encontrado: {filename}"
                    conn.sendall(struct.pack('B', OP_RESPONSE))
                    conn.sendall(struct.pack('B', 0x01))
                    conn.sendall(struct.pack('>I', len(msg)) + msg.encode())

            elif op == OP_SEND:
                name_len = struct.unpack('>I', recv_all(conn, 4))[0]
                filename = recv_all(conn, name_len).decode()
                filesize = struct.unpack('>Q', recv_all(conn, 8))[0]
                with open(filename, 'wb') as f:
                    received = 0
                    while received < filesize:
                        chunk = conn.recv(min(4096, filesize - received))
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)
                print(f"[+] Archivo recibido: {filename} ({filesize} bytes)")

                # Enviar confirmación
                msg = "Archivo recibido correctamente"
                conn.sendall(struct.pack('B', OP_RESPONSE))
                conn.sendall(struct.pack('B', 0x00))  # Código 0x00 = OK
                conn.sendall(struct.pack('>I', len(msg)) + msg.encode())


            elif op == OP_RELAY:
                # Read filename
                name_len = struct.unpack('>I', recv_all(conn, 4))[0]
                filename = recv_all(conn, name_len).decode()
            
                # Read nodes list
                node_count = ord(recv_all(conn, 1))
                nodes = []
                for _ in range(node_count):
                    ip_port = recv_all(conn, 22).decode().strip()
                    nodes.append(ip_port)
            
                # Read file size
                filesize = struct.unpack('>Q', recv_all(conn, 8))[0]
            
                # Pop off the next hop
                next_ip_port = nodes.pop(0)
                next_ip, next_port = next_ip_port.split(':')
                next_port = int(next_port)
            
                try:
                    with socket.create_connection((next_ip, next_port)) as s:
                        if nodes:
                            # More hops remain → forward as OP_RELAY
                            print(f"[*] Relaying to {next_ip}:{next_port} (relay, {len(nodes)} left)")
                            s.sendall(struct.pack('B', OP_RELAY))
                            # filename
                            s.sendall(struct.pack('>I', len(filename)) + filename.encode())
                            # new node count
                            s.sendall(struct.pack('B', len(nodes)))
                            # remaining node list
                            for ip_p in nodes:
                                # pad/truncate each to 22 bytes if needed
                                s.sendall(ip_p.ljust(22).encode())
                            # file size
                            s.sendall(struct.pack('>Q', filesize))
                        else:
                            # This is the last hop → send as OP_SEND
                            print(f"[*] Relaying to {next_ip}:{next_port} (final send)")
                            s.sendall(struct.pack('B', OP_SEND))
                            s.sendall(struct.pack('>I', len(filename)) + filename.encode())
                            s.sendall(struct.pack('>Q', filesize))
            
                        # Stream the file bytes through
                        bytes_remaining = filesize
                        while bytes_remaining > 0:
                            chunk = recv_all(conn, min(4096, bytes_remaining))
                            s.sendall(chunk)
                            bytes_remaining -= len(chunk)

                        # Esperar confirmación del siguiente nodo
                        op_code = ord(recv_all(s, 1))
                        if op_code != OP_RESPONSE:
                            raise Exception("Nodo destino no respondió correctamente")

                        cod = ord(recv_all(s, 1))
                        msg_len = struct.unpack('>I', recv_all(s, 4))[0]
                        msg = recv_all(s, msg_len).decode()

                        if cod == 0x00:
                            print(f"[OK] Confirmación del siguiente nodo: {msg}")
                            conn.sendall(struct.pack('B', OP_RESPONSE))
                            conn.sendall(struct.pack('B', 0x00))
                            conn.sendall(struct.pack('>I', len(msg)) + msg.encode())
                        else:
                            print(f"[ERROR] Nodo intermedio falló: {msg}")
                            conn.sendall(struct.pack('B', OP_RESPONSE))
                            conn.sendall(struct.pack('B', 0x01))
                            conn.sendall(struct.pack('>I', len(msg)) + msg.encode())

                except Exception as e:
                    error_msg = f"Fallo al retransmitir: {e}"
                    print(f"[!] {error_msg}")
                    conn.sendall(struct.pack('B', OP_RESPONSE))
                    conn.sendall(struct.pack('B', 0x01))
                    conn.sendall(struct.pack('>I', len(error_msg)) + error_msg.encode())


    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()


def start_server():
    print(f"[*] Iniciando servidor en {HOST}:{PORT}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == '__main__':
    start_server()
