const { app, BrowserWindow } = require('electron');

// Get the port number from command line arguments
const port = process.argv[2] || '2811'; // Default to 2811 if no argument is provided

function createWindow() {
  // Create the browser window.
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true
    }
  });

  // Construct the URL with the port
  const url = `http://localhost:${port}/`;

  // Load the URL
  win.loadURL(url);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
