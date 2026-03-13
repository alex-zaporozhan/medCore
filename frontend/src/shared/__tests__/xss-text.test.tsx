import { render, screen } from "@testing-library/react";
import { Text } from "@mantine/core";

describe("XSS policy for user text", () => {
  it("renders dangerous strings as plain text in chat-like bubbles", () => {
    const dangerous = "<script>alert('xss')</script>";

    render(<Text size="sm">{dangerous}</Text>);

    expect(screen.getByText(dangerous)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });

  it("does not interpret onerror/html attributes when rendered as text", () => {
    const dangerous = '<img src=x onerror="alert(1)" />';

    render(<Text size="sm">{dangerous}</Text>);

    expect(screen.getByText(dangerous)).toBeInTheDocument();
    const img = document.querySelector("img");
    expect(img).toBeNull();
  });
});

