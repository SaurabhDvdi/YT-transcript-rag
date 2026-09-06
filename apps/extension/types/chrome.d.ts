/**
 * Chrome Side Panel API type augmentations.
 */
declare namespace chrome {
  namespace sidePanel {
    interface PanelBehavior {
      openPanelOnActionClick?: boolean;
    }

    interface OpenOptions {
      windowId?: number;
      tabId?: number;
    }

    function setPanelBehavior(behavior: PanelBehavior): Promise<void>;
    function open(options: OpenOptions): Promise<void>;
  }
}
