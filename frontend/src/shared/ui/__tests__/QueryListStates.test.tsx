import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { QueryListStates, QueryErrorAlert } from "../QueryListStates";

function wrap(ui: ReactNode) {
  return <MantineProvider>{ui}</MantineProvider>;
}

describe("QueryListStates", () => {
  it("renders loading skeleton by default", () => {
    render(
      wrap(
        <QueryListStates isLoading isError={false} isEmpty={false} empty={null}>
          <div data-testid="ok">ok</div>
        </QueryListStates>
      )
    );
    expect(screen.queryByTestId("ok")).toBeNull();
  });

  it("renders error alert", () => {
    render(
      wrap(
        <QueryListStates
          isLoading={false}
          isError
          error={new Error("boom")}
          isEmpty={false}
          empty={null}
        >
          <div>ok</div>
        </QueryListStates>
      )
    );
    expect(screen.getByText("boom")).toBeTruthy();
  });

  it("renders empty when not loading/error", () => {
    render(
      wrap(
        <QueryListStates isLoading={false} isError={false} isEmpty empty={<span>empty-here</span>}>
          <div>ok</div>
        </QueryListStates>
      )
    );
    expect(screen.getByText("empty-here")).toBeTruthy();
  });

  it("renders children on success", () => {
    render(
      wrap(
        <QueryListStates isLoading={false} isError={false} isEmpty={false} empty={null}>
          <span>success-body</span>
        </QueryListStates>
      )
    );
    expect(screen.getByText("success-body")).toBeTruthy();
  });
});

describe("QueryErrorAlert", () => {
  it("shows formatted message", () => {
    render(wrap(<QueryErrorAlert error={new Error("x")} />));
    expect(screen.getByText("x")).toBeTruthy();
  });
});
