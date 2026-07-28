import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import { AuthProvider, useAuth } from "./auth-provider";

const user = {
  id: "8b3e67db-970f-4589-9a80-4bb7716eb3ed",
  email: "person@example.com",
  full_name: "Geo Flow",
  role: "user",
  created_at: "2026-01-01T00:00:00Z",
};

function SessionState() {
  const { loading, user: currentUser } = useAuth();
  if (loading) return <span>Loading</span>;
  return <span>{currentUser?.email ?? "Signed out"}</span>;
}

afterEach(() => {
  vi.restoreAllMocks();
});

test("restores an authenticated user from the current-user endpoint", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => user,
    }),
  );

  render(
    <AuthProvider>
      <SessionState />
    </AuthProvider>,
  );

  await waitFor(() => {
    expect(screen.getByText("person@example.com")).toBeInTheDocument();
  });
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/api/v1/auth/me",
    expect.objectContaining({ credentials: "include" }),
  );
});

test("uses the refresh cookie when the access session has expired", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Authentication required" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ user, token_type: "cookie" }),
      }),
  );

  render(
    <AuthProvider>
      <SessionState />
    </AuthProvider>,
  );

  await waitFor(() => {
    expect(screen.getByText("person@example.com")).toBeInTheDocument();
  });
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch).toHaveBeenLastCalledWith(
    "http://localhost:8000/api/v1/auth/refresh",
    expect.objectContaining({ method: "POST", credentials: "include" }),
  );
});
