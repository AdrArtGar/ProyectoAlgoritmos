# Optimizador de Rutas VPN con Algoritmos de Grafos

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![NetworkX](https://img.shields.io/badge/NetworkX-2.6+-green)
![Matplotlib](https://img.shields.io/badge/Matplotlib-3.5+-yellowgreen)

Sistema de transferencia de archivos optimizado para redes VPN que utiliza algoritmos de grafos para determinar rutas eficientes basadas en métricas de red.

## Características Principales

- Medición automática de latencia y ancho de banda
- Visualización interactiva de topologías de red
- Algoritmo de Dijkstra para encontrar rutas óptimas
- Algoritmo de Kruskal para árbol de expansión mínima
- Transferencia segura de archivos entre nodos
- Interfaz gráfica con Tkinter

## Instalación

1. Clonar repositorio:
     git clone https://github.com/AdrArtGar/ProyectoAlgoritmos.git

     cd ProyectoAlgoritmos
3. Instalar dependencias:
     pip install -r requirements.txt
4. Instalar iperf3
   ### Ubuntu/Debian
     sudo apt install iperf3
   ### Windows
     instalar directamente de la pagina: https://iperf.fr/

## Configuración
Crear archivo ips.txt con las IPs de los nodos

## Para el uso
1. Conectar a la VPN (Usaremos hamachi)
2. Usar la GUI (Inicia automaticamente los servidores necesarios iperf3)
   - *python gui.py*
3. Tomar métricas de red
   - *python tomarmetricas.py --nodos ips.txt --local [TU_IP]*
## Abrir y cerrar la GUI para refrescar las metricas##

## Visualización
La GUI muestra:
- Grafos de latencia/ancho de banda
- MST
- Rutas óptimas calculadas
- Panel de transferencia de archivos
