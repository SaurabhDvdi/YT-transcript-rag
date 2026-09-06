import { defineConfig } from "wxt";

// See https://wxt.dev/api/config.html
export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: () => ({
    name: "YouTube AI Assistant",
    description:
      "Intelligent AI assistant for YouTube videos powered by transcript retrieval-augmented generation (RAG).",
    version: "0.1.0",
    permissions: ["storage"],
    action: {
      default_title: "Open YouTube AI Assistant",
      default_icon: {
        16: "icon/16.png",
        32: "icon/32.png",
        48: "icon/48.png",
        128: "icon/128.png",
      },
    },
    icons: {
      16: "icon/16.png",
      32: "icon/32.png",
      48: "icon/48.png",
      128: "icon/128.png",
    },
  }),
});
