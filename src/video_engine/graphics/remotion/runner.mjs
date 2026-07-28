import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {createHash} from 'node:crypto';
import {createReadStream} from 'node:fs';
import {lstat, readFile, readdir, realpath, stat} from 'node:fs/promises';
import {dirname, join, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {z} from 'zod';

const args = new Map();
for (let index = 2; index < process.argv.length; index += 2) {
  args.set(process.argv[index], process.argv[index + 1]);
}
for (const key of ['--job-root', '--browser', '--timeout-ms']) {
  if (!args.get(key)) throw new Error(`missing ${key}`);
}

const trustedRoot = dirname(fileURLToPath(import.meta.url));
const trustedEntry = join(trustedRoot, 'entry.tsx');
const jobRoot = await realpath(resolve(args.get('--job-root')));
const browserExecutable = await realpath(resolve(args.get('--browser')));
const timeoutInMilliseconds = Number(args.get('--timeout-ms'));
if (
  !Number.isInteger(timeoutInMilliseconds) ||
  timeoutInMilliseconds < 7_000 ||
  timeoutInMilliseconds > 300_000
) {
  throw new Error('--timeout-ms must be an integer from 7000 through 300000');
}
const requestPath = join(jobRoot, 'request.json');
const publicDir = join(jobRoot, 'public');
const outputLocation = join(jobRoot, 'output.mov');
const bundleDir = join(jobRoot, 'bundle');

const assertInside = (path) => {
  const value = relative(jobRoot, path);
  if (value === '..' || value.startsWith(`..${sep}`) || value.startsWith(sep)) {
    throw new Error('job path escaped the job root');
  }
};

const inspectTree = async (root) => {
  const entries = await readdir(root, {withFileTypes: true});
  for (const entry of entries) {
    const path = join(root, entry.name);
    const metadata = await lstat(path);
    if (metadata.isSymbolicLink()) throw new Error('symlinks are forbidden in graphic jobs');
    assertInside(await realpath(path));
    if (metadata.isDirectory()) await inspectTree(path);
  }
};
await inspectTree(publicDir);

const sourceDigest = async () => {
  const files = [];
  const collect = async (root) => {
    for (const entry of await readdir(root, {withFileTypes: true})) {
      const path = join(root, entry.name);
      if (entry.isDirectory()) await collect(path);
      else if (/\.(css|mjs|ts|tsx)$/.test(entry.name)) files.push(path);
    }
  };
  await collect(trustedRoot);
  files.sort();
  const hash = createHash('sha256');
  for (const path of files) {
    hash.update(relative(trustedRoot, path).split(sep).join('/'));
    hash.update('\0');
    hash.update(await readFile(path));
    hash.update('\0');
  }
  return hash.digest('hex');
};

const requestSchema = z.strictObject({
  schema_version: z.literal('1.0.0'),
  component: z.strictObject({
    id: z.string().regex(/^[a-z0-9_]+$/),
    version: z.literal('1.0.0'),
    source_digest: z.string().regex(/^[0-9a-f]{64}$/),
  }),
  canvas: z.strictObject({
    width: z.number().int().positive().max(16384),
    height: z.number().int().positive().max(16384),
    frame_rate: z.strictObject({
      numerator: z.number().int().positive(),
      denominator: z.number().int().positive(),
    }),
    duration_frames: z.number().int().positive(),
  }),
  render_range: z.strictObject({
    start_frame: z.number().int().nonnegative(),
    end_frame_exclusive: z.number().int().positive(),
  }),
  props: z.record(z.string(), z.unknown()),
  assets: z.array(
    z.strictObject({
      id: z.string().regex(/^[A-Za-z0-9_.-]+$/),
      sha256: z.string().regex(/^[0-9a-f]{64}$/),
      media_type: z.enum(['image', 'video']),
      staged_name: z.string().regex(/^[A-Za-z0-9_.-]+$/),
    }),
  ),
  transparent: z.boolean(),
  color_space: z.literal('rec709'),
});

const requestMetadata = await stat(requestPath);
if (requestMetadata.size > 1_100_000) throw new Error('graphic request exceeds byte limit');
const request = requestSchema.parse(JSON.parse(await readFile(requestPath, 'utf8')));
if (request.render_range.end_frame_exclusive > request.canvas.duration_frames) {
  throw new Error('render range exceeds composition duration');
}
if (request.canvas.width * request.canvas.height > 33_554_432) {
  throw new Error('graphic canvas exceeds pixel limit');
}
if (request.canvas.duration_frames > 36_000 || request.assets.length > 32) {
  throw new Error('graphic request exceeds resource limits');
}
if (JSON.stringify(request.props).length > 1_000_000) {
  throw new Error('graphic props exceed size limit');
}
if (request.component.source_digest !== (await sourceDigest())) {
  throw new Error('component source digest mismatch');
}
let totalAssetBytes = 0;
for (const asset of request.assets) {
  const path = await realpath(join(publicDir, asset.staged_name));
  assertInside(path);
  const metadata = await stat(path);
  totalAssetBytes += metadata.size;
  if (totalAssetBytes > 2_147_483_648) throw new Error('graphic assets exceed byte limit');
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(path)) hash.update(chunk);
  if (hash.digest('hex') !== asset.sha256) {
    throw new Error(`graphic asset hash mismatch: ${asset.id}`);
  }
}

const serveUrl = await bundle({
  entryPoint: trustedEntry,
  publicDir,
  outDir: bundleDir,
  enableCaching: false,
  onProgress: () => undefined,
});
const inputProps = {request};
const composition = await selectComposition({
  serveUrl,
  id: 'VideoEngineGraphic',
  inputProps,
  browserExecutable,
  timeoutInMilliseconds,
  chromeMode: 'headless-shell',
  chromiumOptions: {gl: 'swiftshader', enableMultiProcessOnLinux: true},
});
await renderMedia({
  serveUrl,
  composition,
  codec: 'prores',
  proResProfile: '4444',
  pixelFormat: 'yuva444p10le',
  imageFormat: 'png',
  outputLocation,
  inputProps,
  frameRange: [
    request.render_range.start_frame,
    request.render_range.end_frame_exclusive - 1,
  ],
  muted: true,
  colorSpace: 'bt709',
  browserExecutable,
  timeoutInMilliseconds,
  chromeMode: 'headless-shell',
  chromiumOptions: {gl: 'swiftshader', enableMultiProcessOnLinux: true},
});
