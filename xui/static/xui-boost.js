// "Boost" façon htmx hx-boost / Turbo Drive — amélioration progressive pure,
// pas un dispatcher (docs/spec-v1.md §15) : chaque lien reste une vraie URL
// GET, routée normalement par FastAPI. Ce script intercepte juste le clic,
// fait le même fetch() qu'un navigateur ferait, et ne remplace que la
// région #xui-main de la page déjà chargée — la sidebar/le header ne
// bougent pas. Sans JS (ou si le fetch échoue), <a href> fonctionne comme
// un lien normal : dégradation gracieuse, aucune route qui n'existerait
// que pour ce script.
(function () {
  function isBoostable(a) {
    if (!a || !a.href || a.target || a.hasAttribute("download")) return false;
    if (a.dataset.xuiBoost === "off") return false;
    let url;
    try {
      url = new URL(a.href, location.href);
    } catch {
      return false;
    }
    return url.origin === location.origin;
  }

  function highlightActiveNav() {
    document.querySelectorAll("[data-xui-nav-link]").forEach((a) => {
      a.classList.toggle("is-active", a.pathname === location.pathname);
    });
  }

  async function swap(url, push) {
    let res;
    try {
      res = await fetch(url, { headers: { "X-Xui-Boost": "1" } });
    } catch {
      location.href = url; // réseau down, hors de portée du boost — navigation normale
      return;
    }
    if (!res.ok) {
      location.href = url; // 403/500 etc. : page d'erreur complète, pas de demi-mesure
      return;
    }
    const html = await res.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const next = doc.getElementById("xui-main");
    const current = document.getElementById("xui-main");
    if (!next || !current) {
      location.href = url; // page qui n'a pas ce layout (ex: plugin SPA) — pas de boost possible
      return;
    }
    current.replaceWith(next);
    document.title = doc.title;
    // res.url suit les redirections (ex: page protégée -> /login) : l'URL
    // affichée doit être celle réellement servie, pas celle cliquée.
    if (push) history.pushState({ xuiBoost: true }, "", res.url);
    window.scrollTo(0, 0);
    highlightActiveNav();
    document.dispatchEvent(new CustomEvent("xui:boosted", { detail: { url: res.url } }));
  }

  document.addEventListener("click", (event) => {
    const a = event.target.closest("a");
    if (!isBoostable(a)) return;
    event.preventDefault();
    swap(a.href, true);
  });

  window.addEventListener("popstate", () => swap(location.href, false));

  highlightActiveNav();
})();
