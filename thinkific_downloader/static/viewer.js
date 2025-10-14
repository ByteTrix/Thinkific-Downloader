(function () {
  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
    } else {
      fn();
    }
  }

  function initViewer() {
    const container = document.getElementById("lesson-container");
    if (container) {
      container.setAttribute("data-viewer-initialised", "true");
      // Focus main pane for accessibility when opening directly from the filesystem.
      container.focus({ preventScroll: true });
    }

    // Placeholder for richer navigation that will be implemented later.
    if (typeof console !== "undefined" && console.info) {
      console.info("Thinkific offline viewer ready. Interactive navigation will be wired up later.");
    }
  }

  onReady(initViewer);
})();
