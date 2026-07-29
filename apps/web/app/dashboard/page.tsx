"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { apiRequest } from "@/lib/api";
import type { Project } from "@/lib/projects";

export default function DashboardPage() {
  const router = useRouter();
  const { loading, logout, user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  useEffect(() => {
    if (!user) return;
    let active = true;
    apiRequest<Project[]>("/projects")
      .then((result) => {
        if (active) setProjects(result);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Projects could not load.");
        }
      })
      .finally(() => {
        if (active) setProjectsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [user]);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const project = await apiRequest<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({
          name: String(form.get("name")),
          description: String(form.get("description")) || null,
        }),
      });
      setProjects((current) => [project, ...current]);
      setShowForm(false);
      router.push(`/projects/${project.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Project creation failed.");
    } finally {
      setCreating(false);
    }
  }

  async function deleteProject(project: Project) {
    if (!window.confirm(`Delete “${project.name}” and all of its AOIs?`)) return;
    try {
      await apiRequest<void>(`/projects/${project.id}`, { method: "DELETE" });
      setProjects((current) => current.filter((item) => item.id !== project.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Project deletion failed.");
    }
  }

  if (loading || projectsLoading) {
    return (
      <main className="centeredState" aria-live="polite">
        <span className="loadingDot" />
        Loading your projects…
      </main>
    );
  }

  if (!user) return null;

  return (
    <main className="dashboardPage">
      <nav aria-label="Dashboard navigation">
        <Link className="brand" href="/">
          <span className="brandMark" aria-hidden="true">
            G
          </span>
          GeoFlow
        </Link>
        <div className="accountNav">
          <span>{user.email}</span>
          <button
            className="textButton"
            onClick={() => void logout().then(() => router.replace("/login"))}
            type="button"
          >
            Log out
          </button>
        </div>
      </nav>

      <section className="workspaceHeader">
        <div>
          <p className="eyebrow">Project workspace</p>
          <h1>Good to see you, {user.full_name.split(" ")[0]}.</h1>
          <p>Create a project, then draw or upload its geographic area of interest.</p>
        </div>
        <button
          className="primaryButton compactButton"
          onClick={() => setShowForm((current) => !current)}
          type="button"
        >
          {showForm ? "Cancel" : "New project"}
        </button>
      </section>

      {showForm && (
        <section className="projectComposer">
          <form onSubmit={createProject}>
            <label>
              Project name
              <input name="name" minLength={2} maxLength={120} required />
            </label>
            <label>
              Description <span>Optional</span>
              <textarea name="description" maxLength={2000} rows={3} />
            </label>
            <button className="primaryButton" disabled={creating} type="submit">
              {creating ? "Creating…" : "Create and open project"}
            </button>
          </form>
        </section>
      )}

      {error && (
        <p className="workspaceError" role="alert">
          {error}
        </p>
      )}

      <section className="projectSection" aria-labelledby="projects-heading">
        <div className="sectionHeading">
          <h2 id="projects-heading">Your projects</h2>
          <span>{projects.length} total</span>
        </div>

        {projects.length === 0 ? (
          <div className="projectEmpty">
            <span aria-hidden="true">⌖</span>
            <h3>No projects yet</h3>
            <p>Create your first project to begin defining an area on the map.</p>
            <button className="textButton" onClick={() => setShowForm(true)} type="button">
              Create a project →
            </button>
          </div>
        ) : (
          <div className="projectGrid">
            {projects.map((project, index) => (
              <article className="projectCard" key={project.id}>
                <div className="projectNumber">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div>
                  <p>{new Date(project.updated_at).toLocaleDateString()}</p>
                  <h3>{project.name}</h3>
                  <span>{project.description || "No description provided."}</span>
                </div>
                <div className="projectCardActions">
                  <Link href={`/projects/${project.id}`}>Open project →</Link>
                  <button onClick={() => void deleteProject(project)} type="button">
                    Delete
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
