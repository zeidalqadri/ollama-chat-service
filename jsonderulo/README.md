# jsonderulo

Hypersimplistic JSON viewer for the terminal.

## Installation

```bash
npm install -g @gooodboy/jsonderulo
```

Or run directly with npx:

```bash
npx @gooodboy/jsonderulo package.json
```

## Usage

```bash
# View a specific JSON file
jsonderulo package.json

# Interactive mode - lists JSON files in current directory
jsonderulo

# Show help
jsonderulo --help
```

## Features

- **Colorized tree view** - Visual hierarchy with ANSI colors
- **Type-aware formatting** - Strings (green), numbers (cyan), booleans (yellow), null (magenta)
- **File statistics** - Shows root type and size
- **Interactive selection** - Browse and select JSON files in current directory
- **Zero dependencies** - Uses only Node.js built-in modules

## Example Output

```
────────────────────────────────────────────────────────────
File: package.json
Type: object
Root size: 5 keys
────────────────────────────────────────────────────────────

root
├── name: "my-app"
├── version: "1.0.0"
├── dependencies: {2 keys}
│   ├── express: "^4.18.0"
│   └── lodash: "^4.17.21"
├── scripts: {2 keys}
│   ├── start: "node index.js"
│   └── test: "jest"
└── keywords: [3 items]
    ├── [0]: "api"
    ├── [1]: "server"
    └── [2]: "node"
```

## Requirements

- Node.js >= 16.0.0

## License

MIT
