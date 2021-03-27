// Show images only after they're fully loaded.

const flowers = document.querySelector('#flowers');
window.onload = () => { flowers.classList.remove('hidden') };
