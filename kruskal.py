import networkx as nx

def kruskal(grafo):
    # Lista de aristas con sus pesos reales
    edges = [(u, v, d['weight']) for u, v, d in grafo.to_undirected().edges(data=True)]
    edges.sort(key=lambda x: x[2])  # Ordenar por peso

    parent = {}
    def find(n):
        while parent[n] != n:
            parent[n] = parent[parent[n]]
            n = parent[n]
        return n

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
            return True
        return False

    # Inicializar conjuntos
    for nodo in grafo.nodes:
        parent[nodo] = nodo

    mst_edges = []
    for u, v, peso in edges:
        if union(u, v):
            mst_edges.append((u, v, peso))

    # Construir nuevo grafo MST
    mst = nx.Graph()
    for nodo in grafo.nodes:
        mst.add_node(nodo)

    for u, v, peso in mst_edges:
        datos_originales = grafo.get_edge_data(u, v) or grafo.get_edge_data(v, u)
        mst.add_edge(u, v, **datos_originales)

    return mst