import http from 'node:http';
import path from 'node:path';
import { readFile } from 'node:fs/promises';
const root = path.resolve('_site');
const prefix = '/AlertMe-Government-Deadline-Assistant/';
const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
};
http
  .createServer(async (req, res) => {
    try {
      const name = decodeURIComponent(
        new URL(req.url, 'http://localhost').pathname,
      );
      if (!name.startsWith(prefix)) throw new Error();
      const file = path.resolve(
        root,
        name.slice(prefix.length) || 'index.html',
      );
      if (file !== root && !file.startsWith(root + path.sep)) throw new Error();
      const bytes = await readFile(file);
      res.writeHead(200, {
        'Content-Type': types[path.extname(file)] || 'application/octet-stream',
      });
      res.end(bytes);
    } catch {
      res.writeHead(404);
      res.end('Not found');
    }
  })
  .listen(58763, '127.0.0.1', () =>
    console.log('Pages preview: http://127.0.0.1:58763' + prefix),
  );
