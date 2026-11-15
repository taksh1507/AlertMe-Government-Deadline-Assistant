import { cp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
const destination = path.resolve('_site');
const source = path.resolve('Alertme/src/web');
const input = (process.env.ALERTME_API_URL || '').trim();
let apiBaseUrl = '';
if (input) {
  const url = new URL(input);
  if (
    url.protocol !== 'https:' ||
    url.username ||
    url.password ||
    url.search ||
    url.hash
  )
    throw new Error(
      'ALERTME_API_URL must be an HTTPS API root without credentials, query or fragment.',
    );
  apiBaseUrl = url.href.replace(/\/$/, '');
}
await rm(destination, { recursive: true, force: true });
await mkdir(destination, { recursive: true });
await cp(path.join(source, 'static'), path.join(destination, 'static'), {
  recursive: true,
});
const html = await readFile(path.join(source, 'index.html'), 'utf8');
const policy = `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'${apiBaseUrl ? ' ' + new URL(apiBaseUrl).origin : ''}; base-uri 'none'; form-action 'self'`;
await writeFile(
  path.join(destination, 'index.html'),
  html
    .replace(
      '<html lang="en">',
      `<html lang="en" data-workspace-mode="${apiBaseUrl ? 'remote' : 'local'}">`,
    )
    .replace(
      '<head>',
      `<head><meta http-equiv="Content-Security-Policy" content="${policy}">`,
    ),
);
await writeFile(path.join(destination, '.nojekyll'), '');
await writeFile(
  path.join(destination, 'static/runtime-config.js'),
  `export const runtime = Object.freeze(${JSON.stringify({ mode: apiBaseUrl ? 'remote' : 'local', apiBaseUrl })});\n`,
);
console.log(
  `AlertMe static site: _site/ (${apiBaseUrl ? 'connected API' : 'browser-local planner'})`,
);
