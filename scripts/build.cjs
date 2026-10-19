'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const crypto = require('node:crypto');

(async () => {
  const { packager } = await import('@electron/packager');
  const root = path.resolve(__dirname, '..');
  const python = path.join(root, '.venv', 'Scripts', 'python.exe');
  const runtime = execFileSync(python, ['-c', 'import sys; print(sys.base_prefix)'], { encoding: 'utf8' }).trim();
  const paths = await packager({
    dir: path.join(root, 'desktop'), name: 'ChzzkChatLounge',
    platform: 'win32', arch: 'x64', electronVersion: '44.9.0',
    out: process.env.CHZZK_BUILD_OUTPUT ? path.resolve(process.env.CHZZK_BUILD_OUTPUT) : path.join(root, 'dist', '1.1.7'), overwrite: true, asar: true,
    appVersion: '1.1.7', buildVersion: '1.1.7',
    executableName: 'ChzzkChatLounge',
    win32metadata: { ProductName: 'CHZZK Chat Lounge', FileDescription: 'CHZZK game capture and chat overlay', InternalName: 'ChzzkChatLounge' }
  });
  const output = paths[0];
  const resources = path.join(output, 'resources');
  const filter = source => !source.split(path.sep).some(part => ['__pycache__', '.git'].includes(part));
  await fs.cp(runtime, path.join(resources, 'python'), { recursive: true, dereference: true, filter });
  await fs.cp(path.join(root, '.venv', 'Lib', 'site-packages'), path.join(resources, 'python', 'Lib', 'site-packages'), { recursive: true, dereference: true, filter });
  const backend = path.join(resources, 'backend');
  await fs.mkdir(backend, { recursive: true });
  for (const name of ['main.py', 'custom_chat.py', 'capture.py', 'channel.py', 'chat_theme.py', 'hotkeys.py', 'recording.py', 'moderation.py', 'moderation.js']) {
    await fs.copyFile(path.join(root, name), path.join(backend, name));
  }
  await fs.copyFile(path.join(root, 'scripts', 'bootstrap.py'), path.join(backend, 'bootstrap.py'));
  await fs.copyFile(path.join(root, 'README.md'), path.join(output, 'README.md'));
  await fs.copyFile(path.join(root, 'PACKAGING.md'), path.join(output, 'PACKAGING.md'));
  const dependencies = execFileSync(python, ['-c', 'import importlib.metadata as m; print("\\n".join(sorted(d.metadata["Name"]+"=="+d.version for d in m.distributions())))'], { encoding: 'utf8' });
  await fs.writeFile(path.join(output, 'python-dependencies.txt'), dependencies);
  await fs.copyFile(path.join(root, 'LICENSE'), path.join(output, 'LICENSE-GameChzzk.txt'));
  const manifest = [];
  async function hashes(dir) {
    for (const item of await fs.readdir(dir, { withFileTypes: true })) {
      const file = path.join(dir, item.name);
      if (item.isDirectory()) await hashes(file);
      else manifest.push(`${crypto.createHash('sha256').update(await fs.readFile(file)).digest('hex')}  ${path.relative(output, file).replaceAll('\\', '/')}`);
    }
  }
  await hashes(output);
  await fs.writeFile(path.join(output, 'SHA256SUMS.txt'), manifest.sort().join('\n') + '\n');
  console.log(`Built: ${output}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
