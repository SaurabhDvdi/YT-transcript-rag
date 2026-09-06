import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuickActions } from "../components/QuickActions";

describe("QuickActions Component", () => {
  it("renders standard grounded quick action buttons", () => {
    const onSelect = vi.fn();
    render(<QuickActions onSelectAction={onSelect} disabled={false} />);

    expect(screen.getByText("Summarize")).toBeDefined();
    expect(screen.getByText("Key Points")).toBeDefined();
    expect(screen.getByText("Explain Simply")).toBeDefined();
  });

  it("calls onSelectAction with the appropriate prompt on click", () => {
    const onSelect = vi.fn();
    render(<QuickActions onSelectAction={onSelect} disabled={false} />);

    fireEvent.click(screen.getByText("Summarize"));
    expect(onSelect).toHaveBeenCalledWith(
      "Summarize the main topics and takeaways of this video in a concise overview.",
    );

    fireEvent.click(screen.getByText("Key Points"));
    expect(onSelect).toHaveBeenCalledWith(
      "List the key points and important takeaways from this video in bullet points.",
    );

    fireEvent.click(screen.getByText("Explain Simply"));
    expect(onSelect).toHaveBeenCalledWith(
      "Explain the core concepts of this video in simple, beginner-friendly terms.",
    );
  });

  it("disables all buttons when disabled prop is true", () => {
    const onSelect = vi.fn();
    render(<QuickActions onSelectAction={onSelect} disabled={true} />);

    const buttons = screen.getAllByRole("button");
    buttons.forEach((btn) => {
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });

    fireEvent.click(screen.getByText("Summarize"));
    expect(onSelect).not.toHaveBeenCalled();
  });
});
