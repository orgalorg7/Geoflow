"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";
import type { AreaOfInterest, Position, Project } from "@/lib/projects";
import type { WorkflowSummary } from "@/lib/workflows";

const ProjectMap = dynamic(() => import("@/components/project-map"), {
  ssr: false,
});

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const { loading, user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [aois, setAois] = useState<AreaOfInterest[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [drawing, setDrawing] = useState(false);
  const [draft, setDraft] = useState<Position[]>([]);
  const [aoiName, setAoiName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  useEffect(() => {
    if (!user || !projectId) return;
    let active = true;
    Promise.all([
      apiRequest<Project>(`/projects/${projectId}`),
      apiRequest<AreaOfInterest[]>(`/projects/${projectId}/aois`),
      apiRequest<WorkflowSummary[]>(`/projects/${projectId}/workflows`),
    ])
      .then(([projectResult, aoiResult, workflowResult]) => {
        if (!active) return;
        setProject(projectResult);
        setAois(aoiResult);
        setWorkflows(workflowResult);
      })
      .catch((caught: unknown) => {
        if (active)
          setError(
            caught instanceof Error
              ? caught.message
              : "Project failed to load.",
          );
      })
      .finally(() => {
        if (active) setPageLoading(false);
      });
    return () => {
      active = false;
    };
  }, [projectId, user]);

  const draftAreaHint = useMemo(
    () =>
      draft.length < 3
        ? `${draft.length}/3 minimum vertices`
        : `${draft.length} vertices`,
    [draft.length],
  );

  function beginDrawing() {
    setEditingId(null);
    setDraft([]);
    setAoiName("");
    setError("");
    setDrawing(true);
  }

  function beginEditing(aoi: AreaOfInterest) {
    const ring = aoi.geometry.coordinates[0] ?? [];
    setEditingId(aoi.id);
    setAoiName(aoi.name);
    setDraft(ring.slice(0, -1).map(([lng, lat]) => [lng, lat]));
    setDrawing(true);
    setError("");
  }

  function cancelDrawing() {
    setDrawing(false);
    setEditingId(null);
    setDraft([]);
    setAoiName("");
  }

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (draft.length < 3) {
      setError("Draw at least three vertices before saving the AOI.");
      return;
    }
    setSaving(true);
    setError("");
    const geometry = {
      type: "Polygon",
      coordinates: [[...draft, draft[0]]],
    };
    try {
      const path = editingId
        ? `/projects/${projectId}/aois/${editingId}`
        : `/projects/${projectId}/aois`;
      const saved = await apiRequest<AreaOfInterest>(path, {
        method: editingId ? "PATCH" : "POST",
        body: JSON.stringify({ name: aoiName, geometry }),
      });
      setAois((current) =>
        editingId
          ? current.map((aoi) => (aoi.id === editingId ? saved : aoi))
          : [saved, ...current],
      );
      cancelDrawing();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "AOI could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function uploadGeoJSON(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setError("Choose a GeoJSON file first.");
      return;
    }
    const form = new FormData(event.currentTarget);
    form.set("file", file);
    setSaving(true);
    setError("");
    try {
      const saved = await apiRequest<AreaOfInterest>(
        `/projects/${projectId}/aois/upload`,
        { method: "POST", body: form },
      );
      setAois((current) => [saved, ...current]);
      event.currentTarget.reset();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "GeoJSON upload failed.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function deleteAOI(aoi: AreaOfInterest) {
    if (!window.confirm(`Delete the “${aoi.name}” area?`)) return;
    try {
      await apiRequest<void>(`/projects/${projectId}/aois/${aoi.id}`, {
        method: "DELETE",
      });
      setAois((current) => current.filter((item) => item.id !== aoi.id));
      if (editingId === aoi.id) cancelDrawing();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "AOI deletion failed.",
      );
    }
  }

  async function deleteWorkflow(workflow: WorkflowSummary) {
    if (!window.confirm(`Delete the “${workflow.name}” workflow?`)) return;
    try {
      await apiRequest<void>(
        `/projects/${projectId}/workflows/${workflow.id}`,
        { method: "DELETE" },
      );
      setWorkflows((current) =>
        current.filter((item) => item.id !== workflow.id),
      );
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Workflow deletion failed.",
      );
    }
  }

  if (loading || pageLoading) {
    return (
      <main className="centeredState">
        <span className="loadingDot" />
        Opening project…
      </main>
    );
  }

  if (!user) return null;

  if (!project) {
    return (
      <main className="centeredState errorState">
        <p>{error || "Project not found."}</p>
        <Link href="/dashboard">Return to projects</Link>
      </main>
    );
  }

  return (
    <main className="projectWorkspace">
      <header className="projectTopbar">
        <Link className="brand" href="/dashboard">
          <span className="brandMark">G</span>
          GeoFlow
        </Link>
        <div>
          <span>Project</span>
          <strong>{project.name}</strong>
        </div>
        <Link className="textLink" href="/dashboard">
          All projects
        </Link>
      </header>

      <div className="mapWorkspace">
        <section className="mapPanel">
          <ProjectMap
            aois={aois}
            draft={draft}
            drawing={drawing}
            onDraftChange={setDraft}
          />
          <div className="mapStatus">
            <span className={drawing ? "active" : ""} />
            {drawing
              ? "Drawing mode · click map to add vertices"
              : `${aois.length} saved areas`}
          </div>
        </section>

        <aside className="projectSidebar">
          <div className="sidebarHeading">
            <p className="eyebrow">Area of interest</p>
            <h1>{project.name}</h1>
            {project.description && <p>{project.description}</p>}
          </div>

          {error && (
            <p className="workspaceError" role="alert">
              {error}
            </p>
          )}

          {drawing ? (
            <form className="aoiEditor" onSubmit={saveDraft}>
              <div className="editorHeader">
                <h2>{editingId ? "Edit area" : "Draw an area"}</h2>
                <button onClick={cancelDrawing} type="button">
                  Cancel
                </button>
              </div>
              <p>
                Click the map to add points. Drag a point to refine the
                boundary.
              </p>
              <label>
                Area name
                <input
                  maxLength={120}
                  minLength={2}
                  onChange={(event) => setAoiName(event.target.value)}
                  required
                  value={aoiName}
                />
              </label>
              <div className="vertexControls">
                <span>{draftAreaHint}</span>
                <button
                  disabled={draft.length === 0}
                  onClick={() => setDraft((current) => current.slice(0, -1))}
                  type="button"
                >
                  Undo point
                </button>
                <button
                  disabled={draft.length === 0}
                  onClick={() => setDraft([])}
                  type="button"
                >
                  Clear
                </button>
              </div>
              <button
                className="primaryButton"
                disabled={saving || draft.length < 3}
                type="submit"
              >
                {saving
                  ? "Validating…"
                  : editingId
                    ? "Save changes"
                    : "Save area"}
              </button>
            </form>
          ) : (
            <>
              <div className="aoiActions">
                <button
                  className="primaryButton"
                  onClick={beginDrawing}
                  type="button"
                >
                  Draw polygon
                </button>
                <span>or upload a GeoJSON polygon</span>
                <form onSubmit={uploadGeoJSON}>
                  <input
                    accept=".geojson,.json,application/geo+json,application/json"
                    name="file"
                    ref={fileInputRef}
                    required
                    type="file"
                  />
                  <input
                    maxLength={120}
                    minLength={2}
                    name="name"
                    placeholder="Uploaded area name"
                    required
                  />
                  <button disabled={saving} type="submit">
                    {saving ? "Uploading…" : "Upload GeoJSON"}
                  </button>
                </form>
              </div>

              <section className="savedAois">
                <div className="sectionHeading">
                  <h2>Saved areas</h2>
                  <span>{aois.length}</span>
                </div>
                {aois.length === 0 ? (
                  <p className="sidebarEmpty">
                    No areas yet. Draw one directly on the map.
                  </p>
                ) : (
                  <div className="aoiList">
                    {aois.map((aoi) => (
                      <article key={aoi.id}>
                        <div>
                          <h3>{aoi.name}</h3>
                          <p>
                            {aoi.area_sq_km.toLocaleString(undefined, {
                              maximumFractionDigits: 2,
                            })}{" "}
                            km²
                          </p>
                        </div>
                        <div>
                          <button
                            onClick={() => beginEditing(aoi)}
                            type="button"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => void deleteAOI(aoi)}
                            type="button"
                          >
                            Delete
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>

              <section className="savedWorkflows">
                <div className="sectionHeading">
                  <h2>Analysis workflows</h2>
                  <span>{workflows.length}</span>
                </div>
                <Link
                  className={`workflowCreateLink ${aois.length === 0 ? "disabled" : ""}`}
                  href={
                    aois.length > 0
                      ? `/projects/${projectId}/workflows/new`
                      : "#"
                  }
                  aria-disabled={aois.length === 0}
                >
                  <span>+</span>
                  {aois.length > 0
                    ? "Configure a workflow"
                    : "Save an AOI to build a workflow"}
                </Link>
                {workflows.length > 0 && (
                  <div className="workflowList">
                    {workflows.map((workflow) => (
                      <article key={workflow.id}>
                        <div>
                          <h3>{workflow.name}</h3>
                          <p>
                            Updated{" "}
                            {new Date(workflow.updated_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div>
                          <Link
                            href={`/projects/${projectId}/workflows/${workflow.id}`}
                          >
                            Edit
                          </Link>
                          <button
                            onClick={() => void deleteWorkflow(workflow)}
                            type="button"
                          >
                            Delete
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
