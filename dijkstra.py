import networkx as nx
import heapq

def dijkstra(grafo, origen, destino):
    distancias = {nodo: float('inf') for nodo in grafo.nodes}
    previos = {nodo: None for nodo in grafo.nodes}
    distancias[origen] = 0

    # Cola de prioridad con heapq
    heap = [(0, origen)]
    visitados = set()

    while heap:
        distancia_actual, nodo_actual = heapq.heappop(heap)

        if nodo_actual in visitados:
            continue
        visitados.add(nodo_actual)

        if nodo_actual == destino:
            break

        for vecino in grafo[nodo_actual]:
            peso = grafo[nodo_actual][vecino].get('weight', 1)
            nueva_dist = distancia_actual + peso
            if nueva_dist < distancias[vecino]:
                distancias[vecino] = nueva_dist
                previos[vecino] = nodo_actual
                heapq.heappush(heap, (nueva_dist, vecino))

    # Reconstrucción del camino
    if distancias[destino] == float('inf'):
        return None, float('inf')

    camino = []
    nodo = destino
    while nodo:
        camino.insert(0, nodo)
        nodo = previos[nodo]

    return camino, distancias[destino]
