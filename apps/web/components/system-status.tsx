"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "ready" | "unavailable";

export function SystemStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const controller = new AbortController();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

    fetch(`${apiUrl}/api/v1/health/ready`, { signal: controller.signal })
      .then((response) => setStatus(response.ok ? "ready" : "unavailable"))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setStatus("unavailable");
      });

    return () => controller.abort();
  }, []);

  const copy = {
    checking: ["Checking services", "Connecting to the GeoFlow API"],
    ready: ["All systems ready", "API, PostGIS, and Redis are connected"],
    unavailable: ["Services starting", "The API dependencies are not ready yet"],
  } satisfies Record<Status, [string, string]>;

  return (
    <aside className="statusCard" aria-live="polite">
      <div className={`statusOrb ${status}`} aria-hidden="true">
        <span />
      </div>
      <p className="statusLabel">Live environment</p>
      <h2>{copy[status][0]}</h2>
      <p>{copy[status][1]}</p>
      <dl>
        <div>
          <dt>API</dt>
          <dd>FastAPI</dd>
        </div>
        <div>
          <dt>Queue</dt>
          <dd>Celery</dd>
        </div>
        <div>
          <dt>Spatial</dt>
          <dd>PostGIS</dd>
        </div>
      </dl>
    </aside>
  );
}

