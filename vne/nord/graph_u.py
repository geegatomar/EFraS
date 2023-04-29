import numpy as np


class Graph:
    def __init__(self, nodes, edges, neighbours, node_weights, edge_weights) -> None:
        self.nodes = nodes
        self.edges = edges
        self.neighbours = neighbours
        self.node_weights = node_weights  # CRB
        self.edge_weights = edge_weights  # BandWidth
