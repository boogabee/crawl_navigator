#!/usr/bin/env python3
"""Debug script to see what Crawl outputs on startup."""

import subprocess
import time
import sys

# Start Crawl
process = subprocess.Popen(
    'crawl',
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=0,
    shell=True
)

print("Crawl started. Reading initial output...")
time.sleep(2)

# Try to read output
try:
    import select
    ready = select.select([process.stdout], [], [], 2.0)
    if ready[0]:
        data = process.stdout.read(2048)
        output = data.decode('utf-8', errors='ignore')
        print(f"\n=== RAW OUTPUT ({len(output)} bytes) ===")
        print(repr(output[:500]))
        print(f"\n=== CLEANED OUTPUT ===")
        print(output[:500])
except Exception as e:
    print(f"Error reading: {e}")

# Send 'd' and see what happens
print("\n\nSending 'd'...")
process.stdin.write(b'd')
process.stdin.flush()
time.sleep(1)

ready = select.select([process.stdout], [], [], 1.0)
if ready[0]:
    data = process.stdout.read(2048)
    output = data.decode('utf-8', errors='ignore')
    print(f"\n=== RESPONSE TO 'd' ({len(output)} bytes) ===")
    print(repr(output[:500]))
    print(f"\n=== CLEANED ===")
    print(output[:500])

# Terminate
process.terminate()
process.wait(timeout=2)
print("\nDone")
