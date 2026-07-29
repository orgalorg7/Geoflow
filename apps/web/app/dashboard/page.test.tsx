import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { beforeEach, expect, test, vi } from "vitest";

import DashboardPage from "./page";

const replace = vi.fn();
const push = vi.fn();
const apiRequest = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace }),
}));

vi.mock("@/components/auth-provider", () => {
  const user = {
      id: "user-1",
      email: "owner@example.com",
      full_name: "Project Owner",
      role: "user",
      created_at: "2026-01-01T00:00:00Z",
  };
  return {
    useAuth: () => ({
      loading: false,
      logout: vi.fn(),
      user,
    }),
  };
});

vi.mock("@/lib/api", () => ({
  apiRequest: (...args: unknown[]) => apiRequest(...args),
}));

beforeEach(() => {
  apiRequest.mockReset();
  push.mockReset();
  replace.mockReset();
});

test("loads existing projects for the authenticated user", async () => {
  apiRequest.mockResolvedValueOnce([
    {
      id: "project-1",
      user_id: "user-1",
      name: "Nile Delta",
      description: "Vegetation monitoring",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    },
  ]);

  render(<DashboardPage />);

  await waitFor(() => {
    expect(screen.getByText("Nile Delta")).toBeInTheDocument();
  });
  expect(screen.getByText("Vegetation monitoring")).toBeInTheDocument();
});

test("creates a project and opens its map workspace", async () => {
  apiRequest
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce({
      id: "project-2",
      user_id: "user-1",
      name: "Cairo Growth",
      description: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });

  render(<DashboardPage />);
  await screen.findByText("No projects yet");
  fireEvent.click(screen.getByRole("button", { name: "New project" }));
  fireEvent.change(screen.getByLabelText("Project name"), {
    target: { value: "Cairo Growth" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create and open project" }));

  await waitFor(() => {
    expect(push).toHaveBeenCalledWith("/projects/project-2");
  });
  expect(apiRequest).toHaveBeenLastCalledWith(
    "/projects",
    expect.objectContaining({ method: "POST" }),
  );
});
