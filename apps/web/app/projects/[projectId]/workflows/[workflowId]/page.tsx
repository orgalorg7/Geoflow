"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";
import type { AreaOfInterest, Project } from "@/lib/projects";
import {
  buildGuidedGraph,
  type WorkflowDefinitions,
  type WorkflowGraph,
  type WorkflowSummary,
  type WorkflowValidation,
} from "@/lib/workflows";

interface FormValues {
  name: string;
  description: string;
  aoiId: string;
  dataset: string;
  dateFrom: string;
  dateTo: string;
  cloudCover: string;
  operation: string;
  colorRamp: string;
  minimum: string;
  maximum: string;
  opacity: string;
}

const initialValues: FormValues = {
  name: "NDVI analysis",
  description: "",
  aoiId: "",
  dataset: "sentinel-2-l2a",
  dateFrom: "",
  dateTo: "",
  cloudCover: "20",
  operation: "ndvi",
  colorRamp: "rdylgn",
  minimum: "-1",
  maximum: "1",
  opacity: "0.85",
};

export default function WorkflowBuilderPage() {
  const { projectId, workflowId } = useParams<{
    projectId: string;
    workflowId: string;
  }>();
  const router = useRouter();
  const { loading, user } = useAuth();
  const isNew = workflowId === "new";
  const [project, setProject] = useState<Project | null>(null);
  const [aois, setAois] = useState<AreaOfInterest[]>([]);
  const [definitions, setDefinitions] = useState<WorkflowDefinitions | null>(
    null,
  );
  const [values, setValues] = useState<FormValues>(initialValues);
  const [pageLoading, setPageLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<WorkflowValidation | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  useEffect(() => {
    if (!user || !projectId) return;
    let active = true;
    const requests: [
      Promise<Project>,
      Promise<AreaOfInterest[]>,
      Promise<WorkflowDefinitions>,
      Promise<WorkflowGraph | null>,
    ] = [
      apiRequest<Project>(`/projects/${projectId}`),
      apiRequest<AreaOfInterest[]>(`/projects/${projectId}/aois`),
      apiRequest<WorkflowDefinitions>("/workflow-definitions"),
      isNew
        ? Promise.resolve(null)
        : apiRequest<WorkflowGraph>(
            `/projects/${projectId}/workflows/${workflowId}`,
          ),
    ];
    Promise.all(requests)
      .then(([projectResult, aoiResult, definitionResult, workflow]) => {
        if (!active) return;
        setProject(projectResult);
        setAois(aoiResult);
        setDefinitions(definitionResult);
        if (workflow) setValues(valuesFromWorkflow(workflow));
        else if (aoiResult[0]) {
          setValues((current) => ({ ...current, aoiId: aoiResult[0].id }));
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(
            caught instanceof Error
              ? caught.message
              : "Workflow could not load.",
          );
        }
      })
      .finally(() => {
        if (active) setPageLoading(false);
      });
    return () => {
      active = false;
    };
  }, [isNew, projectId, user, workflowId]);

  const flowPreview = useMemo(
    () => [
      aois.find((aoi) => aoi.id === values.aoiId)?.name || "Select AOI",
      definitions?.datasets.find((item) => item.id === values.dataset)?.label ||
        "Dataset",
      definitions?.operations.find((item) => item.id === values.operation)
        ?.label || "Operation",
      definitions?.visualization_ramps.find(
        (item) => item.id === values.colorRamp,
      )?.label || "Visualization",
    ],
    [aois, definitions, values],
  );

  function setField(field: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setValidation(null);
  }

  async function saveWorkflow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setValidation(null);
    try {
      let id = workflowId;
      if (isNew) {
        const created = await apiRequest<WorkflowSummary>(
          `/projects/${projectId}/workflows`,
          {
            method: "POST",
            body: JSON.stringify({
              name: values.name,
              description: values.description || null,
            }),
          },
        );
        id = created.id;
      } else {
        await apiRequest<WorkflowSummary>(
          `/projects/${projectId}/workflows/${id}`,
          {
            method: "PATCH",
            body: JSON.stringify({
              name: values.name,
              description: values.description || null,
            }),
          },
        );
      }

      const graph = buildGuidedGraph({
        aoiId: values.aoiId,
        dataset: values.dataset,
        dateFrom: values.dateFrom,
        dateTo: values.dateTo,
        cloudCoverMax: Number(values.cloudCover),
        operation: values.operation,
        colorRamp: values.colorRamp,
        minimum: Number(values.minimum),
        maximum: Number(values.maximum),
        opacity: Number(values.opacity),
      });
      await apiRequest<WorkflowGraph>(
        `/projects/${projectId}/workflows/${id}/graph`,
        { method: "PUT", body: JSON.stringify(graph) },
      );
      const report = await apiRequest<WorkflowValidation>(
        `/projects/${projectId}/workflows/${id}/validate`,
        { method: "POST" },
      );
      setValidation(report);
      if (isNew) {
        router.replace(`/projects/${projectId}/workflows/${id}`);
      }
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Workflow save failed.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (loading || pageLoading) {
    return (
      <main className="centeredState">
        <span className="loadingDot" />
        Loading workflow builder…
      </main>
    );
  }

  if (!user) return null;

  if (!project || !definitions) {
    return (
      <main className="centeredState errorState">
        <p>{error || "Workflow builder could not be opened."}</p>
        <Link href={`/projects/${projectId}`}>Return to project</Link>
      </main>
    );
  }

  if (aois.length === 0) {
    return (
      <main className="workflowEmptyPage">
        <p className="eyebrow">AOI required</p>
        <h1>Define an area before building a workflow.</h1>
        <p>
          The dataset search and analysis operation both need a saved polygon.
        </p>
        <Link className="primaryButton" href={`/projects/${projectId}`}>
          Return to {project.name}
        </Link>
      </main>
    );
  }

  return (
    <main className="workflowBuilderPage">
      <header className="workflowTopbar">
        <Link className="brand" href={`/projects/${projectId}`}>
          <span className="brandMark">G</span>
          GeoFlow
        </Link>
        <div>
          <span>Guided workflow</span>
          <strong>{project.name}</strong>
        </div>
        <Link className="textLink" href={`/projects/${projectId}`}>
          Back to map
        </Link>
      </header>

      <section className="workflowHero">
        <div>
          <p className="eyebrow">No-code analysis builder</p>
          <h1>{isNew ? "Configure a workflow." : "Edit your workflow."}</h1>
          <p>
            Choose the source, date window, analysis, and visual treatment.
            GeoFlow stores these choices as a validated directed graph.
          </p>
        </div>
        <div className="flowPreview" aria-label="Workflow graph preview">
          {flowPreview.map((label, index) => (
            <div key={index}>
              <span>{index + 1}</span>
              <strong>{label}</strong>
              {index < flowPreview.length - 1 && <i>→</i>}
            </div>
          ))}
        </div>
      </section>

      <form className="guidedForm" onSubmit={saveWorkflow}>
        <section>
          <div className="formSectionNumber">01</div>
          <div className="formSectionContent">
            <h2>Workflow details</h2>
            <p>Name this repeatable analysis.</p>
            <div className="fieldGrid">
              <label>
                Workflow name
                <input
                  maxLength={120}
                  minLength={2}
                  onChange={(event) => setField("name", event.target.value)}
                  required
                  value={values.name}
                />
              </label>
              <label>
                Description
                <input
                  maxLength={2000}
                  onChange={(event) =>
                    setField("description", event.target.value)
                  }
                  value={values.description}
                />
              </label>
            </div>
          </div>
        </section>

        <section>
          <div className="formSectionNumber">02</div>
          <div className="formSectionContent">
            <h2>Source imagery</h2>
            <p>Select where and when GeoFlow should search.</p>
            <div className="fieldGrid">
              <label>
                Area of interest
                <select
                  onChange={(event) => setField("aoiId", event.target.value)}
                  required
                  value={values.aoiId}
                >
                  {aois.map((aoi) => (
                    <option key={aoi.id} value={aoi.id}>
                      {aoi.name} · {aoi.area_sq_km.toFixed(2)} km²
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Satellite dataset
                <select
                  onChange={(event) => setField("dataset", event.target.value)}
                  value={values.dataset}
                >
                  {definitions.datasets.map((dataset) => (
                    <option key={dataset.id} value={dataset.id}>
                      {dataset.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Start date
                <input
                  onChange={(event) => setField("dateFrom", event.target.value)}
                  required
                  type="date"
                  value={values.dateFrom}
                />
              </label>
              <label>
                End date
                <input
                  onChange={(event) => setField("dateTo", event.target.value)}
                  required
                  type="date"
                  value={values.dateTo}
                />
              </label>
              <label>
                Maximum cloud cover
                <div className="rangeField">
                  <input
                    max={100}
                    min={0}
                    onChange={(event) =>
                      setField("cloudCover", event.target.value)
                    }
                    type="range"
                    value={values.cloudCover}
                  />
                  <output>{values.cloudCover}%</output>
                </div>
              </label>
            </div>
          </div>
        </section>

        <section>
          <div className="formSectionNumber">03</div>
          <div className="formSectionContent">
            <h2>Analysis operation</h2>
            <p>Choose the calculation that will transform the source bands.</p>
            <div className="operationChoices">
              {definitions.operations.map((operation) => (
                <label
                  className={
                    values.operation === operation.id ? "selected" : ""
                  }
                  key={operation.id}
                >
                  <input
                    checked={values.operation === operation.id}
                    name="operation"
                    onChange={() => setField("operation", operation.id)}
                    type="radio"
                    value={operation.id}
                  />
                  <strong>{operation.label}</strong>
                  <span>{operation.required_bands.join(" + ")}</span>
                </label>
              ))}
            </div>
          </div>
        </section>

        <section>
          <div className="formSectionNumber">04</div>
          <div className="formSectionContent">
            <h2>Visualization</h2>
            <p>
              Set the initial preview style without changing analytical values.
            </p>
            <div className="fieldGrid">
              <label>
                Color ramp
                <select
                  onChange={(event) =>
                    setField("colorRamp", event.target.value)
                  }
                  value={values.colorRamp}
                >
                  {definitions.visualization_ramps.map((ramp) => (
                    <option key={ramp.id} value={ramp.id}>
                      {ramp.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Minimum value
                <input
                  onChange={(event) => setField("minimum", event.target.value)}
                  required
                  step="any"
                  type="number"
                  value={values.minimum}
                />
              </label>
              <label>
                Maximum value
                <input
                  onChange={(event) => setField("maximum", event.target.value)}
                  required
                  step="any"
                  type="number"
                  value={values.maximum}
                />
              </label>
              <label>
                Layer opacity
                <div className="rangeField">
                  <input
                    max={1}
                    min={0}
                    onChange={(event) =>
                      setField("opacity", event.target.value)
                    }
                    step={0.05}
                    type="range"
                    value={values.opacity}
                  />
                  <output>{Math.round(Number(values.opacity) * 100)}%</output>
                </div>
              </label>
            </div>
          </div>
        </section>

        {error && (
          <p className="workspaceError" role="alert">
            {error}
          </p>
        )}

        {validation && (
          <aside
            className={`validationResult ${validation.valid ? "valid" : "invalid"}`}
            aria-live="polite"
          >
            <div>
              <span>{validation.valid ? "✓" : "!"}</span>
              <div>
                <strong>
                  {validation.valid
                    ? "Workflow is executable"
                    : "Workflow needs attention"}
                </strong>
                <p>
                  {validation.valid
                    ? "All nodes, inputs, dates, bands, and parameters are valid."
                    : `${validation.errors.length} validation issues found.`}
                </p>
              </div>
            </div>
            {validation.errors.length > 0 && (
              <ul>
                {validation.errors.map((issue, index) => (
                  <li key={`${issue.code}-${index}`}>{issue.message}</li>
                ))}
              </ul>
            )}
          </aside>
        )}

        <footer className="builderFooter">
          <Link href={`/projects/${projectId}`}>Cancel</Link>
          <button className="primaryButton" disabled={saving} type="submit">
            {saving ? "Saving and validating…" : "Save and validate workflow"}
          </button>
        </footer>
      </form>
    </main>
  );
}

function valuesFromWorkflow(workflow: WorkflowGraph): FormValues {
  const aoi = workflow.nodes.find((node) => node.type === "aoi")?.config;
  const dataset = workflow.nodes.find(
    (node) => node.type === "dataset",
  )?.config;
  const operation = workflow.nodes.find(
    (node) => node.type === "operation",
  )?.config;
  const visualization = workflow.nodes.find(
    (node) => node.type === "visualization",
  )?.config;
  return {
    name: workflow.name,
    description: workflow.description ?? "",
    aoiId: String(aoi?.aoi_id ?? ""),
    dataset: String(dataset?.dataset ?? "sentinel-2-l2a"),
    dateFrom: String(dataset?.date_from ?? ""),
    dateTo: String(dataset?.date_to ?? ""),
    cloudCover: String(dataset?.cloud_cover_max ?? 20),
    operation: String(operation?.operation ?? "ndvi"),
    colorRamp: String(visualization?.color_ramp ?? "rdylgn"),
    minimum: String(visualization?.min ?? -1),
    maximum: String(visualization?.max ?? 1),
    opacity: String(visualization?.opacity ?? 0.85),
  };
}
