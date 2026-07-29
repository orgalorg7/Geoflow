export interface WorkflowSummary {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowNode {
  id?: string;
  key: string;
  type: string;
  config: Record<string, unknown>;
}

export interface WorkflowEdge {
  id?: string;
  source: string;
  source_port: string;
  target: string;
  target_port: string;
}

export interface WorkflowGraph extends WorkflowSummary {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

export interface WorkflowValidationIssue {
  code: string;
  message: string;
  node_key: string | null;
  edge_index: number | null;
}

export interface WorkflowValidation {
  valid: boolean;
  executable: boolean;
  errors: WorkflowValidationIssue[];
}

export interface WorkflowDefinitions {
  node_types: Array<{
    type: string;
    label: string;
    required_inputs: string[];
    outputs: string[];
  }>;
  datasets: Array<{ id: string; label: string; bands: string[] }>;
  operations: Array<{
    id: string;
    label: string;
    required_bands: string[];
    parameters: Record<string, Record<string, unknown>>;
  }>;
  visualization_ramps: Array<{ id: string; label: string }>;
  connections: Array<{
    source_type: string;
    source_port: string;
    target_type: string;
    target_port: string;
  }>;
}

export interface GuidedWorkflowValues {
  aoiId: string;
  dataset: string;
  dateFrom: string;
  dateTo: string;
  cloudCoverMax: number;
  operation: string;
  colorRamp: string;
  minimum: number;
  maximum: number;
  opacity: number;
}

export function buildGuidedGraph(values: GuidedWorkflowValues): {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
} {
  return {
    nodes: [
      {
        key: "aoi",
        type: "aoi",
        config: { aoi_id: values.aoiId },
      },
      {
        key: "dataset",
        type: "dataset",
        config: {
          dataset: values.dataset,
          date_from: values.dateFrom,
          date_to: values.dateTo,
          cloud_cover_max: values.cloudCoverMax,
        },
      },
      {
        key: "operation",
        type: "operation",
        config: { operation: values.operation, parameters: {} },
      },
      {
        key: "visualization",
        type: "visualization",
        config: {
          color_ramp: values.colorRamp,
          min: values.minimum,
          max: values.maximum,
          opacity: values.opacity,
        },
      },
    ],
    edges: [
      {
        source: "aoi",
        source_port: "geometry",
        target: "dataset",
        target_port: "aoi",
      },
      {
        source: "aoi",
        source_port: "geometry",
        target: "operation",
        target_port: "aoi",
      },
      {
        source: "dataset",
        source_port: "raster",
        target: "operation",
        target_port: "raster",
      },
      {
        source: "operation",
        source_port: "raster",
        target: "visualization",
        target_port: "raster",
      },
    ],
  };
}
