document.addEventListener('DOMContentLoaded', () => {
  const ipInput = document.getElementById('backendIp');
  const portInput = document.getElementById('backendPort');
  const saveButton = document.getElementById('save');

  chrome.storage.sync.get(['backendIp', 'backendPort'], (result) => {
    ipInput.value = result.backendIp || 'localhost';
    portInput.value = result.backendPort || '8555';
  });

  saveButton.addEventListener('click', () => {
    const backendIp = ipInput.value;
    const backendPort = portInput.value;
    chrome.storage.sync.set({ backendIp, backendPort }, () => {
      alert('Settings saved.');
    });
  });
});
