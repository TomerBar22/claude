// Renders the scene to MP4 at 30fps (needs playwright + ffmpeg).
//   node render.mjs            -> scene-04-trust.mp4           (16:9, 1920x1080, 8s)
//   node render.mjs vertical   -> scene-04-trust-vertical.mp4  (9:16, 1080x1920, 10s)
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const FORMATS = {
  wide:     { page: 'index.html',    width: 1920, height: 1080, seconds: 8,  out: 'scene-04-trust.mp4' },
  vertical: { page: 'vertical.html', width: 1080, height: 1920, seconds: 10, out: 'scene-04-trust-vertical.mp4' },
};
const FPS = 30;
const fmt = FORMATS[process.argv[2] || 'wide'];
if (!fmt) throw new Error(`unknown format "${process.argv[2]}" (use: ${Object.keys(FORMATS).join(', ')})`);

const dir = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(dir, fmt.out);

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: fmt.width, height: fmt.height } });
await page.goto(pathToFileURL(path.join(dir, fmt.page)).href + '?render=1&t=0');
await page.waitForLoadState('networkidle');

const ffmpeg = spawn('ffmpeg', [
  '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', out,
], { stdio: ['pipe', 'inherit', 'inherit'] });

for (let f = 0; f < FPS * fmt.seconds; f++) {
  await page.evaluate(t => window.seek(t), f / FPS);
  ffmpeg.stdin.write(await page.screenshot({ type: 'png' }));
}
ffmpeg.stdin.end();
await new Promise(r => ffmpeg.on('close', r));
await browser.close();
console.log('wrote', out);
