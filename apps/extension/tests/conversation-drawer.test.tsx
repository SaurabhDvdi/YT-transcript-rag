import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ConversationDrawer } from "../components/ConversationDrawer";
import { apiClient } from "../services/api";

describe("ConversationDrawer Component", () => {
  const testVideoId = "Gfr50f6ZBvo";
  const mockConversations = [
    {
      id: "conv_1",
      videoId: testVideoId,
      title: "Self-Attention Basics",
      titleSource: "auto" as const,
      createdAt: "2026-09-05T10:00:00Z",
      updatedAt: "2026-09-05T10:15:00Z",
    },
    {
      id: "conv_2",
      videoId: testVideoId,
      title: "Multi-Head Attention",
      titleSource: "user" as const,
      createdAt: "2026-09-05T11:00:00Z",
      updatedAt: "2026-09-05T11:30:00Z",
    },
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(apiClient, "listConversations").mockResolvedValue({
      success: true,
      videoId: testVideoId,
      conversations: mockConversations,
      requestId: "req_list",
    });
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={false}
        activeConversationId="conv_1"
        onClose={vi.fn()}
        onSelectConversation={vi.fn()}
        onNewChat={vi.fn()}
        onClearConversation={vi.fn()}
      />,
    );

    expect(container.firstChild).toBeNull();
  });

  it("renders conversation list and handles selection", async () => {
    const onSelect = vi.fn();
    const onClose = vi.fn();

    render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={true}
        activeConversationId="conv_1"
        onClose={onClose}
        onSelectConversation={onSelect}
        onNewChat={vi.fn()}
        onClearConversation={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Self-Attention Basics")).toBeDefined();
      expect(screen.getByText("Multi-Head Attention")).toBeDefined();
    });

    fireEvent.click(screen.getByText("Multi-Head Attention"));
    expect(onSelect).toHaveBeenCalledWith("conv_2");
    expect(onClose).toHaveBeenCalled();
  });

  it("triggers onNewChat when + New button is clicked", async () => {
    const onNewChat = vi.fn();

    render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={true}
        activeConversationId="conv_1"
        onClose={vi.fn()}
        onSelectConversation={vi.fn()}
        onNewChat={onNewChat}
        onClearConversation={vi.fn()}
      />,
    );

    const newBtn = screen.getByTitle("Start a new chat");
    fireEvent.click(newBtn);
    expect(onNewChat).toHaveBeenCalled();
  });

  it("triggers onClearConversation when Clear current chat is clicked", async () => {
    const onClear = vi.fn();

    render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={true}
        activeConversationId="conv_1"
        onClose={vi.fn()}
        onSelectConversation={vi.fn()}
        onNewChat={vi.fn()}
        onClearConversation={onClear}
      />,
    );

    const clearBtn = screen.getByText("Clear current chat");
    fireEvent.click(clearBtn);
    expect(onClear).toHaveBeenCalled();
  });

  it("filters conversations based on client-side search query", async () => {
    render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={true}
        activeConversationId="conv_1"
        onClose={vi.fn()}
        onSelectConversation={vi.fn()}
        onNewChat={vi.fn()}
        onClearConversation={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Self-Attention Basics")).toBeDefined();
      expect(screen.getByText("Multi-Head Attention")).toBeDefined();
    });

    const searchInput = screen.getByPlaceholderText("Search conversations...");
    fireEvent.change(searchInput, { target: { value: "Multi" } });

    expect(screen.getByText("Multi-Head Attention")).toBeDefined();
    expect(screen.queryByText("Self-Attention Basics")).toBeNull();
  });

  it("opens delete confirmation dialog and cancels without calling API", async () => {
    const deleteSpy = vi.spyOn(apiClient, "deleteConversation").mockResolvedValue({
      success: true,
      conversationId: "conv_1",
      requestId: "req_del",
    });

    render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={true}
        activeConversationId="conv_1"
        onClose={vi.fn()}
        onSelectConversation={vi.fn()}
        onNewChat={vi.fn()}
        onClearConversation={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Self-Attention Basics")).toBeDefined();
    });

    // Hover or find delete button
    const deleteButtons = screen.getAllByTitle("Delete conversation");
    expect(deleteButtons.length).toBeGreaterThan(0);

    fireEvent.click(deleteButtons[0]!);

    // Modal should be open
    expect(screen.getByRole("alertdialog")).toBeDefined();
    expect(screen.getByText(/Delete “Self-Attention Basics”\?/)).toBeDefined();

    // Click cancel
    const cancelBtn = screen.getByText("Cancel");
    fireEvent.click(cancelBtn);

    // Modal closed
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(deleteSpy).not.toHaveBeenCalled();
  });

  it("confirms deletion in dialog and deletes conversation", async () => {
    const deleteSpy = vi.spyOn(apiClient, "deleteConversation").mockResolvedValue({
      success: true,
      conversationId: "conv_1",
      requestId: "req_del",
    });

    render(
      <ConversationDrawer
        videoId={testVideoId}
        isOpen={true}
        activeConversationId="conv_1"
        onClose={vi.fn()}
        onSelectConversation={vi.fn()}
        onNewChat={vi.fn()}
        onClearConversation={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Self-Attention Basics")).toBeDefined();
    });

    const deleteButtons = screen.getAllByTitle("Delete conversation");
    fireEvent.click(deleteButtons[0]!);

    expect(screen.getByRole("alertdialog")).toBeDefined();

    const confirmDeleteBtn = screen.getByRole("button", { name: "Delete" });
    fireEvent.click(confirmDeleteBtn);

    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith("conv_1", testVideoId);
      expect(screen.queryByRole("alertdialog")).toBeNull();
    });
  });
});
