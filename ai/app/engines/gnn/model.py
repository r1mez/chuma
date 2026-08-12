"""Faithful PyTorch implementation of PengLinzhi/DyGKT model components.

The code preserves the original computational graph: ``TimeDualDecayEncoder``,
``feature_Linear`` / edge / time / struct projections, two ``DyKT_Seq`` GRUs,
a shared output layer, and the two-layer ``MergeLayer`` classifier. The
external DyGLib neighbor sampler is represented by the local course-isolated
student-knowledge ``TemporalBipartiteGraph`` adapter.
"""

from __future__ import annotations

from typing import Iterable

from app.engines.gnn.graph import DyGKTTarget, TemporalBipartiteGraph


def require_torch():
    """Import PyTorch lazily so API startup supports explicit cold start."""

    try:
        import torch
        from torch import nn
    except ImportError as exc:  # pragma: no cover - depends on deployment image
        raise RuntimeError("DyGKT neural inference requires PyTorch in the AI-service environment.") from exc
    return torch, nn


def build_tgnn_model(
    node_raw_features: list[list[float]],
    edge_raw_features: list[float],
    time_dim: int = 16,
    num_neighbors: int = 50,
    ablation: str = "-1",
    dropout: float = 0.5,
):
    """Build the original DyGKT backbone plus its original MergeLayer head."""

    torch, nn = require_torch()

    def initial_time_weight(out_features: int, in_features: int = 1):
        """Use the exact original geometric initializer and matrix shape."""

        values = 1 / 10 ** torch.linspace(
            0, 9, out_features * in_features, dtype=torch.float32
        )
        return values.reshape(out_features, in_features)

    class TimeEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.w = nn.Linear(1, time_dim)
            self.w.weight = nn.Parameter(initial_time_weight(time_dim))
            self.w.bias = nn.Parameter(torch.zeros(time_dim))

        def forward(self, timestamps):
            return torch.cos(self.w(timestamps.unsqueeze(2)))

    class TimeDualDecayEncoder(nn.Module):
        """Exact original branch convention and one-day threshold."""

        def __init__(self):
            super().__init__()
            self.w_short = nn.Linear(1, time_dim)
            self.w_long = nn.Linear(1, time_dim)
            self.w_short.weight = nn.Parameter(initial_time_weight(time_dim))
            self.w_short.bias = nn.Parameter(torch.zeros(time_dim))
            self.w_long.weight = nn.Parameter(initial_time_weight(time_dim))
            self.w_long.bias = nn.Parameter(torch.zeros(time_dim))
            self.f = nn.ReLU()
            self.w_o = nn.Linear(time_dim, time_dim)
            self.w_o.weight = nn.Parameter(initial_time_weight(time_dim, time_dim))
            self.w_o.bias = nn.Parameter(torch.zeros(time_dim))

        def forward(self, timestamps):
            timestamps = timestamps.unsqueeze(2)
            timestamps_right = torch.cat(
                [timestamps[:, 1:, :], timestamps[:, -1, :].unsqueeze(1)], dim=1
            )
            timestamps_diff = timestamps_right - timestamps
            timestamps_mask = (timestamps_diff > 3600 * 24).float()
            timestamps_short = self.f(self.w_short(timestamps_diff * timestamps_mask))
            timestamps_long = self.f(self.w_long(timestamps_diff * (1 - timestamps_mask)))
            return self.w_o(timestamps_short + timestamps_long)

    class DyKTSeq(nn.Module):
        def __init__(self):
            super().__init__()
            # Kept for parameter-level compatibility with the original class.
            self.patch_enc_layer = nn.Linear(64, 64)
            self.hid_node_updater = nn.GRU(input_size=64, hidden_size=64, batch_first=True)

        def update(self, values):
            _, hidden = self.hid_node_updater(values)
            return torch.squeeze(hidden, dim=0)

    class MergeLayer(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = nn.Linear(128, 64)
            self.fc2 = nn.Linear(64, 1)
            self.act = nn.ReLU()

        def forward(self, input_1, input_2):
            return self.fc2(self.act(self.fc1(torch.cat([input_1, input_2], dim=1))))

    class OriginalDyGKT(nn.Module):
        node_dim = 64
        edge_dim = 64

        def __init__(self):
            super().__init__()
            self.num_neighbors = num_neighbors
            self.ablation = ablation
            # Graph data varies between online calls, therefore these buffers
            # intentionally do not enter the learned checkpoint.
            self.register_buffer("node_raw_features", torch.tensor(node_raw_features, dtype=torch.float32), persistent=False)
            self.register_buffer("edge_raw_features", torch.tensor(edge_raw_features, dtype=torch.float32), persistent=False)
            self.projection_layer = nn.ModuleDict({
                "feature_Linear": nn.Linear(len(node_raw_features[0]), 64, bias=True),
                "edge": nn.Linear(1, 64, bias=True),
                "time": nn.Linear(time_dim, 64, bias=True),
                "struct": nn.Linear(1, 64, bias=True),
            })
            self.output_layer = nn.Linear(64, 64, bias=True)
            self.src_node_updater = DyKTSeq()
            self.dst_node_updater = DyKTSeq()
            self.time_encoder = TimeEncoder() if ablation == "dual" else TimeDualDecayEncoder()
            self.link_predictor = MergeLayer()
            self.graph: TemporalBipartiteGraph | None = None
            self.model_config = {
                "time_dim": time_dim,
                "num_neighbors": num_neighbors,
                "ablation": ablation,
                "dropout": dropout,
                "implementation": "PengLinzhi/DyGKT-main",
            }

        def set_neighbor_sampler(self, graph: TemporalBipartiteGraph):
            self.graph = graph

        def _refresh_graph_features(self, graph: TemporalBipartiteGraph):
            device = next(self.parameters()).device
            self.node_raw_features = torch.tensor(graph.node_raw_features, dtype=torch.float32, device=device)
            self.edge_raw_features = torch.tensor(graph.edge_raw_features, dtype=torch.float32, device=device)
            self.set_neighbor_sampler(graph)

        def get_features(self, node_interact_times, neighbor_edge_ids, neighbor_node_ids, neighbor_times):
            device = next(self.parameters()).device
            node_ids = torch.tensor(neighbor_node_ids, dtype=torch.long, device=device)
            edge_ids = torch.tensor(neighbor_edge_ids, dtype=torch.long, device=device)
            times = torch.tensor(neighbor_times, dtype=torch.float32, device=device)
            interaction_times = torch.tensor(node_interact_times, dtype=torch.float32, device=device)
            node_features = self.projection_layer["feature_Linear"](self.node_raw_features[node_ids])
            if self.ablation == "dual":
                time_features = self.time_encoder(interaction_times[:, None] - times)
            else:
                time_features = self.time_encoder(times)
            time_features = self.projection_layer["time"](time_features)
            # Same as the original model: only the first raw edge feature is
            # projected for DyGKT's answer-performance representation.
            edge_features = self.projection_layer["edge"](
                self.edge_raw_features[edge_ids][:, :, 0].unsqueeze(-1)
            )
            if self.ablation == "time":
                time_features *= 0
            elif self.ablation == "skill":
                node_features *= 0
            return node_features, edge_features, time_features

        def compute_src_dst_node_temporal_embeddings(self, targets: Iterable[DyGKTTarget]):
            if self.graph is None:
                raise RuntimeError("DyGKT neighbor sampler was not configured")
            targets = list(targets)
            if not targets:
                return torch.empty((0, 64)), torch.empty((0, 64))
            source_ids = [target.student_node_id for target in targets]
            destination_ids = [target.knowledge_node_id for target in targets]
            interaction_times = [target.timestamp for target in targets]
            src_neighbor_ids, src_neighbor_edge_ids, src_neighbor_times = self.graph.get_historical_neighbors(
                source_ids, interaction_times, self.num_neighbors
            )
            dst_neighbor_ids, dst_neighbor_edge_ids, dst_neighbor_times = self.graph.get_historical_neighbors(
                destination_ids, interaction_times, self.num_neighbors
            )
            # Original implementation appends the node itself, a padding edge
            # id and the current timestamp to both neighbourhood sequences.
            src_nodes = [neighbors + [source] for neighbors, source in zip(src_neighbor_ids, source_ids)]
            src_edges = [edges + [0] for edges in src_neighbor_edge_ids]
            src_times = [times + [now] for times, now in zip(src_neighbor_times, interaction_times)]
            dst_nodes = [neighbors + [destination] for neighbors, destination in zip(dst_neighbor_ids, destination_ids)]
            dst_edges = [edges + [0] for edges in dst_neighbor_edge_ids]
            dst_times = [times + [now] for times, now in zip(dst_neighbor_times, interaction_times)]

            device = next(self.parameters()).device
            src_tensor = torch.tensor(src_nodes, dtype=torch.long, device=device)
            dst_tensor = torch.tensor(dst_nodes, dtype=torch.long, device=device)
            source_tensor = torch.tensor(source_ids, dtype=torch.long, device=device)
            destination_tensor = torch.tensor(destination_ids, dtype=torch.long, device=device)
            src_counter = (src_tensor[:, :-1] == destination_tensor.unsqueeze(1)).unsqueeze(-1).float()
            dst_counter = (dst_tensor[:, :-1] == source_tensor.unsqueeze(1)).unsqueeze(-1).float()
            src_skill = self.node_raw_features[src_tensor][:, :-1, 0].long()
            dst_skill = self.node_raw_features[dst_tensor][:, -1, 0].long().unsqueeze(1).repeat(1, self.num_neighbors)
            src_skill_counter = (src_skill == dst_skill).unsqueeze(-1).float()
            counter_enabled = 0 if self.ablation == "counter" else 1
            src_counter_features = self.projection_layer["struct"](counter_enabled * src_counter)
            dst_counter_features = self.projection_layer["struct"](counter_enabled * dst_counter)
            src_skill_features = self.projection_layer["struct"](counter_enabled * src_skill_counter)

            src_node_features, src_edge_features, src_time_features = self.get_features(
                interaction_times, src_edges, src_nodes, src_times
            )
            dst_node_features, dst_edge_features, dst_time_features = self.get_features(
                interaction_times, dst_edges, dst_nodes, dst_times
            )
            src_features = src_node_features + src_edge_features + src_time_features
            dst_features = dst_node_features + dst_edge_features + dst_time_features
            src_embeddings = self.src_node_updater.update(
                src_features[:, :-1, :] + src_skill_features + src_counter_features
            ) + (src_edge_features + src_time_features)[:, -1, :]
            if self.ablation in {"q_qid", "q_kid"}:
                dst_embeddings = dst_node_features[:, -1]
            else:
                dst_embeddings = self.dst_node_updater.update(
                    (dst_edge_features + dst_time_features)[:, :-1, :] + dst_counter_features
                ) + dst_features[:, -1, :]
            return self.output_layer(src_embeddings), self.output_layer(dst_embeddings)

        def forward(self, targets: Iterable[DyGKTTarget], graph: TemporalBipartiteGraph | None = None):
            if graph is not None:
                self._refresh_graph_features(graph)
            src_embeddings, dst_embeddings = self.compute_src_dst_node_temporal_embeddings(targets)
            return self.link_predictor(src_embeddings, dst_embeddings).squeeze(-1)

    return OriginalDyGKT()
