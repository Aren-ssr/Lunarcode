document.addEventListener("DOMContentLoaded", () => {
  const menuButton = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-nav]");
  menuButton?.addEventListener("click", () => {
    const expanded = menuButton.getAttribute("aria-expanded") === "true";
    menuButton.setAttribute("aria-expanded", String(!expanded));
    nav?.classList.toggle("is-open", !expanded);
  });

  document.querySelector("[data-language-select]")?.addEventListener("change", (event) => {
    event.currentTarget.form?.requestSubmit();
  });

  const revealItems = [...document.querySelectorAll("[data-reveal]")];
  const flow = document.querySelector("[data-lesson-flow]");
  const flowSteps = [...document.querySelectorAll("[data-flow-step]")];
  const flowMeter = document.querySelector("[data-flow-meter]");
  const flowCount = document.querySelector("[data-flow-count]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => {
      item.classList.add("reveal-pending");
      revealObserver.observe(item);
    });

    if (flow && flowSteps.length) {
      const stepObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const index = flowSteps.indexOf(entry.target);
          flowSteps.forEach((step, stepIndex) => step.classList.toggle("is-current", stepIndex === index));
          if (flowMeter) flowMeter.value = Math.round(((index + 1) / flowSteps.length) * 100);
          if (flowCount) flowCount.textContent = String(index + 1).padStart(2, "0") + " / " + String(flowSteps.length).padStart(2, "0");
        });
      }, { rootMargin: "-18% 0px -62% 0px", threshold: 0 });
      flowSteps.forEach((step) => stepObserver.observe(step));
    }
  } else if (flowMeter) {
    flowMeter.value = 100;
  }

  if (location.hash === "#quiz") {
    document.querySelector("#quiz")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
  }

  document.querySelector("[data-copy-code]")?.addEventListener("click", async (event) => {
    const code = document.querySelector(".code-window pre code")?.textContent ?? "";
    const button = event.currentTarget;
    try {
      await navigator.clipboard.writeText(code);
      button.textContent = button.dataset.copiedLabel ?? "Copied";
      window.setTimeout(() => { button.textContent = (button.dataset.copyLabel ?? "Copy") + " ⧉"; }, 1400);
    } catch {
      button.textContent = code ? (button.dataset.copyLabel ?? "Copy") : "No code";
    }
  });

  const countdown = document.querySelector("[data-countdown]");
  if (countdown) {
    let remaining = Number(countdown.dataset.countdown);
    const update = () => {
      const minutes = Math.floor(remaining / 60).toString().padStart(2, "0");
      const seconds = (remaining % 60).toString().padStart(2, "0");
      countdown.textContent = minutes + ":" + seconds;
      if (remaining <= 0) {
        window.location.reload();
        return;
      }
      remaining -= 1;
      window.setTimeout(update, 1000);
    };
    update();
  }

  if (!reducedMotion) document.querySelectorAll(".algorithm-visual").forEach((visual) => {
    const nodes = [...visual.querySelectorAll(".algorithm-node")];
    if (nodes.length < 2) return;
    let active = 1;
    window.setInterval(() => {
      nodes.forEach((node, index) => node.classList.toggle("active", index === active));
      active = (active + 1) % nodes.length;
    }, 1400);
  });
});
