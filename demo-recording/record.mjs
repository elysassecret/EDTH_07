import { chromium } from '@playwright/test';
import { spawn, spawnSync } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..');
const out = path.join(here, 'output');
await mkdir(out, { recursive: true });

console.log('=== PHAROS PITCH DEMO RECORDER (180s · 1080p · 30 FPS) ===');
console.log(`Working directory: ${root}`);
console.log(`Output directory:  ${out}`);

// 1. Verify timeline
const timeline = JSON.parse(await readFile(path.join(here, 'timeline.json'), 'utf8'));
const totalSec = timeline.reduce((n, s) => n + s.duration, 0);
if (totalSec !== 215) {
  throw new Error(`Timeline durations must total exactly 215 seconds (found: ${totalSec}s)`);
}
console.log(`Timeline verified: ${timeline.length} scenes, exactly 215 seconds.`);

// 2. Verify FFmpeg & FFprobe
function exec(cmd, args, cwd = root) {
  const r = spawnSync(cmd, args, { cwd, stdio: 'inherit' });
  if (r.status !== 0) {
    throw new Error(`${cmd} failed with exit code ${r.status}`);
  }
}
exec('ffmpeg', ['-version']);
exec('ffprobe', ['-version']);

// 3. Ensure frontend bundle is up-to-date
console.log('\nBuilding frontend distribution (web/dist)...');
exec('npm', ['--prefix', 'web', 'run', 'build'], root);

// 4. Start isolated simulation server daemon on port 8878
const PORT = 8878;
console.log(`\nStarting PHAROS server on port ${PORT}...`);
let serverLogs = '';
const server = spawn(
  'uv',
  ['run', 'python', '-m', 'server', '--serve-web', '--demo', 'server/pitch.toml', '--host', '127.0.0.1', '--port', String(PORT)],
  { cwd: root, stdio: ['ignore', 'pipe', 'pipe'] }
);
server.stdout.on('data', (b) => { serverLogs += b; });
server.stderr.on('data', (b) => { serverLogs += b; });

let browser = null;
let context = null;
const pageErrors = [];

