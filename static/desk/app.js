// Evita o envio repetido sem interferir na validação nativa do navegador.
document.querySelectorAll('form[method="post"]').forEach((form) => {
  form.addEventListener('submit', () => {
    if (!form.checkValidity()) return;
    form.querySelectorAll('button[type="submit"]').forEach((button) => {
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
    });
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('button[aria-busy="true"]').forEach((button) => {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  });
});
