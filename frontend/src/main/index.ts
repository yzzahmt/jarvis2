import { app, shell, BrowserWindow } from 'electron'
import { join } from 'path'
import { exec } from 'child_process'
import { is } from '@electron-toolkit/utils'

function createWindow(): void {
  const mainWindow = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 720,
    minHeight: 520,
    show: false,
    backgroundColor: '#05070d',
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// Unlike a typical Mac app, Jarvis has no menu bar/dock story worth staying
// alive for when the window closes — closing the window should fully quit,
// mic/camera and all, on every platform.
app.on('window-all-closed', () => {
  app.quit()
})

// The Python backend (uvicorn + mic/camera capture) is a sibling process,
// not a child of Electron, so quitting Electron alone leaves it running
// invisibly. Kill it explicitly whenever we quit, from any trigger (Cmd+Q,
// closing the window, Dock > Quit).
app.on('before-quit', () => {
  exec('pkill -f "uvicorn jarvis.main"')
})
