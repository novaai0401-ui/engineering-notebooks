import {build} from 'esbuild';
import {mkdir, copyFile} from 'node:fs/promises';
await mkdir('dist', {recursive:true});
await build({entryPoints:['src/main.jsx'],bundle:true,outfile:'dist/app.js',format:'iife',platform:'browser'});
await build({entryPoints:['src/StudyApp.jsx'],bundle:true,outfile:'dist/StudyApp.mjs',format:'esm',platform:'node',external:['react','react-dom']});
await copyFile('index.html','dist/index.html');
console.log('Browser bundle and test module built');