try {
  // Wait for server ready
  let ready = false;
  for (let i = 0; i < 60; i++) {
    if (server.exitCode !== null) {
      throw new Error(`Server exited unexpectedly: ${serverLogs}`);
    }
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/`);
      if (res.ok) { ready = true; break; }
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  if (!ready) {
    throw new Error(`Server failed to start after 30s. Logs:\n${serverLogs}`);
  }
  console.log(`Server is ready at http://127.0.0.1:${PORT}/`);

  // 5. Launch Chromium with video recording
  console.log('\nLaunching Chromium with 1920x1080 viewport and video recording...');
  browser = await chromium.launch({
    headless: true,
    args: [
      '--enable-unsafe-swiftshader',
      '--hide-scrollbars',
      '--disable-notifications',
      '--font-render-hinting=none',
    ],
  });

  const rawRecordDir = path.join(out, 'raw');
  await mkdir(rawRecordDir, { recursive: true });

  context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    recordVideo: {
      dir: rawRecordDir,
      size: { width: 1920, height: 1080 },
    },
  });

  const page = await context.newPage();
  page.on('pageerror', (e) => {
    console.error(`Page error: ${e.message}`);
    pageErrors.push(e.message);
  });

  // Navigate to PHAROS in pitch presentation mode
  const targetUrl = `http://127.0.0.1:${PORT}/?pitch=true`;
  console.log(`Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await page.evaluate(() => document.fonts.ready);

  // Hide cursor completely
  await page.addStyleTag({ content: '* { cursor: none !important; }' });

  // Wait for Pitch Director readiness
  console.log('Waiting for simulation feed and map readiness...');
  await page.waitForFunction(
    () => window.__pharos_pitch_ready === true,
    { timeout: 20000 }
  );

  const leadSec = await page.evaluate(() => window.__pharos_pitch_lead || 0);
  console.log(`Pitch director active at lead offset: ${leadSec.toFixed(2)}s`);

  const video = page.video();
  const startTime = performance.now();
  console.log('Pitch recording sequence active: recording 215 seconds (180s pitch + 35s PHAROS outro)...');

  // Track elapsed time and log scene milestones
  let lastLoggedScene = '';
  while (performance.now() - startTime < 215500) {
    const elapsedSec = (performance.now() - startTime) / 1000;
    const currentScene = timeline.find((s) => elapsedSec >= s.start && elapsedSec < s.end);
    if (currentScene && currentScene.id !== lastLoggedScene) {
      lastLoggedScene = currentScene.id;
      console.log(`[${elapsedSec.toFixed(1)}s] SCENE: ${currentScene.speaker} — ${currentScene.title}`);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }

  console.log('215 seconds completed. Capturing final snapshot...');
  await page.screenshot({ path: path.join(out, 'final_frame.png') });

  // Close context to finish writing raw video
  console.log('Closing browser context to finalize raw video stream...');
  await context.close();
  context = null;

  const rawVideoPath = await video.path();
  console.log(`Raw video saved: ${rawVideoPath}`);

  // 6. Transcode with FFmpeg to exact 1920x1080 30FPS H.264 MP4
  const finalMp4Path = path.join(out, 'pharos-pitch.mp4');
  console.log(`\nTranscoding to final MP4: ${finalMp4Path}...`);

  // We enforce exactly 215.00 seconds output with 30fps CFR
  exec('ffmpeg', [
    '-y',
    '-ss', String(leadSec),
    '-i', rawVideoPath,
    '-t', '215.00',
    '-vf', 'fps=30,scale=1920:1080',
    '-an',
    '-c:v', 'libx264',
    '-preset', 'fast',
    '-crf', '18',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    finalMp4Path,
  ]);

  // 7. Verify with FFprobe
  console.log('\nVerifying video properties with FFprobe:');
  exec('ffprobe', [
    '-v', 'error',
    '-show_entries', 'stream=width,height,r_frame_rate,codec_name:format=duration,size',
    '-of', 'default=noprint_wrappers=1',
    finalMp4Path,
  ]);

  // 8. Extract representative scene snapshot frames for review
  console.log('\nExtracting representative scene frames for verification...');
  const keyframes = [
    { name: 'scene1_01_gulf_reconstruction.png', ss: '10.0' },
    { name: 'scene1_02_great_belt_swarm.png', ss: '27.0' },
    { name: 'scene2_01_drift_station_keeping.png', ss: '52.0' },
    { name: 'scene2_02_boat_failure_coverage.png', ss: '69.0' },
    { name: 'scene2_03_endurance_scorecard.png', ss: '75.0' },
    { name: 'scene3_01_decision_explanation.png', ss: '84.0' },
    { name: 'scene3_02_relay_reconfiguration.png', ss: '98.0' },
    { name: 'scene3_03_shore_reconciliation.png', ss: '108.0' },
    { name: 'scene4_01_distributed_auction.png', ss: '128.0' },
    { name: 'scene4_02_ardupilot_hardware.png', ss: '146.0' },
    { name: 'scene5_01_closing_statements.png', ss: '172.0' },
    { name: 'scene6_01_pharos_outro.png', ss: '195.0' },
  ];

  for (const kf of keyframes) {
    exec('ffmpeg', [
      '-y',
      '-ss', kf.ss,
      '-i', finalMp4Path,
      '-frames:v', '1',
      '-q:v', '2',
      path.join(out, kf.name),
    ]);
  }
  console.log(`Generated ${keyframes.length} scene inspection snapshots in ${out}`);

  if (pageErrors.length > 0) {
    console.warn(`\nWarnings: Encountered ${pageErrors.length} page error(s) during recording.`);
  }

  console.log('\n=== RECORDING COMPLETE SUCCESSFULLY ===');
  console.log(`Final Video: ${finalMp4Path}`);

} finally {
  if (context) {
    try { await context.close(); } catch {}
  }
  if (browser) {
    try { await browser.close(); } catch {}
  }
  console.log('Stopping PHAROS server process...');
  server.kill('SIGTERM');
  await writeFile(path.join(out, 'server.log'), serverLogs);
}
