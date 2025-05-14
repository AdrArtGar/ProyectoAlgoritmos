"""
  ips.txt         Archivo de texto con una IP por línea (cada nodo de la VPN)
  --puerto-iperf  Puerto en el que corre iperf3 en modo servidor en cada nodo
  --conteo-ping   Número de paquetes ICMP para medir latencia
  --duracion-iperf Duración en segundos de la prueba de ancho de banda
"""
import argparse
import subprocess
import platform
import csv
import networkx as nx
import matplotlib.pyplot as plt
import re

def medir_latencia(ip, conteo=4):
    try:
        sistema = platform.system()
        if sistema == "Windows":
            comando = ["ping", "-n", str(conteo), ip]
        else:
            comando = ["ping", "-c", str(conteo), ip]

        resultado = subprocess.run(comando, capture_output=True, text=True, encoding='cp850', errors='ignore')

        for linea in resultado.stdout.splitlines():
            if sistema == "Windows" and ("Media" in linea or "media" in linea):
                # Extrae el último número antes de 'ms'
                numeros = re.findall(r'\d+', linea)
                if numeros:
                    return float(numeros[-1])
            elif sistema != "Windows" and ("rtt min" in linea or "round-trip" in linea):
                partes = linea.split(' = ')[1].split(' ')[0].split('/')
                return float(partes[1])

    except subprocess.CalledProcessError:
        return None


def medir_ancho_banda(ip, puerto=5201, duracion=10):
    try:
        resultado = subprocess.run([
            "iperf3", "-c", ip, "-p", str(puerto), "-t", str(duracion), "-f", "m"
        ], capture_output=True, text=True, check=True)
        
        for linea in reversed(resultado.stdout.splitlines()):
            if "sender" in linea and "Mbits/sec" in linea:
                campos = linea.split()
                for i, campo in enumerate(campos):
                    if campo == "Mbits/sec" and i > 0:
                        try:
                            ancho = float(campos[i - 1])
                            return ancho
                        except ValueError:
                            continue
    except subprocess.CalledProcessError:
        return None

def cargar_nodos(ruta_archivo):
    with open(ruta_archivo) as f:
        return [linea.strip() for linea in f if linea.strip()]


def main():
    parser = argparse.ArgumentParser(description="Medición de latencia y ancho de banda entre nodos")
    parser.add_argument("--nodos", required=True, help="Archivo con IPs de los nodos, una por línea")
    parser.add_argument("--puerto-iperf", type=int, default=5201, help="Puerto de iperf3 servidor")
    parser.add_argument("--conteo-ping", type=int, default=4, help="Número de pings por prueba")
    parser.add_argument("--duracion-iperf", type=int, default=10, help="Duración de iperf3 en segundos")
    parser.add_argument("--local", required=True, help="IP Local")
    args = parser.parse_args()

    nodos = cargar_nodos(args.nodos)
    metricas = []  # lista de tuplas: (origen, destino, latencia_ms, ancho_banda_mbps)
    
    ip_local = args.local

    for destino in nodos:
            if ip_local == destino:
                continue
            print(f"Midiendo {ip_local} -> {destino}...")
            lat = medir_latencia(destino, conteo=args.conteo_ping)
            bw = medir_ancho_banda(destino, puerto=args.puerto_iperf, duracion=args.duracion_iperf)
            metricas.append((ip_local, destino, lat if lat else float('nan'), bw if bw else float('nan')))

    nombre_archivo = f"metricas_{ip_local}.csv"
    with open(nombre_archivo, "w", newline="") as archivo_csv:
        escritor = csv.writer(archivo_csv)
        escritor.writerow(["origen", "destino", "latencia_ms", "ancho_banda_mbps"])
        escritor.writerows(metricas)
    print(f"Guardado {nombre_archivo}")


    
if __name__ == "__main__":
    main()