'use strict';
const { app, dialog } = require('electron');
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

app.setName('CHZZK Chat Lounge');
if (process.argv.includes('--package-smoke')) {
  app.setPath('userData', path.join(app.getPath('temp'), 'chzzk-launch-smoke'));
}
if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on('second-instance', () => {
    dialog.showMessageBox({ type: 'info', message: '이미 실행 중입니다.', detail: '작업 표시줄에서 치지직 게임 · 녹화 화면 설정 창을 선택하세요.' });
  });
  app.whenReady().then(() => {
    const root = process.resourcesPath;
    const executable = path.join(root, 'python', 'pythonw.exe');
    const entry = path.join(root, 'backend', 'bootstrap.py');
    fs.mkdirSync(app.getPath('userData'), { recursive: true });
    const logFile = path.join(app.getPath('userData'), 'last-run.log');
    const log = fs.createWriteStream(logFile, { flags: 'w' });
    const smoke = process.argv.includes('--package-smoke');
    // Fixed, bundled executable and script; never invoke a shell or download code.
    const child = spawn(executable, ['-I', '-B', entry, ...(smoke ? ['--package-smoke'] : [])], {
      // pythonw has no console. SW_HIDE would also hide Qt's settings window.
      cwd: path.dirname(entry), windowsHide: false, shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: Object.fromEntries(Object.entries(process.env).filter(([key]) =>
        !/^(PYTHON|QT_|QML|PYSIDE|ELECTRON_RUN_AS_NODE)/i.test(key)))
    });
    child.stdout.pipe(log, { end: false });
    child.stderr.pipe(log, { end: false });
    child.on('error', error => {
      log.end(String(error));
      if (!smoke) dialog.showErrorBox('실행 실패', `프로그램 폴더 전체가 있는지 확인하세요.\n${error.message}\n로그: ${logFile}`);
      app.exit(1);
    });
    child.on('exit', (code, signal) => {
      log.end(`\nBackend exit: ${code}, signal: ${signal}\n`);
      if (code !== 0 && !smoke) dialog.showErrorBox('프로그램이 종료되었습니다', `오류 로그를 확인하세요.\n${logFile}`);
      app.exit(code === 0 ? 0 : 1);
    });
  }).catch(error => { dialog.showErrorBox('실행 실패', error.message); app.exit(1); });
}
