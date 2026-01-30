# Pyte Buffer Architecture Pattern

## The Core Principle

**The pyte screen buffer is the authoritative, primary source of game state for all decision making.**

Raw PTY output is NOT sufficient for game decisions because it contains only ANSI code deltas (incremental changes), not complete screen text.

## Why This Matters

### Raw PTY Output (DELTA)
```
[1;33H[39;49m[90m[40m[1K[2;4H[30X[3d           .##
[16X[4;4H  #####    ..#     ..         [5;4H  #...#   ##.#### #..
...
```

When you parse this raw output looking for the pattern `([a-zA-Z])\s{3,}([\w\s]+?)`, you won't find "J   endoplasm" because:
- The cursor position codes move the terminal position
- The color/style codes don't render text
- The complete text is reconstructed elsewhere (in the terminal's display)

### Pyte Buffer (ACCUMULATED)
The pyte library processes all those ANSI codes and maintains a 160x40 character grid with the complete, reconstructed display:

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│ J   endoplasm                                                         │
│ r   rat                                                               │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

Now when you parse this text, you find "J   endoplasm" and "r   rat" perfectly.

## The Pattern in Practice

### Main Game Loop
```python
while self.move_count < max_steps:
    # 1. GET RAW OUTPUT (DELTA - only ANSI code changes)
    response = self.ssh_client.read_output(timeout=3.0)
    
    if response:
        # 2. ACCUMULATE INTO PYTE BUFFER
        self.screen_buffer.update_from_output(response)
        
        # 3. USE BUFFER FOR DECISIONS (complete state)
        screen_text = self.screen_buffer.get_screen_text()
        action = self._decide_action(screen_text)
        
        # 4. LOG RAW OUTPUT (delta for debugging)
        self._save_debug_screen(response, ...)
```

### Before (BROKEN - v1.3)
```python
action = self._decide_action(self.last_screen)  # Raw ANSI delta
                                                 # Missing "endoplasm" name!
```

### After (CORRECT - v1.4)
```python
screen_text = self.screen_buffer.get_screen_text()  # Complete state
action = self._decide_action(screen_text)            # Has "endoplasm" name!
```

## Visual Screenshots Represent Bot's Actual Decision Input

The _visual.txt screenshots in logs show what the pyte buffer contains:
- This IS what the bot uses for game decisions
- The _raw.txt files show the delta (for debugging only)
- The _clean.txt files show cleaned delta (also for debugging)

This alignment is critical for understanding bot behavior.

## Key Applications

### Enemy Detection
```python
def _extract_all_enemies_from_tui(self, output: str):
    """
    Extract enemies from TUI monsters section.
    
    output: Should be screen_buffer.get_screen_text() (complete)
    NOT: self.last_screen (raw delta)
    """
```

### Health Tracking
```python
def _extract_health(self, output: str):
    """
    Extract player health from TUI status line.
    
    Requires complete reconstructed text from pyte buffer.
    """
```

### All Game State Parsing
Every regex pattern that looks for game state must receive the complete, accumulated text from the pyte buffer, not raw PTY deltas.

## Implementation Checklist

When adding new game state decisions:

- [ ] Receive screen text from `screen_buffer.get_screen_text()`
- [ ] NOT from `self.last_screen` (raw ANSI delta)
- [ ] NOT from raw PTY output
- [ ] Document in docstring that complete buffer text is required
- [ ] Test regex patterns against real game screens
- [ ] Verify against _visual.txt screenshots in logs

## Common Mistakes

❌ **Wrong**: Uses raw output with jumbled ANSI codes
```python
def _decide_action(self, output: str):
    # If output is self.last_screen, missing info!
    enemies = self._extract_all_enemies_from_tui(output)
```

✅ **Correct**: Uses complete buffer text
```python
def run(self):
    screen_text = self.screen_buffer.get_screen_text()
    action = self._decide_action(screen_text)
```

## Testing

All game state extraction functions should be tested with:
1. Real game screen _visual.txt content (complete state)
2. NOT with _raw.txt content (delta only)
3. Fixtures in `tests/fixtures/game_screens/` provide real examples

## Historical Context

- **v1.3**: Switched from message-based to TUI-based detection
- **v1.4**: Switched from raw PTY delta to pyte buffer (complete state)

This progression reflects understanding that:
1. TUI is more reliable than messages ✓
2. Complete screen buffer is more reliable than incomplete delta ✓

Both changes use the same principle: **use the authoritative, complete representation of game state, not ephemeral or incomplete sources**.
