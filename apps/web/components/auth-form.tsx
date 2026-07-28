"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { useAuth } from "@/components/auth-provider";

type Mode = "login" | "register";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const { login, register } = useAuth();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      const email = String(form.get("email"));
      const password = String(form.get("password"));
      if (mode === "register") {
        await register({
          email,
          fullName: String(form.get("fullName")),
          password,
        });
      } else {
        await login(email, password);
      }
      router.replace("/dashboard");
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Authentication failed. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const isRegister = mode === "register";

  return (
    <main className="authPage">
      <section className="authIntro">
        <Link className="brand brandLight" href="/">
          <span className="brandMark" aria-hidden="true">
            G
          </span>
          GeoFlow
        </Link>
        <div>
          <p className="eyebrow eyebrowLight">Your geospatial workspace</p>
          <h1>{isRegister ? "Start exploring Earth." : "Welcome back."}</h1>
          <p>
            Build repeatable satellite analyses with a guided workflow—no GIS
            scripting required.
          </p>
        </div>
        <p className="authFootnote">Phase 2 · Secure user accounts</p>
      </section>

      <section className="authPanel">
        <div className="authCard">
          <p className="eyebrow">{isRegister ? "Create account" : "Sign in"}</p>
          <h2>{isRegister ? "Create your GeoFlow account" : "Continue to GeoFlow"}</h2>
          <p className="authSwitch">
            {isRegister ? "Already have an account?" : "New to GeoFlow?"}{" "}
            <Link href={isRegister ? "/login" : "/register"}>
              {isRegister ? "Sign in" : "Create one"}
            </Link>
          </p>

          <form onSubmit={handleSubmit}>
            {isRegister && (
              <label>
                Full name
                <input
                  autoComplete="name"
                  minLength={2}
                  name="fullName"
                  placeholder="Your name"
                  required
                />
              </label>
            )}
            <label>
              Email address
              <input
                autoComplete="email"
                name="email"
                placeholder="you@example.com"
                required
                type="email"
              />
            </label>
            <label>
              Password
              <input
                autoComplete={isRegister ? "new-password" : "current-password"}
                minLength={isRegister ? 12 : 1}
                name="password"
                placeholder={isRegister ? "At least 12 characters" : "Your password"}
                required
                type="password"
              />
            </label>
            {error && (
              <p className="formError" role="alert">
                {error}
              </p>
            )}
            <button className="primaryButton" disabled={submitting} type="submit">
              {submitting
                ? "Please wait…"
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>
          <p className="securityNote">
            Sessions use rotating tokens stored in secure HTTP-only cookies.
          </p>
        </div>
      </section>
    </main>
  );
}
