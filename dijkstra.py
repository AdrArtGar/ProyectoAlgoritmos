import networkx as nx

def dijkstra(grafo, origen, destino):
    # Convertimos el grafo a un diccionario simple
    distancias = {nodo: float('inf') for nodo in grafo.nodes}
    previos = {nodo: None for nodo in grafo.nodes}
    distancias[origen] = 0
    visitados = set()

    while len(visitados) < len(grafo.nodes):
        nodo_actual = min((n for n in grafo.nodes if n not in visitados), key=lambda n: distancias[n], default=None)
        if nodo_actual is None or distancias[nodo_actual] == float('inf'):
            break
        visitados.add(nodo_actual)

        for vecino in grafo[nodo_actual]:
            peso = grafo[nodo_actual][vecino].get('weight', 1)
            nueva_dist = distancias[nodo_actual] + peso
            if nueva_dist < distancias[vecino]:
                distancias[vecino] = nueva_dist
                previos[vecino] = nodo_actual

    # Reconstruir camino
    if distancias[destino] == float('inf'):
        return None, float('inf')

    camino = []
    nodo = destino
    while nodo:
        camino.insert(0, nodo)
        nodo = previos[nodo]
    
    return camino, distancias[destino]