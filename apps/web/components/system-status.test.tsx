import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import { SystemStatus } from "./system-status";

afterEach(() => {
  vi.restoreAllMocks();
});

test("shows the ready state when the API is healthy", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));

  render(<SystemStatus />);

  await waitFor(() => {
    expect(screen.getByText("All systems ready")).toBeInTheDocument();
  });
});
