/**
 * Mermaid validation helper (test-only).
 *
 * Reads Mermaid text from stdin and validates it using the Mermaid parser.
 * Exits 0 on parse success, non-zero on failure.
 *
 * Usage:
 *   echo "graph TD\n  A --> B" | node validate.mjs
 */

// Mermaid v11+ requires a DOM environment. Provide one via jsdom.
import { JSDOM } from 'jsdom';
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
  pretendToBeVisual: true,
});

// Polyfill DOM globals that Mermaid expects.
// Use Object.defineProperty for read-only globals (e.g. navigator in Node 25+).
for (const key of ['window', 'document', 'DOMParser', 'XMLSerializer']) {
  if (!(key in globalThis) || globalThis[key] === undefined) {
    Object.defineProperty(globalThis, key, {
      value: dom.window[key],
      writable: true,
      configurable: true,
    });
  }
}

// Navigator may be read-only in newer Node versions
try {
  globalThis.navigator = dom.window.navigator;
} catch {
  Object.defineProperty(globalThis, 'navigator', {
    value: dom.window.navigator,
    writable: true,
    configurable: true,
  });
}

const { default: mermaid } = await import('mermaid');

// Initialize mermaid in a minimal config
mermaid.initialize({
  startOnLoad: false,
  securityLevel: 'strict',
  suppressErrors: false,
});

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const input = Buffer.concat(chunks).toString('utf-8').trim();

  if (!input) {
    console.error('No input provided');
    process.exit(1);
  }

  try {
    const result = await mermaid.parse(input);
    if (result === false) {
      console.error('Mermaid parse returned false');
      process.exit(1);
    }
    process.exit(0);
  } catch (err) {
    console.error('Mermaid parse error:', err.message || err);
    process.exit(1);
  }
}

main();
