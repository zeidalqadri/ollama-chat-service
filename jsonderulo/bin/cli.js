#!/usr/bin/env node

import { readFileSync, existsSync, statSync, readdirSync } from 'fs';
import { resolve, basename } from 'path';
import { createInterface } from 'readline';
import { stdin, stdout } from 'process';

// ANSI color codes
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  yellow: '\x1b[33m',
  green: '\x1b[32m',
  magenta: '\x1b[35m',
  blue: '\x1b[34m',
  red: '\x1b[31m',
  gray: '\x1b[90m',
};

// Tree drawing characters
const tree = {
  branch: '├── ',
  last: '└── ',
  vertical: '│   ',
  space: '    ',
};

function colorize(text, color) {
  return `${colors[color]}${text}${colors.reset}`;
}

function getValueColor(value) {
  if (value === null) return 'magenta';
  if (typeof value === 'boolean') return 'yellow';
  if (typeof value === 'number') return 'cyan';
  if (typeof value === 'string') return 'green';
  return 'reset';
}

function formatValue(value) {
  if (value === null) return colorize('null', 'magenta');
  if (typeof value === 'boolean') return colorize(value.toString(), 'yellow');
  if (typeof value === 'number') return colorize(value.toString(), 'cyan');
  if (typeof value === 'string') {
    const truncated = value.length > 80 ? value.substring(0, 77) + '...' : value;
    return colorize(`"${truncated}"`, 'green');
  }
  return value;
}

function printTree(data, prefix = '', isLast = true, isRoot = true) {
  if (isRoot) {
    console.log(colorize('root', 'bright'));
  }

  if (typeof data !== 'object' || data === null) {
    return;
  }

  const entries = Array.isArray(data)
    ? data.map((v, i) => [i, v])
    : Object.entries(data);

  entries.forEach(([key, value], index) => {
    const isLastItem = index === entries.length - 1;
    const connector = isLastItem ? tree.last : tree.branch;
    const newPrefix = prefix + (isLastItem ? tree.space : tree.vertical);

    if (Array.isArray(data)) {
      key = colorize(`[${key}]`, 'gray');
    } else {
      key = colorize(key, 'blue');
    }

    if (value === null || typeof value !== 'object') {
      console.log(`${prefix}${connector}${key}: ${formatValue(value)}`);
    } else if (Array.isArray(value)) {
      console.log(`${prefix}${connector}${key}: ${colorize(`[${value.length} items]`, 'dim')}`);
      printTree(value, newPrefix, isLastItem, false);
    } else {
      const keyCount = Object.keys(value).length;
      console.log(`${prefix}${connector}${key}: ${colorize(`{${keyCount} keys}`, 'dim')}`);
      printTree(value, newPrefix, isLastItem, false);
    }
  });
}

function printStats(data, filePath) {
  const stats = {
    type: Array.isArray(data) ? 'array' : 'object',
    size: Array.isArray(data) ? data.length : Object.keys(data).length,
  };

  console.log();
  console.log(colorize('─'.repeat(60), 'dim'));
  console.log(`${colorize('File:', 'bright')} ${basename(filePath)}`);
  console.log(`${colorize('Type:', 'bright')} ${stats.type}`);
  console.log(`${colorize('Root size:', 'bright')} ${stats.size} ${stats.type === 'array' ? 'items' : 'keys'}`);
  console.log(colorize('─'.repeat(60), 'dim'));
  console.log();
}

function loadAndDisplay(filePath) {
  const absolutePath = resolve(filePath);

  if (!existsSync(absolutePath)) {
    console.error(colorize(`Error: File not found: ${filePath}`, 'red'));
    process.exit(1);
  }

  try {
    const content = readFileSync(absolutePath, 'utf-8');
    const data = JSON.parse(content);

    printStats(data, absolutePath);
    printTree(data);
    console.log();

  } catch (err) {
    if (err instanceof SyntaxError) {
      console.error(colorize(`Error: Invalid JSON - ${err.message}`, 'red'));
    } else {
      console.error(colorize(`Error: ${err.message}`, 'red'));
    }
    process.exit(1);
  }
}

function listJsonFiles(dir = '.') {
  const files = readdirSync(dir)
    .filter(f => f.endsWith('.json'))
    .map((f, i) => `  ${colorize(`[${i + 1}]`, 'cyan')} ${f}`);

  if (files.length === 0) {
    console.log(colorize('No JSON files found in current directory.', 'yellow'));
    return [];
  }

  console.log(colorize('\nJSON files in current directory:\n', 'bright'));
  files.forEach(f => console.log(f));
  console.log();

  return readdirSync(dir).filter(f => f.endsWith('.json'));
}

function showHelp() {
  console.log(`
${colorize('jsonderulo', 'bright')} - Hypersimplistic JSON Viewer

${colorize('Usage:', 'yellow')}
  jsonderulo <file.json>     View a JSON file
  jsonderulo                 Interactive mode (list & select JSON files)
  jsonderulo --help          Show this help message

${colorize('Examples:', 'yellow')}
  jsonderulo package.json
  jsonderulo data/config.json
  jsonderulo

${colorize('Features:', 'yellow')}
  - Colorized tree view of JSON structure
  - Type-aware value formatting
  - File statistics
  - Interactive file selection
`);
}

async function interactiveMode() {
  const files = listJsonFiles();

  if (files.length === 0) {
    return;
  }

  const rl = createInterface({ input: stdin, output: stdout });

  const question = (prompt) => new Promise((resolve) => {
    rl.question(prompt, resolve);
  });

  try {
    const answer = await question(colorize('Enter file number (or q to quit): ', 'cyan'));

    if (answer.toLowerCase() === 'q') {
      console.log('Goodbye!');
      rl.close();
      return;
    }

    const index = parseInt(answer) - 1;

    if (isNaN(index) || index < 0 || index >= files.length) {
      console.log(colorize('Invalid selection.', 'red'));
      rl.close();
      return;
    }

    rl.close();
    loadAndDisplay(files[index]);

  } catch (err) {
    rl.close();
    console.error(colorize(`Error: ${err.message}`, 'red'));
  }
}

// Main
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  showHelp();
} else if (args.length > 0) {
  loadAndDisplay(args[0]);
} else {
  interactiveMode();
}
