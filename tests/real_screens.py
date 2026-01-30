"""Real screen captures from Dungeon Crawl Stone Soup for testing."""

import random
import string


def generate_random_name() -> str:
    """Generate a random character name (6-8 characters)."""
    length = random.randint(6, 8)
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def get_startup_screen_main() -> str:
    """Get the startup menu screen with a random name."""
    name = generate_random_name()
    return f"""Hello, welcome to Dungeon Crawl Stone Soup 0.28.0!
(c) Copyright 1997-2002 Linley Henzell, 2002-2021 Crawl DevTeam

Enter your name: {name}

Choices:         Dungeon Crawl
                 Choose Game Seed
                 Tutorial for Dungeon Crawl
                 Hints Mode for Dungeon Crawl
                 Dungeon Sprint
                 Instructions
                 The Arena
                 High Scores


[tab] quick-start last combo: {name} the Ogre Hedge Wizard
[ctrl-p] view rc file information and log

Dungeon Crawl: The main game: full of monsters, items, gods and danger!"""


def get_character_creation_species() -> str:
    """Get the species selection screen with a random name."""
    name = generate_random_name()
    return f"""Welcome, {name}!

You are a Ogre. Ogres are large, dull-witted, and strong. They have thick hides,
which gives them an armour bonus. Ogres are particularly good at melee combat.

Select your species:

a - Human        c - Elf          e - Orc
b - Dwarf        d - Half-Orc     f - Ogre (*)"""


# Static screens that don't need names

# Real startup menu screen from actual game
STARTUP_SCREEN_MAIN = get_startup_screen_main()

# Starting name entry (just the name prompt)
STARTUP_SCREEN_NAME_ENTRY = """Enter your name: """

# Menu choices screen
STARTUP_SCREEN_MENU_CHOICES = """Choices:         Dungeon Crawl
                 Choose Game Seed
                 Tutorial for Dungeon Crawl
                 Hints Mode for Dungeon Crawl
                 Dungeon Sprint
                 Instructions
                 The Arena
                 High Scores"""

# Species selection screen (first character creation menu after selecting Dungeon Crawl)
CHARACTER_CREATION_SPECIES = get_character_creation_species()

# Class selection screen
CHARACTER_CREATION_CLASS = """You will be a Ogre.

Select your class:

a - Fighter      c - Ranger       e - Necromancer
b - Wizard       d - Rogue        f - Berserker (*) """

# Background selection screen
CHARACTER_CREATION_BACKGROUND = """You are a Ogre Berserker.

Select your background:

a - Death Knight                    d - Monk
b - Hexslinger                      e - Hunter (*)
c - Blood Knight"""

# A typical gameplay screen (after character is fully created and game starts)
GAMEPLAY_SCREEN = """Dungeon:1
HP: 10/10 XL: 1 Sp: 10/10 AC: 4 EV: 8 SH: 0
AC: 4 EV: 8 SH: 0 Fire: .... Cold: .... Elec: .... Poison: .... 
Speed: 10

#####################
#...@......#########
#................###
#................###
##################### """
