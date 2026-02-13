(function () {
  var LESSON_HASH_PREFIX = "lesson-";

  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
    } else {
      fn();
    }
  }

  function initViewer() {
    var container = document.getElementById("lesson-container");
    var sidebar = document.querySelector(".sidebar-nav");
    var templatesRoot = document.getElementById("lesson-templates");

    if (!container || !sidebar || !templatesRoot) {
      return;
    }

    container.setAttribute("data-viewer-initialised", "true");

    var lessonButtons = Array.prototype.slice.call(
      sidebar.querySelectorAll(".lesson-link")
    );
    if (!lessonButtons.length) {
      return;
    }

    var state = {
      currentLessonId: null,
    };

    function getTemplateForLesson(lessonId) {
      return document.getElementById("lesson-template-" + lessonId);
    }

    function getHashLessonId(hash) {
      if (!hash) return null;
      var value = hash.charAt(0) === "#" ? hash.slice(1) : hash;
      if (value.indexOf(LESSON_HASH_PREFIX) !== 0) return null;
      return value.slice(LESSON_HASH_PREFIX.length);
    }

    function updateHash(lessonId, fromHash) {
      if (fromHash) return;
      var targetHash = "#" + LESSON_HASH_PREFIX + lessonId;
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, "", targetHash);
      } else {
        window.location.hash = targetHash;
      }
    }

    function pauseActiveMedia() {
      var media = container.querySelectorAll("video, audio");
      for (var i = 0; i < media.length; i += 1) {
        try {
          media[i].pause();
          media[i].currentTime = 0;
        } catch (err) {
          /* noop */
        }
      }
    }

    function setActiveButton(lessonId) {
      lessonButtons.forEach(function (button) {
        var isActive = button.dataset.lessonId === String(lessonId);
        button.classList.toggle("is-active", isActive);
        if (isActive) {
          button.setAttribute("aria-current", "page");
        } else {
          button.removeAttribute("aria-current");
        }
      });
    }

    function focusLessonContent() {
      container.focus({ preventScroll: true });
      container.scrollTop = 0;
      var heading = container.querySelector(".lesson-title");
      if (heading) {
        heading.setAttribute("tabindex", "-1");
        heading.focus({ preventScroll: true });
        heading.removeAttribute("tabindex");
      }
    }

    function renderLesson(lessonId, options) {
      if (!lessonId) return;
      if (!options || !options.force) {
        if (state.currentLessonId === lessonId) return;
      }

      var template = getTemplateForLesson(lessonId);
      if (!template || !("content" in template)) {
        console.warn("Missing template for lesson", lessonId);
        return;
      }

      pauseActiveMedia();
      container.innerHTML = "";
      container.appendChild(template.content.cloneNode(true));

      state.currentLessonId = lessonId;
      setActiveButton(lessonId);
      focusLessonContent();
      updateHash(lessonId, options && options.fromHash);
    }

    function handleLessonClick(event) {
      var lessonId = event.currentTarget.dataset.lessonId;
      renderLesson(lessonId);
    }

    function handleLessonKeydown(event) {
      var key = event.key;
      var currentIndex = lessonButtons.indexOf(event.currentTarget);
      if (key === "ArrowDown") {
        event.preventDefault();
        var next = lessonButtons[currentIndex + 1] || lessonButtons[0];
        next.focus();
        return;
      }
      if (key === "ArrowUp") {
        event.preventDefault();
        var prev =
          lessonButtons[currentIndex - 1] ||
          lessonButtons[lessonButtons.length - 1];
        prev.focus();
        return;
      }
      if (key === "Home") {
        event.preventDefault();
        lessonButtons[0].focus();
        return;
      }
      if (key === "End") {
        event.preventDefault();
        lessonButtons[lessonButtons.length - 1].focus();
        return;
      }
      if (key === " " || key === "Enter") {
        event.preventDefault();
        var lessonId = event.currentTarget.dataset.lessonId;
        renderLesson(lessonId);
      }
    }

    function bindEvents() {
      lessonButtons.forEach(function (button) {
        button.addEventListener("click", handleLessonClick);
        button.addEventListener("keydown", handleLessonKeydown);
      });

      window.addEventListener("hashchange", function () {
        var lessonId = getHashLessonId(window.location.hash);
        if (lessonId) {
          renderLesson(lessonId, { fromHash: true, force: true });
        }
      });
    }

    function initInitialLesson() {
      var hashLessonId = getHashLessonId(window.location.hash);
      var activeButton = lessonButtons[0];
      for (var i = 0; i < lessonButtons.length; i += 1) {
        if (lessonButtons[i].classList.contains("is-active")) {
          activeButton = lessonButtons[i];
          break;
        }
      }
      var initialId = hashLessonId || (activeButton && activeButton.dataset.lessonId);
      renderLesson(initialId, { fromHash: true, force: true });
    }

    bindEvents();
    initInitialLesson();
  }

  onReady(initViewer);
})();
