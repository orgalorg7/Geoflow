"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";

export default function DashboardPage() {
  const router = useRouter();
  const { loading, logout, user } = useAuth();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  if (loading) {
    return (
      <main className="centeredState" aria-live="polite">
        <span className="loadingDot" />
        Restoring your workspace…
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

      <section className="dashboardHero">
        <div>
          <p className="eyebrow">Protected workspace</p>
          <h1>Hello, {user.full_name.split(" ")[0]}.</h1>
          <p>
            Your account and session are ready. Projects and map-based areas of
            interest arrive in Phase 3.
          </p>
        </div>
        <aside className="profileCard">
          <span className="profileInitial">{user.full_name.charAt(0).toUpperCase()}</span>
          <div>
            <p>Signed in as</p>
            <strong>{user.full_name}</strong>
            <span>{user.role}</span>
          </div>
        </aside>
      </section>

      <section className="emptyWorkspace">
        <span>01</span>
        <div>
          <h2>Your workspace is protected</h2>
          <p>
            Only authenticated users can view this page. The next phase will add
            project creation and AOI drawing here.
          </p>
        </div>
      </section>
    </main>
  );
}
