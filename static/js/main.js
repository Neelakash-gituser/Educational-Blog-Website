/* Insight — progressive enhancement only. Every feature here has a
   server-rendered fallback, so the site works with JavaScript disabled. */
(function () {
  "use strict";

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /* ----------------------------------------------------------- theme --- */

  const root = document.documentElement;

  function currentTheme() {
    if (root.dataset.theme === "dark" || root.dataset.theme === "light") {
      return root.dataset.theme;
    }
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  $$("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const next = currentTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try {
        localStorage.setItem("theme", next);
      } catch (e) {}
      document.cookie = "theme=" + next + ";path=/;max-age=31536000;samesite=lax";
    });
  });

  /* ------------------------------------------------------ navigation --- */

  const header = $("[data-header]");
  if (header) {
    const onScroll = () => header.classList.toggle("is-stuck", window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  const navToggle = $("[data-nav-toggle]");
  const mobileNav = $("[data-mobile-nav]");
  if (navToggle && mobileNav) {
    navToggle.addEventListener("click", () => {
      const open = mobileNav.hidden;
      mobileNav.hidden = !open;
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  // Close the account menu when clicking outside of it.
  document.addEventListener("click", (event) => {
    $$("details.user-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.open = false;
    });
  });

  /* ----------------------------------------------------- flash notes --- */

  $$("[data-dismiss]").forEach((button) => {
    button.addEventListener("click", () => button.closest(".flash").remove());
  });

  /* ------------------------------------------------- code block chrome -- */

  const LANG_LABELS = {
    py: "Python", python: "Python", js: "JavaScript", javascript: "JavaScript",
    ts: "TypeScript", typescript: "TypeScript", sh: "Shell", bash: "Bash",
    console: "Shell", shell: "Shell", html: "HTML", css: "CSS", cpp: "C++",
    "c++": "C++", cs: "C#", go: "Go", rs: "Rust", rust: "Rust", sql: "SQL",
    json: "JSON", yaml: "YAML", yml: "YAML", java: "Java", kt: "Kotlin",
    rb: "Ruby", ruby: "Ruby", php: "PHP", tex: "LaTeX", latex: "LaTeX",
    r: "R", matlab: "MATLAB", text: "Text", diff: "Diff", toml: "TOML",
  };

  function labelFor(block) {
    // pymdownx puts language-<name> on the wrapper; plain fenced_code puts it
    // on the <code> element. Check both.
    const code = $("code", block);
    const classes = block.className + " " + ((code && code.className) || "");
    const match = classes.match(/language-([\w+#-]+)/);
    if (!match) return "Code";
    const key = match[1].toLowerCase();
    return LANG_LABELS[key] || match[1].toUpperCase();
  }

  function decorateCodeBlocks(root) {
    $$(".prose .codehilite, .comment-body .codehilite, .preview-body .codehilite", root).forEach((block) => {
      if ($(".code-head", block)) return;

      const head = document.createElement("div");
      head.className = "code-head";

      const label = document.createElement("span");
      label.textContent = labelFor(block);

      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "code-copy";
      copy.textContent = "Copy";
      copy.addEventListener("click", async () => {
        const text = ($("pre", block) || block).innerText;
        try {
          await navigator.clipboard.writeText(text);
          copy.textContent = "Copied";
          copy.classList.add("is-done");
        } catch (e) {
          copy.textContent = "Press ⌘C";
        }
        setTimeout(() => {
          copy.textContent = "Copy";
          copy.classList.remove("is-done");
        }, 1800);
      });

      head.append(label, copy);
      block.prepend(head);
    });

    // Wide tables get their own scroll container rather than breaking the layout.
    $$(".prose table", root).forEach((table) => {
      if (table.parentElement.classList.contains("table-scroll")) return;
      const wrap = document.createElement("div");
      wrap.className = "table-scroll";
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
    });
  }

  decorateCodeBlocks(document);

  /* ------------------------------------------------ reading progress --- */

  const progress = $("[data-progress]");
  const articleBody = $("[data-article-body]");
  if (progress && articleBody) {
    const update = () => {
      const rect = articleBody.getBoundingClientRect();
      const total = rect.height - window.innerHeight;
      const done = total > 0 ? Math.min(1, Math.max(0, -rect.top / total)) : 0;
      progress.style.width = (done * 100).toFixed(2) + "%";
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
  }

  /* ---------------------------------------------------- active in TOC --- */

  const tocLinks = $$(".toc a[href^='#']");
  if (tocLinks.length && "IntersectionObserver" in window) {
    const byId = new Map();
    tocLinks.forEach((link) => byId.set(decodeURIComponent(link.hash.slice(1)), link));
    const headings = Array.from(byId.keys())
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          tocLinks.forEach((link) => link.classList.remove("is-active"));
          const link = byId.get(entry.target.id);
          if (link) link.classList.add("is-active");
        });
      },
      { rootMargin: "-90px 0px -70% 0px" }
    );
    headings.forEach((heading) => observer.observe(heading));
  }

  /* ---------------------------------------------------------- replies -- */

  $$("[data-reply-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const box = document.getElementById(button.dataset.replyToggle);
      if (!box) return;
      box.hidden = !box.hidden;
      button.classList.toggle("is-on", !box.hidden);
      if (!box.hidden) {
        const field = $("textarea", box);
        if (field) field.focus();
      }
    });
  });

  $$("[data-edit-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const form = document.getElementById(button.dataset.editToggle);
      const body = document.getElementById(button.dataset.editBody);
      if (!form) return;
      form.hidden = !form.hidden;
      if (body) body.hidden = !form.hidden;
    });
  });

  $$("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  /* --------------------------------------------- async like / bookmark -- */

  function csrfToken() {
    const field = $("input[name=csrfmiddlewaretoken]");
    if (field) return field.value;
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : "";
  }

  $$("form[data-async]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = $("button", form);
      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: new FormData(form),
        });
        if (!response.ok) throw new Error("request failed");
        const data = await response.json();
        const on = data.liked !== undefined ? data.liked : data.saved;
        button.classList.toggle("is-on", Boolean(on));
        const counter = $("[data-count]", form);
        if (counter && data.count !== undefined) counter.textContent = data.count;
        const onLabel = button.dataset.labelOn;
        const offLabel = button.dataset.labelOff;
        const text = $("[data-label]", form);
        if (text && onLabel && offLabel) text.textContent = on ? onLabel : offLabel;
      } catch (e) {
        form.removeAttribute("data-async");
        form.submit();
      }
    });
  });

  /* ------------------------------------------------- markdown editor --- */

  const editor = $("[data-editor]");
  const preview = $("[data-preview]");
  if (editor) {
    const previewUrl = editor.dataset.previewUrl;
    let timer = null;

    async function refreshPreview() {
      if (!preview || !previewUrl) return;
      const body = new FormData();
      body.append("content", editor.value);
      body.append("csrfmiddlewaretoken", csrfToken());
      try {
        const response = await fetch(previewUrl, {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
          body,
        });
        const data = await response.json();
        preview.innerHTML = data.html || '<p class="muted">Nothing to preview yet.</p>';
        decorateCodeBlocks(preview);
        if (window.MathJax && window.MathJax.typesetPromise) {
          window.MathJax.typesetPromise([preview]).catch(() => {});
        }
      } catch (e) {
        preview.innerHTML = '<p class="muted">Preview unavailable.</p>';
      }
    }

    editor.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(refreshPreview, 400);
      const counter = $("[data-word-count]");
      if (counter) {
        const words = editor.value.trim() ? editor.value.trim().split(/\s+/).length : 0;
        counter.textContent = words + " words · ~" + Math.max(1, Math.round(words / 220)) + " min read";
      }
    });
    refreshPreview();

    // Toolbar buttons wrap or prefix the current selection.
    $$("[data-md]").forEach((button) => {
      button.addEventListener("click", () => {
        const [before, after = ""] = button.dataset.md.split("|");
        const start = editor.selectionStart;
        const end = editor.selectionEnd;
        const selected = editor.value.slice(start, end);
        const insert = before + (selected || button.dataset.placeholder || "") + after;
        editor.setRangeText(insert, start, end, "end");
        if (!selected && button.dataset.placeholder) {
          editor.setSelectionRange(start + before.length, start + before.length + button.dataset.placeholder.length);
        }
        editor.focus();
        editor.dispatchEvent(new Event("input"));
      });
    });

    // Tab indents instead of leaving the textarea — handy for code blocks.
    editor.addEventListener("keydown", (event) => {
      if (event.key === "Tab") {
        event.preventDefault();
        const start = editor.selectionStart;
        editor.setRangeText("  ", start, editor.selectionEnd, "end");
      }
    });
  }
})();
