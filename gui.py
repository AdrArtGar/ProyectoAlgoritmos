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
        
