import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const target = join(__dirname, '..', 'node_modules', '@volar', 'language-core', 'lib', 'types.js')

if (!existsSync(target)) {
  process.exit(0)
}

const content = readFileSync(target, 'utf-8')
if (content.startsWith('"use strict"') || content.includes('Object.defineProperty(exports,')) {
  process.exit(0)
}

const stub = `"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
`
writeFileSync(target, stub, 'utf-8')
