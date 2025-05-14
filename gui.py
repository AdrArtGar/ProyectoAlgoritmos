import subprocess
import sys
import argparse
import csv
import networkx as nx
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import time
import socket
import threading
from datetime import datetime
import glob

from cliente import enviar_archivo, enviar_por_ruta
from server import start_server
from dijkstra import dijkstra
from kruskal import kruskal
## --- Configuración de Red --- ##

def iniciar_servidor_iperf(puerto=5201):
    """Inicia servidor iperf3 en segundo plano"""
    try:
        subprocess.Popen(["iperf3", "-s", "-p", str(puerto)], 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False
## --- Interfaz Gráfica --- ##

class VPNTransferGUI:
    def __init__(self, root, ip_local, nodos, latencias, anchos_banda):
        self.root = root
        self.root.title(f"Optimizador VPN - {ip_local}")
        self.root.geometry("1100x750")
        
        self.ip_local = ip_local
        self.nodos = nodos
        self.latencias = latencias
        self.anchos_banda = anchos_banda
        self.grafo_latencia = nx.DiGraph()
        self.grafo_ancho_banda = nx.DiGraph()
        self.archivo_seleccionado = None
        
        self.construir_interfaz()
        self.procesar_metricas()
        self.actualizar_visualizacion()
    
    def construir_interfaz(self):
        # Frame principal
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel de control
        self.control_frame = ttk.Frame(self.main_frame, width=300)
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        # Panel de visualización
        self.display_frame = ttk.Frame(self.main_frame)
        self.display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Widgets de control
        self.etiqueta_nodos = ttk.Label(self.control_frame, text="Nodos VPN:\n" + '\n'.join(self.nodos))
        self.etiqueta_nodos.pack(pady=10)
        
        ttk.Label(self.control_frame, text="Archivo a transferir:").pack()
        self.entry_archivo = ttk.Entry(self.control_frame)
        self.entry_archivo.pack(fill=tk.X, padx=5)
        ttk.Button(self.control_frame, text="Seleccionar", 
                  command=self.seleccionar_archivo).pack(pady=5)
        
        ttk.Label(self.control_frame, text="Nodo destino:").pack()
        self.combo_destino = ttk.Combobox(self.control_frame, values=self.nodos)
        self.combo_destino.pack(fill=tk.X, padx=5)
        
        self.var_optimizar = tk.IntVar(value=1)
        ttk.Checkbutton(self.control_frame, text="Optimizar por latencia",
                       variable=self.var_optimizar).pack(anchor=tk.W)
        
        ttk.Button(self.control_frame, text="Iniciar Transferencia", 
                  command=self.iniciar_transferencia).pack(pady=20)
        
        self.texto_resultados = tk.Text(self.control_frame, height=10, wrap=tk.WORD)
        self.texto_resultados.pack(fill=tk.BOTH, expand=True)
        
        # Notebook para gráficos
        self.notebook = ttk.Notebook(self.display_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.tabs = {
            "latencia": ttk.Frame(self.notebook),
            "ancho_banda": ttk.Frame(self.notebook),
            "mst": ttk.Frame(self.notebook),
            "rutas": ttk.Frame(self.notebook)
        }
        
        for nombre, tab in self.tabs.items():
            self.notebook.add(tab, text=nombre.capitalize())
            setattr(self, f"canvas_{nombre}", ttk.Frame(tab))
            getattr(self, f"canvas_{nombre}").pack(fill=tk.BOTH, expand=True)
    
    def procesar_metricas(self):
        self.grafo_latencia.add_nodes_from(self.nodos)
        self.grafo_ancho_banda.add_nodes_from(self.nodos)

        for (origen, destino), latencia in self.latencias.items():
            if not (latencia != latencia):  # Verifica que no sea NaN
                self.grafo_latencia.add_edge(origen, destino, weight=latencia)

        for (origen, destino), ancho_banda in self.anchos_banda.items():
            if not (ancho_banda != ancho_banda) and ancho_banda > 0:  # No NaN y positivo
                self.grafo_ancho_banda.add_edge(origen, destino,
                                                weight=1/ancho_banda,
                                                ancho_banda_real=ancho_banda)
    
    def actualizar_visualizacion(self):
        self.dibujar_grafo(self.grafo_latencia, "latencia", "Latencia (ms)")
        self.dibujar_grafo(self.grafo_ancho_banda, "ancho_banda", "Ancho de Banda (Mbps)", True)
        self.dibujar_mst()
    
    def dibujar_grafo(self, grafo, nombre_tab, titulo, usar_ancho_banda=False):
        frame = getattr(self, f"canvas_{nombre_tab}")
        for widget in frame.winfo_children():
            widget.destroy()
        
        if grafo.number_of_edges() == 0:
            ttk.Label(frame, text=f"No hay datos de {titulo}").pack(expand=True)
            return
        
        fig, ax = plt.subplots(figsize=(7, 5))
        pos = nx.circular_layout(grafo)
        
        nx.draw(grafo, pos, ax=ax, with_labels=True, node_size=800,
               node_color="lightblue", font_size=9, width=1.5)
        
        if usar_ancho_banda:
            etiquetas = {(u, v): f"{d['ancho_banda_real']:.1f}" 
                        for u, v, d in grafo.edges(data=True)}
        else:
            etiquetas = nx.get_edge_attributes(grafo, 'weight')
            etiquetas = {k: f"{v:.1f}" for k, v in etiquetas.items()}
        
        nx.draw_networkx_edge_labels(grafo, pos, edge_labels=etiquetas, font_size=8)
        ax.set_title(titulo)
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def dibujar_mst(self):
        frame = self.canvas_mst
        for widget in frame.winfo_children():
            widget.destroy()
        
        if self.grafo_ancho_banda.number_of_edges() == 0:
            ttk.Label(frame, text="No hay datos para MST").pack(expand=True)
            return
        
        mst = kruskal(self.grafo_ancho_banda)
        if not mst:
            ttk.Label(frame, text="No se pudo calcular MST").pack(expand=True)
            return
        
        fig, ax = plt.subplots(figsize=(7, 5))
        pos = nx.circular_layout(mst)
        
        nx.draw(mst, pos, ax=ax, with_labels=True, node_size=800,
               node_color="lightgreen", font_size=9, width=1.5)
        
        etiquetas = {(u, v): f"{d['ancho_banda_real']:.1f}" 
                    for u, v, d in mst.edges(data=True)}
        nx.draw_networkx_edge_labels(mst, pos, edge_labels=etiquetas, font_size=8)
        ax.set_title("Árbol de Expansión Mínima (Mbps)")
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def seleccionar_archivo(self):
        archivo = filedialog.askopenfilename()
        if archivo:
            self.archivo_seleccionado = archivo
            self.entry_archivo.delete(0, tk.END)
            self.entry_archivo.insert(0, archivo)
            tamano = os.path.getsize(archivo) / (1024 * 1024)  # MB
            self.texto_resultados.insert(tk.END, f"Archivo: {archivo}\nTamaño: {tamano:.2f} MB\n")
    
    def iniciar_transferencia(self):
        if not self.archivo_seleccionado:
            messagebox.showerror("Error", "Seleccione un archivo")
            return

        destino = self.combo_destino.get()
        if not destino or destino == self.ip_local:
            messagebox.showerror("Error", "Seleccione un destino válido")
            return

        optimizar_por_latencia = self.var_optimizar.get()
        grafo = self.grafo_latencia if optimizar_por_latencia else self.grafo_ancho_banda

        camino, costo = dijkstra(grafo, self.ip_local, destino)
        if not camino:
            self.texto_resultados.insert(tk.END, f"No se pudo encontrar ruta hacia {destino}\n")
            return

        self.texto_resultados.insert(tk.END, f"\nIniciando transferencia a {destino}...\n")
        self.texto_resultados.insert(tk.END, f"Ruta calculada: {' → '.join(camino)}\n")
        
        ruta_ip = [f"{nodo}:3843" for nodo in camino[1:]]  # Asume puerto TCP 3843

        # Elegir modo directo o relay
        try:
            if len(ruta_ip) == 1:
                enviar_archivo(ruta_ip[0].split(':')[0], 3843, self.archivo_seleccionado)
            else:
                enviar_por_ruta(ruta_ip[0].split(':')[0], 3843, self.archivo_seleccionado, ruta_ip[1:])
        except Exception as e:
            self.texto_resultados.insert(tk.END, f"[ERROR] Transferencia falló: {e}\n")
        else:
            self.texto_resultados.insert(tk.END, "[OK] Transferencia finalizada.\n")

    
    def dibujar_ruta(self, ruta, titulo):
        frame = self.canvas_rutas
        for widget in frame.winfo_children():
            widget.destroy()
        
        fig, ax = plt.subplots(figsize=(7, 5))
        pos = nx.circular_layout(self.grafo_latencia)
        
        # Dibujar grafo completo
        nx.draw(self.grafo_latencia, pos, ax=ax, with_labels=True,
               node_size=600, node_color="lightgray", alpha=0.7)
        
        # Resaltar ruta
        nx.draw_networkx_nodes(self.grafo_latencia, pos, nodelist=ruta,
                             node_color="red", node_size=800)
        
        aristas_ruta = [(ruta[i], ruta[i+1]) for i in range(len(ruta)-1)]
        nx.draw_networkx_edges(self.grafo_latencia, pos, edgelist=aristas_ruta,
                             edge_color="red", width=2)
        
        ax.set_title(titulo)
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def simular_transferencia(self, destino):
        # Simulación basada en métricas reales
        tamano = os.path.getsize(self.archivo_seleccionado) / (1024 * 1024)  # MB
        
        if self.grafo_latencia.has_edge(self.ip_local, destino):
            latencia = self.grafo_latencia[self.ip_local][destino]['weight']
        else:
            latencia = 100  # Valor por defecto si no hay datos
        
        if (self.grafo_ancho_banda.has_edge(self.ip_local, destino) and 
            'ancho_banda_real' in self.grafo_ancho_banda[self.ip_local][destino]):
            ancho_banda = self.grafo_ancho_banda[self.ip_local][destino]['ancho_banda_real']
        else:
            ancho_banda = 10  # Valor por defecto en Mbps
        
        # Calcular tiempo estimado (en segundos)
        tiempo = (tamano * 8) / ancho_banda + (latencia / 1000)
        
        self.texto_resultados.insert(tk.END, f"\nEstimación de transferencia:\n")
        self.texto_resultados.insert(tk.END, f"- Latencia: {latencia:.2f} ms\n")
        self.texto_resultados.insert(tk.END, f"- Ancho de banda: {ancho_banda:.2f} Mbps\n")
        self.texto_resultados.insert(tk.END, f"- Tiempo estimado: {tiempo:.2f} segundos\n")
        
        # Simular progreso
        self.simular_progreso(tiempo)
    
    def simular_progreso(self, tiempo_total):
        tiempo_inicio = time.time()
        tiempo_restante = tiempo_total
        
        self.barra_progreso = ttk.Progressbar(self.control_frame, 
                                            orient=tk.HORIZONTAL,
                                            length=200,
                                            mode='determinate',
                                            maximum=100)
        self.barra_progreso.pack(pady=10)
        
        while tiempo_restante > 0:
            progreso = 100 * (1 - tiempo_restante/tiempo_total)
            self.barra_progreso['value'] = progreso
            self.root.update()
            
            time.sleep(0.1)
            tiempo_restante = tiempo_total - (time.time() - tiempo_inicio)
        
        self.barra_progreso['value'] = 100
        self.texto_resultados.insert(tk.END, "\n¡Transferencia completada!\n")
        self.texto_resultados.see(tk.END)

def leer_metricas():
    latencias = {}
    anchos_banda = {}
    nodos = set()  # Usamos un set para evitar duplicados

    for archivo in glob.glob("metricas_*.csv"):
        with open(archivo, newline='') as csvfile:
            lector = csv.DictReader(csvfile)
            for fila in lector:
                origen = fila['origen']
                destino = fila['destino']
                clave = (origen, destino)

                latencias[clave] = float(fila['latencia_ms'])
                anchos_banda[clave] = float(fila['ancho_banda_mbps'])

                nodos.add(origen)
                nodos.add(destino)

    return latencias, anchos_banda, sorted(nodos)


## --- Función Principal --- ##

def main():
    threading.Thread(target=start_server, daemon=True).start()
    # Configuración inicial
    parser = argparse.ArgumentParser(description="Medición de latencia y ancho de banda entre nodos")
    parser.add_argument("--local", required=True, help="IP Local")
    args = parser.parse_args()

    metricas_latencia, metricas_ancho_banda, nodos = leer_metricas()

    ip_local = args.local

    print(f"Dirección IP local: {ip_local}")
    
    # Iniciar servidor iperf para que otros nodos puedan detectarnos
    if not iniciar_servidor_iperf():
        print("Advertencia: No se pudo iniciar servidor iperf3")

    print(f"Nodos detectados: {nodos}")
    
    # Iniciar interfaz gráfica
    print("\nIniciando interfaz gráfica...")
    root = tk.Tk()
    app = VPNTransferGUI(root, ip_local, nodos, metricas_latencia, metricas_ancho_banda)
    root.mainloop()

if __name__ == "__main__":
    main()
