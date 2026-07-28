import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

import {
  createRenderJob,
  executeRenderJob,
  resolveConfig,
  runHyperframeLint,
} from '@hyperframes/producer';

const args = process.argv.slice(2);
const rootIndex = args.indexOf('--job-root');
if (rootIndex === -1 || !args[rootIndex + 1]) {
  throw new Error('usage: runner.mjs --job-root <directory>');
}

const jobRoot = path.resolve(args[rootIndex + 1]);
const requestPath = path.join(jobRoot, 'request.json');
const request = JSON.parse(await fs.readFile(requestPath, 'utf8'));
const projectDir = path.resolve(jobRoot, 'project');
const outputPath = path.resolve(jobRoot, 'full.mov');
const entryPath = path.resolve(projectDir, request.entryFile);

for (const candidate of [projectDir, outputPath, entryPath]) {
  if (candidate !== jobRoot && !candidate.startsWith(`${jobRoot}${path.sep}`)) {
    throw new Error(`HyperFrames path escapes job root: ${candidate}`);
  }
}

const html = await fs.readFile(entryPath, 'utf8');
if (/(?:https?:)?\/\//i.test(html)) {
  throw new Error('HyperFrames compositions must use declared local assets, not remote URLs');
}
const lint = await runHyperframeLint({
  entryFile: request.entryFile,
  html,
  source: 'projectDir',
});
if (lint.errorCount > 0 || (request.strictness === 'strict' && lint.warningCount > 0)) {
  throw new Error(`HyperFrames lint gate failed: ${JSON.stringify(lint)}`);
}

const producerConfig = resolveConfig({
  chromePath: request.browserPath,
  browserGpuMode: 'software',
  concurrency: request.workers,
  forceScreenshot: true,
});
const job = createRenderJob({
  fps: request.frameRate,
  quality: request.quality,
  format: 'mov',
  workers: request.workers,
  strictness: request.strictness,
  entryFile: request.entryFile,
  producerConfig,
  variables: request.variables,
});
await executeRenderJob(job, projectDir, outputPath);
await fs.writeFile(
  path.join(jobRoot, 'hyperframes-result.json'),
  `${JSON.stringify({lint, outputPath}, null, 2)}\n`,
  'utf8',
);
