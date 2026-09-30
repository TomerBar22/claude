// Renders index.html to scene-04-trust.mp4 (1920x1080, 30fps, 8s).
// Usage: node render.mjs            (needs playwright + ffmpeg)
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const FPS = 30;
const SECONDS = 8;
const dir = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(dir, 'scene-04-trust.mp4');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await page.goto(pathToFileURL(path.join(dir, 'index.html')).href + '?render=1&t=0');
await page.waitForLoadState('networkidle');

const ffmpeg = spawn('ffmpeg', [
  '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });

for (let f = 0; f < FPS * SECONDS; f++) {
  await page.evaluate(t => window.seek(t), f / FPS);
  ffmpeg.stdin.write(await page.screenshot({ type: 'png' }));
}
ffmpeg.stdin.end();
await new Promise(r => ffmpeg.on('close', r));
await browser.close();
console.log('wrote', out);
