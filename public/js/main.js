// Fade the image in only after it's fully loaded.

const flowers = document.querySelector('#flowers');
window.onload = () => { flowers.classList.remove('loading') };
