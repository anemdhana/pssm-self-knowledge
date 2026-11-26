(function () {
  var frame = document.getElementById("read");
  var menus = document.querySelectorAll(".shell-menu a");
  var navs = document.querySelectorAll(".shell-nav");

  var starts = window.SHELL_SECTIONS || {};

  function sectionName() {
    var name = location.hash.replace(/^#/, "");
    return starts[name] ? name : "home";
  }

  function normalize(path) {
    var clean = path.split("?")[0].split("#")[0];
    if (clean.charAt(clean.length - 1) === "/") clean += "index.html";
    return clean.replace(/-(te|kn)(?=\.html$)/, "");
  }

  function samePath(href, current) {
    return normalize(new URL(href, location.href).pathname) === current;
  }

  function mark(path) {
    var current = normalize(path);
    document.querySelectorAll(".nav-article, .nav-series").forEach(function (link) {
      var href = link.getAttribute("href") || link.getAttribute("data-href");
      if (!href) return;
      var extra = (link.getAttribute("data-also") || "").split(/\s+/).filter(Boolean);
      var same = samePath(href, current) || extra.some(function (item) {
        return samePath(item, current);
      });
      if (same) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  var navToggle = document.querySelector(".shell-nav-toggle");

  function narrow() {
    return window.matchMedia("(max-width: 800px)").matches;
  }

  function setNavOpen(open) {
    document.body.classList.toggle("nav-open", open);
    if (navToggle) navToggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  if (navToggle) {
    navToggle.addEventListener("click", function () {
      setNavOpen(!document.body.classList.contains("nav-open"));
    });
  }

  document.querySelectorAll(".nav-series").forEach(function (button) {
    button.addEventListener("click", function () {
      var open = button.getAttribute("aria-expanded") === "true";
      var days = document.getElementById(button.getAttribute("aria-controls"));
      button.setAttribute("aria-expanded", open ? "false" : "true");
      if (days) days.classList.toggle("is-open", !open);
      var href = button.getAttribute("data-href");
      if (href) frame.setAttribute("src", href);
    });
  });

  function show(name, src) {
    navs.forEach(function (nav) {
      nav.hidden = nav.getAttribute("data-section") !== name;
    });
    menus.forEach(function (link) {
      if (link.getAttribute("data-section") === name) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    var start = src || starts[name] || starts.home;
    if (frame.getAttribute("src") !== start) frame.setAttribute("src", start);
  }

  menus.forEach(function (link) {
    link.addEventListener("click", function (event) {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      var name = link.getAttribute("data-section");
      history.pushState(null, "", "#" + (starts[name] ? name : "home"));
      show(name);
    });
  });

  document.querySelector(".shell-brand").addEventListener("click", function (event) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    history.pushState(null, "", "#home");
    show("home");
  });

  document.querySelectorAll(".nav-article").forEach(function (link) {
    link.addEventListener("click", function (event) {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      frame.setAttribute("src", link.getAttribute("href"));
      if (narrow()) setNavOpen(false);
    });
  });

  function settle() {
    try {
      if (!frame.contentDocument || !frame.contentDocument.body) return;
      frame.contentDocument.body.classList.add("in-pane");
      mark(frame.contentWindow.location.pathname);
    } catch (error) {
      /* The reading pane stays usable if the document cannot be reached. */
    }
  }

  frame.addEventListener("load", settle);

  window.addEventListener("popstate", function () {
    show(sectionName());
  });

  show(sectionName());
  settle();
})();
