import { describe, expect, it, vi } from "vitest";
import "@/i18n";
import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { appTheme } from "@/theme";
import AdminTaskDetailsPage from "../AdminTaskDetailsPage";
import { ROUTE_PATHS } from "@/routePaths";

vi.mock("@/admin/components/TaskDetailsView", () => ({
  TaskDetailsView: () => <div>task-body</div>,
}));

describe("AdminTaskDetailsPage chrome", () => {
  it("uses tasks dictionary for title and back action", async () => {
    render(
      <MemoryRouter initialEntries={["/admin/tasks/task-1"]}>
        <MantineProvider theme={appTheme} defaultColorScheme="light">
          <Routes>
            <Route path="/admin/tasks/:taskId" element={<AdminTaskDetailsPage />} />
          </Routes>
        </MantineProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText("Task")).toBeInTheDocument();
    const back = screen.getByRole("link", { name: "Back to Kanban" });
    expect(back.getAttribute("href")).toBe(ROUTE_PATHS.admin.tasks);
    expect(screen.getByText("task-body")).toBeInTheDocument();
  });
});
