import Link from "next/link";

import { SystemStatus } from "@/components/system-status";

const foundations = [
  ["Web application", "Next.js and strict TypeScript"],
  ["Application API", "FastAPI with generated OpenAPI docs"],
  ["Background jobs", "Celery workers backed by Redis"],
  ["Spatial database", "PostgreSQL with the PostGIS extension"],
];

export default function Home() {
  return (
    <main>
      <nav aria-label="Primary navigation">
        <Link className="brand" href="/">
          <span className="brandMark" aria-hidden="true">
            G
          </span>
          GeoFlow
        </Link>
        <div className="homeActions">
          <span className="phase">Authentication · Phase 2</span>
          <Link className="navLink" href="/login">
            Sign in
          </Link>
          <Link className="navButton" href="/register">
            Create account
          </Link>
        </div>
      </nav>

      <section className="hero">
        <div>
          <p className="eyebrow">No-code earth intelligence</p>
          <h1>Turn an area on the map into an answer.</h1>
          <p className="lede">
            GeoFlow is being built for people who need satellite insight without
            writing geospatial code. Create a secure account to enter your
            protected workspace.
          </p>
          <div className="heroActions">
            <Link className="docsLink" href="/register">
              Start with GeoFlow
              <span aria-hidden="true">→</span>
            </Link>
            <Link className="secondaryLink" href="/login">
              Sign in
            </Link>
          </div>
        </div>
        <SystemStatus />
      </section>

      <section className="foundation" aria-labelledby="foundation-heading">
        <div>
          <p className="eyebrow">System foundation</p>
          <h2 id="foundation-heading">Built for real processing.</h2>
        </div>
        <div className="foundationGrid">
          {foundations.map(([title, detail], index) => (
            <article key={title}>
              <span>0{index + 1}</span>
              <h3>{title}</h3>
              <p>{detail}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
