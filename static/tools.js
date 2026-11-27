(function () {
  var DEFAULT_FULL = 2500;
  var DEFAULT_BLURB = 450;

  var form = document.getElementById("beautify");
  if (!form) return;

  var status = document.getElementById("tool-status");
  var fileInput = document.getElementById("captions-file");
  var speakerInput = document.getElementById("speaker-only");
  var blurbInput = document.getElementById("blurb-content");
  var wordsInput = document.getElementById("word-limit");
  var formatBtn = document.getElementById("format-btn");
  var beautifyBtn = document.getElementById("beautify-btn");

  var wordsTouched = false;

  function setStatus(message, isError) {
    status.textContent = message;
    status.className = "tool-status" + (isError ? " is-error" : "");
  }

  function applyWordDefault() {
    if (wordsTouched) return;
    wordsInput.value = blurbInput.checked ? DEFAULT_BLURB : DEFAULT_FULL;
  }

  function setBusy(busy) {
    formatBtn.disabled = busy;
    beautifyBtn.disabled = busy;
  }

  function selectedLangs() {
    return Array.prototype.map
      .call(form.querySelectorAll('input[name="lang"]:checked'), function (input) {
        return input.value;
      })
      .filter(Boolean);
  }

  function langLabel(lang) {
    if (lang === "en") return "English";
    if (lang === "hi") return "Hindi";
    return "original-language";
  }

  function langsLabel(langs) {
    return langs.map(langLabel).join(", ");
  }

  function downloadHtml(html, filename) {
    var blob = new Blob([html], { type: "text/html;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = filename || "reading.html";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function downloadFiles(files) {
    files.forEach(function (file, index) {
      window.setTimeout(function () {
        downloadHtml(file.html, file.filename || "reading.html");
      }, index * 450);
    });
  }

  function prepare(mode) {
    var file = fileInput.files && fileInput.files[0];
    if (!file) {
      setStatus("Choose a captions .txt file.", true);
      return;
    }
    if (location.hostname !== "127.0.0.1" && location.hostname !== "localhost") {
      setStatus("Open Tools from the local reader at http://127.0.0.1:8766/#tools", true);
      return;
    }

    var blurb = mode === "beautify" && blurbInput.checked;
    var langs = mode === "beautify" ? selectedLangs() : ["original"];
    if (mode === "beautify" && !langs.length) {
      setStatus("Check at least one output language.", true);
      return;
    }
    var words = null;
    if (mode === "beautify") {
      var wordsRaw = (wordsInput.value || "").trim();
      words = wordsRaw === "" ? null : parseInt(wordsRaw, 10);
      if (wordsRaw !== "" && (!words || words < 50 || words > 20000)) {
        setStatus("Enter a word limit between 50 and 20000, or leave it empty.", true);
        return;
      }
    }

    setBusy(true);
    setStatus(
      mode === "format"
        ? "Formatting the reading…"
        : blurb
          ? "Beautifying blurb (" + langsLabel(langs) + ")…"
          : "Beautifying reading (" + langsLabel(langs) + ")…",
      false
    );

    var speaker = ((speakerInput && speakerInput.value) || "").trim();
    var query =
      "name=" +
      encodeURIComponent(file.name) +
      "&mode=" +
      encodeURIComponent(mode) +
      "&blurb=" +
      (blurb ? "1" : "0");
    langs.forEach(function (lang) {
      query += "&lang=" + encodeURIComponent(lang);
    });
    if (speaker) query += "&speaker=" + encodeURIComponent(speaker);
    if (words !== null) query += "&words=" + encodeURIComponent(String(words));

    file
      .text()
      .then(function (text) {
        return fetch("/api/beautify?" + query, {
          method: "POST",
          headers: { "Content-Type": "text/plain; charset=utf-8" },
          body: text
        });
      })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok || !data || !data.ok) {
            throw new Error((data && data.error) || "Could not prepare the reading.");
          }
          return data;
        });
      })
      .then(function (data) {
        var files = data.files && data.files.length ? data.files : [{ html: data.html, filename: data.filename }];
        downloadFiles(files);
        if (mode === "format") {
          setStatus("Formatted reading downloaded.", false);
        } else if (files.length === 1) {
          setStatus(
            (blurb ? "Beautified blurb" : "Beautified reading") +
              " (" +
              langLabel(files[0].lang || langs[0]) +
              ") downloaded.",
            false
          );
        } else {
          setStatus(
            "Downloaded " +
              files.length +
              " files (" +
              langsLabel(files.map(function (item) {
                return item.lang;
              })) +
              ").",
            false
          );
        }
      })
      .catch(function (error) {
        setStatus(error.message || "Could not prepare the reading.", true);
      })
      .then(function () {
        setBusy(false);
      });
  }

  blurbInput.addEventListener("change", applyWordDefault);
  wordsInput.addEventListener("input", function () {
    wordsTouched = true;
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
  });

  formatBtn.addEventListener("click", function () {
    prepare("format");
  });
  beautifyBtn.addEventListener("click", function () {
    prepare("beautify");
  });
})();
