import { describe, expect, test } from "vitest";

import { buildGuidedGraph } from "./workflows";

describe("buildGuidedGraph", () => {
  test("creates the executable four-node NDVI graph", () => {
    const graph = buildGuidedGraph({
      aoiId: "4f145787-1977-4ade-af52-65d680c6d9fb",
      dataset: "sentinel-2-l2a",
      dateFrom: "2026-06-01",
      dateTo: "2026-06-30",
      cloudCoverMax: 20,
      operation: "ndvi",
      colorRamp: "rdylgn",
      minimum: -1,
      maximum: 1,
      opacity: 0.8,
    });

    expect(graph.nodes.map((node) => node.type)).toEqual([
      "aoi",
      "dataset",
      "operation",
      "visualization",
    ]);
    expect(graph.edges).toHaveLength(4);
    expect(graph.nodes[2].config).toEqual({
      operation: "ndvi",
      parameters: {},
    });
  });

  test("preserves source and visualization choices", () => {
    const graph = buildGuidedGraph({
      aoiId: "4f145787-1977-4ade-af52-65d680c6d9fb",
      dataset: "sentinel-2-l2a",
      dateFrom: "2026-06-01",
      dateTo: "2026-06-30",
      cloudCoverMax: 12,
      operation: "ndvi",
      colorRamp: "viridis",
      minimum: -0.5,
      maximum: 0.9,
      opacity: 0.7,
    });

    expect(graph.nodes[1].config).toEqual({
      dataset: "sentinel-2-l2a",
      date_from: "2026-06-01",
      date_to: "2026-06-30",
      cloud_cover_max: 12,
    });
    expect(graph.nodes[3].config).toEqual({
      color_ramp: "viridis",
      min: -0.5,
      max: 0.9,
      opacity: 0.7,
    });
  });
});
