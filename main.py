#!/usr/bin/env python3
"""Main entry point for the Dungeon Crawl Stone Soup bot."""

import argparse
import logging
import sys

from loguru import logger
from credentials import CRAWL_COMMAND
from bot import DCSSBot

# Configure standard logging to go to stderr, not stdout (so TUI can use stdout)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # Send logs to stderr to avoid interfering with TUI display
)

# Configure loguru to only show INFO and above by default (DEBUG hidden)
# This will be overridden if --debug flag is used
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    level="INFO",
    format="<level>{time:HH:mm:ss.SSS}</level> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

std_logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='DCSS Bot - Automated player for Dungeon Crawl Stone Soup')
    parser.add_argument('--steps', type=int, default=5000,
                       help='Maximum number of steps to take (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--crawl-cmd', default=CRAWL_COMMAND,
                       help='Command to run local Crawl')
    
    args = parser.parse_args()
    
    # Configure debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.remove()  # Remove default handler
        logger.add(
            sys.stderr,
            level="DEBUG",
            format="<level>{time:HH:mm:ss.SSS}</level> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    
    std_logger.info("Starting Dungeon Crawl Stone Soup Bot")
    
    # Create bot for local Crawl execution
    std_logger.info(f"Execution mode: LOCAL (command: {args.crawl_cmd})")
    bot = DCSSBot(crawl_command=args.crawl_cmd)
    
    bot.run(max_steps=args.steps)


if __name__ == '__main__':
    main()
