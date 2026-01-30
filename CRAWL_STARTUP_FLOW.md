# Crawl Startup Flow Analysis

## Based on Crawl v0.28.0 Source Code Review

This document describes the actual startup flow of Dungeon Crawl Stone Soup, derived from examining the source code in `crawl/crawl-ref/source/`.

### Startup Sequence

According to the quickstart guide (`crawl/crawl-ref/docs/quickstart.md`) and source files:

1. **Welcome Message** - Opening screen with version information and copyright
   - Source: `ng-input.cc::opening_screen()`
   - Shows: "Hello, welcome to Crawl [version]"

2. **Name Prompt** - "After starting the program you will be greeted with a message asking for your name"
   - Input: Player types name and **presses Enter**
   - Validation: `validate_player_name()` in `ng-input.cc`
   - File: Source code location: `newgame.cc` and `ng-input.cc`

3. **Species/Ancestry Selection** - "Next you are given menus of species and backgrounds"
   - Format: Menu with letter shortcuts (a, b, c, etc.)
   - Navigation: Use arrow keys or letter keys to select
   - Confirm: Press Enter to select
   - File: `newgame.cc` handles UI using `UINewGameMenu`

4. **Job/Class Selection** - Choose character class
   - Format: Menu with options
   - Navigation: Arrow keys or letters (a, b, c, etc.)
   - Confirm: Press Enter

5. **Weapons Selection** - Optional weapon choice for some classes
   - Format: Menu of starting weapons
   - Navigation: Same as above
   - Confirm: Press Enter

6. **Game Starts** - Character enters the dungeon
   - Display: Map with `@` symbol (player character)
   - Ready for input: Movement commands, abilities, etc.

### Key UI Framework

From examining `outer-menu.h` and `outer-menu.cc`:

- **MenuButton class**: Handles interactive menu buttons
- **Navigation**: 
  - Arrow keys (up/down/left/right) to move between options
  - Letter hotkeys (`a`, `b`, `c`, etc.) for quick selection
  - Enter to confirm selection
- **Event handling**: `on_event()` processes keyboard input
- **Hotkey mapping**: Uses `numpad_to_regular()` function

### Important Facts About Menu Navigation

From `keybind.txt`:

1. **No "Menu Selection" Command** - There's no special "choose option a" command
   - Letters are **hotkeys for menu options**, not commands
   - When a menu shows `[a] Option One [b] Option Two`, you press `a` or `b`
   - This is **direct letter input**, not a state-based menu navigation

2. **Arrow Keys Work** - Cursor/arrow navigation is supported:
   - `k` / Up arrow / NP8: Move up
   - `j` / Down arrow / NP2: Move down
   - `l` / Right arrow / NP6: Move right
   - `h` / Left arrow / NP4: Move left
   - Enter: Confirm selection

3. **Menu Behavior** - Character creation menus:
   - Display options with letter shortcuts (`a)`, `b)`, etc.)
   - Player can either:
     - Press the letter (`a`) to select
     - Use arrow keys to navigate and press Enter to confirm
     - Use menu navigation commands (depends on UI mode)

### Name Entry Details

From `ng-input.cc`:

```cpp
// Name validation rules:
- Maximum length: MAX_NAME_LENGTH (implementation-dependent)
- Valid characters: alphanumeric, hyphen (-), period (.), underscore (_), space
- Invalid on Windows: "CON", "NUL", "PRN", "LPT" (reserved names)
- UTF-8 support: Yes, but must pass validation
```

### Key Issue: After Name Entry

**Critical finding**: After sending the name with Enter, the flow is:

1. Name is received and validated
2. UI transitions to **species/ancestry menu** (not directly to "Dungeon Crawl" option)
3. Player must navigate this menu to select starting species/job/weapons
4. Only after all selections does the game actually start

**This means**: "Dungeon Crawl" is NOT a direct startup option to select with 'a'.

### Expected Menu Structure

Based on source code analysis:

```
Name: [player enters name and presses Enter]
    ↓
Species Menu:
  a) Human              (selected by pressing 'a' or navigating with arrows + Enter)
  b) Mountain Dwarf
  c) Elf
  ...
    ↓
Job Menu:
  a) Fighter
  b) Wizard
  c) Rogue
  ...
    ↓
[Optional] Weapon Choice
    ↓
GAMEPLAY STARTS (Time display appears)
```

### Critical for Bot Implementation

1. **Name Entry + Enter** correctly starts the process
2. **Expect a species menu next** (not immediate game start)
3. **Use letter keys** (a, b, c) or **arrow keys + Enter** to select menu options
4. **Check for multiple menu screens** during character creation
5. **Only Time display indicates actual gameplay start**

### References in Source Code

- `newgame.cc`: Main character creation menu logic
- `ng-input.cc`: Name entry and validation
- `outer-menu.cc`: Interactive menu rendering and input handling
- `outer-menu.h`: Menu button and navigation structure
- Docs: `quickstart.md`, `keybind.txt`
