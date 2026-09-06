import { describe, it, expect } from "vitest";
import {
  extractYouTubeVideoId,
  extractYouTubeVideoType,
  isYouTubeVideoPage,
  isValidYouTubeVideoId,
  isYouTubeHost,
} from "../utils/url";

describe("YouTube URL & ID Extraction Utilities", () => {
  describe("isValidYouTubeVideoId", () => {
    it("accepts valid 11-character alphanumeric and symbol IDs", () => {
      expect(isValidYouTubeVideoId("Gfr50f6ZBvo")).toBe(true);
      expect(isValidYouTubeVideoId("dQw4w9WgXcQ")).toBe(true);
      expect(isValidYouTubeVideoId("a-1_B2c3D4e")).toBe(true);
    });

    it("rejects IDs that are too short, too long, or contain invalid characters", () => {
      expect(isValidYouTubeVideoId("")).toBe(false);
      expect(isValidYouTubeVideoId("too_short")).toBe(false);
      expect(isValidYouTubeVideoId("way_too_long_to_be_a_valid_id")).toBe(false);
      expect(isValidYouTubeVideoId("invalid!id$#")).toBe(false);
      expect(isValidYouTubeVideoId(null)).toBe(false);
      expect(isValidYouTubeVideoId(undefined)).toBe(false);
    });
  });

  describe("isYouTubeHost", () => {
    it("recognizes legitimate YouTube domains", () => {
      expect(isYouTubeHost("youtube.com")).toBe(true);
      expect(isYouTubeHost("www.youtube.com")).toBe(true);
      expect(isYouTubeHost("m.youtube.com")).toBe(true);
      expect(isYouTubeHost("music.youtube.com")).toBe(true);
      expect(isYouTubeHost("youtu.be")).toBe(true);
    });

    it("rejects spoofed and unrelated domains", () => {
      expect(isYouTubeHost("notyoutube.com")).toBe(false);
      expect(isYouTubeHost("youtube.com.attacker.com")).toBe(false);
      expect(isYouTubeHost("fake-youtube.com")).toBe(false);
      expect(isYouTubeHost("vimeo.com")).toBe(false);
      expect(isYouTubeHost("google.com")).toBe(false);
    });
  });

  describe("Standard Watch URLs", () => {
    it("extracts ID from standard watch URL", () => {
      const url = "https://www.youtube.com/watch?v=Gfr50f6ZBvo";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("watch");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });

    it("extracts ID from watch URL with extra query parameters", () => {
      const url =
        "https://www.youtube.com/watch?v=Gfr50f6ZBvo&t=120s&list=PL12345&index=2";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("watch");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });

    it("handles mobile watch URL (m.youtube.com)", () => {
      const url = "https://m.youtube.com/watch?v=Gfr50f6ZBvo";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("watch");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });

    it("handles youtu.be shortlink URL", () => {
      const url = "https://youtu.be/Gfr50f6ZBvo?t=10";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("watch");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });
  });

  describe("Shorts URLs", () => {
    it("extracts ID from shorts URL", () => {
      const url = "https://www.youtube.com/shorts/Gfr50f6ZBvo";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("shorts");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });

    it("extracts ID from shorts URL with query parameters", () => {
      const url = "https://www.youtube.com/shorts/Gfr50f6ZBvo?feature=share";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("shorts");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });
  });

  describe("Embedded Video URLs", () => {
    it("extracts ID from embed URL", () => {
      const url = "https://www.youtube.com/embed/Gfr50f6ZBvo";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("embed");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });

    it("extracts ID from embed URL with autoplay parameters", () => {
      const url = "https://www.youtube.com/embed/Gfr50f6ZBvo?autoplay=1&enablejsapi=1";
      expect(extractYouTubeVideoId(url)).toBe("Gfr50f6ZBvo");
      expect(extractYouTubeVideoType(url)).toBe("embed");
      expect(isYouTubeVideoPage(url)).toBe(true);
    });
  });

  describe("Invalid, Non-Video & Edge Case URLs", () => {
    it("rejects non-video YouTube pages", () => {
      expect(extractYouTubeVideoId("https://www.youtube.com/")).toBeNull();
      expect(
        extractYouTubeVideoId("https://www.youtube.com/feed/subscriptions"),
      ).toBeNull();
      expect(extractYouTubeVideoId("https://www.youtube.com/@mkbhd")).toBeNull();
      expect(
        extractYouTubeVideoId("https://www.youtube.com/results?search_query=test"),
      ).toBeNull();
      expect(isYouTubeVideoPage("https://www.youtube.com/")).toBe(false);
    });

    it("rejects watch URL with missing or empty v parameter", () => {
      expect(extractYouTubeVideoId("https://www.youtube.com/watch")).toBeNull();
      expect(extractYouTubeVideoId("https://www.youtube.com/watch?v=")).toBeNull();
      expect(isYouTubeVideoPage("https://www.youtube.com/watch")).toBe(false);
    });

    it("rejects watch URL with invalid video ID characters or length", () => {
      expect(extractYouTubeVideoId("https://www.youtube.com/watch?v=short")).toBeNull();
      expect(
        extractYouTubeVideoId("https://www.youtube.com/watch?v=invalid!symbols!"),
      ).toBeNull();
      expect(isYouTubeVideoPage("https://www.youtube.com/watch?v=short")).toBe(false);
    });

    it("rejects non-YouTube URLs", () => {
      expect(extractYouTubeVideoId("https://vimeo.com/12345678")).toBeNull();
      expect(extractYouTubeVideoId("https://google.com/watch?v=Gfr50f6ZBvo")).toBeNull();
      expect(isYouTubeVideoPage("https://vimeo.com/12345678")).toBe(false);
    });

    it("rejects domain spoofing attempts", () => {
      expect(
        extractYouTubeVideoId("https://notyoutube.com/watch?v=Gfr50f6ZBvo"),
      ).toBeNull();
      expect(
        extractYouTubeVideoId("https://youtube.com.attacker.com/watch?v=Gfr50f6ZBvo"),
      ).toBeNull();
      expect(
        isYouTubeVideoPage("https://youtube.com.attacker.com/watch?v=Gfr50f6ZBvo"),
      ).toBe(false);
    });

    it("handles malformed and empty URLs without throwing", () => {
      expect(extractYouTubeVideoId("")).toBeNull();
      expect(extractYouTubeVideoId("not-a-valid-url")).toBeNull();
      expect(extractYouTubeVideoId("http://")).toBeNull();
      expect(extractYouTubeVideoId("://invalid")).toBeNull();
      expect(isYouTubeVideoPage("")).toBe(false);
      expect(isYouTubeVideoPage("not-a-valid-url")).toBe(false);
    });
  });
});
