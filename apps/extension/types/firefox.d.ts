import "@wxt-dev/browser";
import type { SidebarAction } from "webextension-polyfill";

/**
 * Firefox sidebarAction API type declaration merging.
 * Augments both @wxt-dev/browser namespace and WxtBrowser interfaces to ensure
 * robust typing across WXT versions and target runtimes without type suppressions.
 */
declare module "@wxt-dev/browser" {
  namespace Browser {
    export const sidebarAction: SidebarAction.Static;
  }
}

declare module "wxt/browser" {
  export interface WxtBrowser {
    sidebarAction?: SidebarAction.Static;
  }
}

declare global {
  interface WxtBrowser {
    sidebarAction?: SidebarAction.Static;
  }
}
