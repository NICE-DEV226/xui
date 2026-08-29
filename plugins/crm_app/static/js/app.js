// Propre à crm_app — aucun runtime partagé, aucun appel générique : juste
// un confort local à cette page (focus sur le champ nom du formulaire).
document.addEventListener("DOMContentLoaded", () => {
  const nameInput = document.querySelector('form input[name="name"]');
  if (nameInput) nameInput.focus();
});
