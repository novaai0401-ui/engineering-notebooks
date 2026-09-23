import {build} from 'esbuild';
import {mkdir,copyFile} from 'node:fs/promises';
const target='../java/src/main/resources/static';
await mkdir(target,{recursive:true});
await build({entryPoints:['src/main.tsx'],bundle:true,outfile:target+'/app.js',format:'iife',minify:true});
await copyFile('index.html',target+'/index.html');
console.log('Typed React app bundled into the Spring static directory');
