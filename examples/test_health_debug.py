"""Test to see what visual_screen contains."""
import sys
import time
from bot import DCSSBot
from credentials import CRAWL_COMMAND

# Create bot instance
bot = DCSSBot(crawl_command=CRAWL_COMMAND)

# Just do one step of the run  to see what's in the screen
if not bot.local_client.connect():
    print("Failed to connect")
    sys.exit(1)

# Handle startup
if not bot._local_startup():
    print("Failed startup")
    bot.local_client.disconnect()
    sys.exit(1)

# Now read one step
output = bot.local_client.read_output(timeout=2.5)
if output:
    bot.last_screen = output
    bot.screen_buffer.update_from_output(output)
    bot.parser.parse_output(output)
    
    visual = bot.screen_buffer.get_screen_text()
    has_health = "Health:" in visual or "HP:" in visual
    print(f"Parser health: {bot.parser.state.health}/{bot.parser.state.max_health}")
    print(f"Has 'Health:' in visual_screen: {has_health}")
    if not has_health:
        print(f"Visual screen (first 1000 chars):\n{visual[:1000]}")
    else:
        print(f"Visual screen (first 500 chars):\n{visual[:500]}")

bot.local_client.disconnect()
