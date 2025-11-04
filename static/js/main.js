const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const form = document.getElementById('uploadForm');

// Show file name
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.style.borderColor = '#00e5ff';
  dropZone.style.backgroundColor = 'rgba(0, 229, 255, 0.05)';
});

dropZone.addEventListener('dragleave', () => {
  dropZone.style.borderColor = '#00e5ff';
  dropZone.style.backgroundColor = 'transparent';
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  fileInput.files = e.dataTransfer.files;
  dropZone.querySelector('p').textContent = `✅ ${fileInput.files[0].name} selected`;
});

// Loading overlay
const overlay = document.createElement('div');
overlay.id = 'loadingOverlay';
overlay.innerHTML = `
  <div class="spinner"></div>
  <p>Analyzing image... Please wait 🧠</p>
`;
overlay.style.cssText = `
  display: none;
  position: fixed;
  top: 0; left: 0;
  width: 100%; height: 100%;
  background: rgba(0,0,0,0.8);
  color: white;
  font-size: 1.2rem;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  z-index: 9999;
`;
document.body.appendChild(overlay);

// Spinner styling
const style = document.createElement('style');
style.innerHTML = `
.spinner {
  border: 6px solid #ddd;
  border-top: 6px solid #00e5ff;
  border-radius: 50%;
  width: 60px;
  height: 60px;
  animation: spin 1s linear infinite;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
`;
document.head.appendChild(style);

// Show overlay when submitting
form.addEventListener('submit', () => {
  overlay.style.display = 'flex';
});
window.addEventListener("load", () => {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) overlay.style.display = "none";
});
