/**
 * Mermaid validation helper (test-only).
 *
 * Reads Mermaid text from stdin and validates it using the Mermaid parser.
 * Exits 0 on parse success, non-zero on failure.
 *
 * Usage:
 *   echo "graph TD\n  A --> B" | node validate.mjs
 */

import mermaid from 'mermaid';

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
    // Use mermaid.parse() which validates syntax without rendering
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
