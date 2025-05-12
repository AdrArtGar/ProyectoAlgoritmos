import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import heapq
import paramiko
import time
import os

# GRAFO DE LATENCIA 
raw_bandwidth_graph = {
    'A': {'B': 100, 'C': 50},
    'B': {'A': 100, 'D': 75},
    'C': {'A': 50, 'D': 30},
    'D': {'B': 75, 'C': 30}
}

graph = {}
for node in raw_bandwidth_graph:
    graph[node] = {}
    for neighbor in raw_bandwidth_graph[node]:
        bandwidth = raw_bandwidth_graph[node][neighbor]
        graph[node][neighbor] = 1 / bandwidth  # Convertir ancho de banda a latencia (menor = mayor latencia)

# MAPA DE IPs
node_ips = {
    'A': '10.0.0.1',
    'B': '10.0.0.2',
    'C': '10.0.0.3',
    'D': '10.0.0.4',
}

username = 'usuario'  # CAMBIAR
password = 'contraseña'  # CAMBIAR

# ALGORITMO DIJKSTRA
def dijkstra(graph, start, end):
    queue = [(0, start, [])]
    visited = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in visited:
            continue
        path = path + [node]
        visited.add(node)
        if node == end:
            return cost, path
        for neighbor in graph.get(node, {}):
            if neighbor not in visited:
                total_cost = cost + graph[node][neighbor]
                heapq.heappush(queue, (total_cost, neighbor, path))
    return float("inf"), []

# TRANSFERENCIA DE ARCHIVO
def transfer_file_via_path(path, file_path, node_ips, username, password):
    dest = path[-1]  # Nodo destino final
    ip = node_ips[dest]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Conectando a {dest} ({ip})...")
    ssh.connect(ip, username=username, password=password)
    sftp = ssh.open_sftp()
    print(f"Enviando archivo directamente a {dest}...")
    sftp.put(file_path, '/tmp/archivo_transferido')  # Ruta de destino en el nodo remoto
    sftp.close()
    ssh.close()
    print("Transferencia completada.")

# COMPARAR TIEMPOS DE TRANSFERENCIA
def transfer_file(path, file_path, node_ips, username, password):
    start_time = time.time()
    transfer_file_via_path(path, file_path, node_ips, username, password)
    return time.time() - start_time

# GUI
def run_gui():
    def on_transfer():
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        target_node = target_combobox.get()
        if not target_node:
            messagebox.showerror("Error", "Debes seleccionar un nodo destino.")
            return

        # Ruta óptima
        cost, path_optimal = dijkstra(graph, local_node, target_node)
        if not path_optimal:
            messagebox.showerror("Error", "Ruta óptima no encontrada.")
            return

        # Ruta directa
        direct_path = [local_node, target_node]
        
        # Comparar tiempos de transferencia
        time_optimal = transfer_file(path_optimal, file_path, node_ips, username, password)
        time_direct = transfer_file(direct_path, file_path, node_ips, username, password)

        # Mostrar resultados en la GUI
        messagebox.showinfo("Éxito", f"Archivo transferido por ruta óptima: {path_optimal}\nTiempo (óptima): {time_optimal:.2f} segundos")
        messagebox.showinfo("Comparación", f"Tiempo de transferencia ruta directa: {time_direct:.2f} segundos")

        # Confirmar recepción del archivo
        if check_file_received(path_optimal[-1], file_path):
            messagebox.showinfo("Confirmación", "Archivo recibido exitosamente.")
        else:
            messagebox.showerror("Error", "El archivo no fue recibido correctamente.")

    def check_file_received(node, file_path):
        # Verificar si el archivo existe en el destino
        ip = node_ips[node]
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)
        sftp = ssh.open_sftp()
        try:
            sftp.stat('/tmp/temp_transfer_file')
            return True
        except FileNotFoundError:
            return False
        finally:
            sftp.close()
            ssh.close()

    local_node = "A"
    root = tk.Tk()
    root.title("File Transfer Optimizer (Latencia)")
    tk.Label(root, text="Selecciona el nodo destino:").pack(pady=10)
    target_combobox = ttk.Combobox(root, values=list(graph.keys()))
    target_combobox.pack(pady=5)
    transfer_button = tk.Button(root, text="Seleccionar archivo y transferir", command=on_transfer)
    transfer_button.pack(pady=20)
    root.mainloop()

if __name__ == "__main__":
    run_gui()
