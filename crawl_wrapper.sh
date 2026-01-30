#!/bin/bash
# Wrapper to run Crawl while capturing all output
# This helps work around ncurses alternate buffer issues

# Force unbuffered output
export LC_ALL=C
export TERM=xterm-256color

# Use script to force PTY and capture output
exec /usr/bin/script -q -c "/usr/games/crawl" /dev/null
