const { app, BrowserWindow } = require('electron');
const path = require('path');

// Get the port number from command line arguments
const port = process.argv[2] || '2811'; // Default to 2811 if no argument is provided

let iconPath;

if (process.platform === 'win32') {
  iconPath = path.join(__dirname, 'assets/icons/resobox.ico');
} else if (process.platform === 'darwin') {
  iconPath = path.join(__dirname, 'assets/icons/resobox.icns');
} else if (process.platform === 'linux') {
  iconPath = path.join(__dirname, 'assets/icons/resobox.png');
}

function createWindow() {
  // Create the browser window.
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true
    },
    icon: iconPath,
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
