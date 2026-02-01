"""Local client for running Crawl as a subprocess."""

import subprocess
import time
import threading
import select
import pty
import os
from typing import Optional
from loguru import logger


class LocalCrawlClient:
    """Manages local Crawl process execution."""

    def __init__(self, crawl_command: str = "crawl", **kwargs):
        """
        Initialize local Crawl client.
        
        Args:
            crawl_command: Command to execute (default: "crawl")
            **kwargs: Other arguments (ignored for compatibility with NethackSSHClient)
        """
        self.crawl_command = crawl_command
        self.process = None
        self.process_fd = None
        self.process_pid = None
        self.output_buffer = ""
        self.read_thread = None
        self.stop_reading = False

    def connect(self) -> bool:
        """
        Start local Crawl process with PTY for proper terminal emulation.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting local Crawl with PTY: {self.crawl_command}")
            
            # Use pty.spawn to run Crawl in a proper terminal
            # This ensures proper terminal behavior (colors, cursor control, etc)
            # We'll fork and use pipes for I/O
            master, slave = pty.openpty()
            
            # Set terminal size
            self._set_terminal_size_pty(master)
            
            # Set PTY to raw mode for proper input handling
            self._set_pty_raw_mode(master)
            
            # Fork and exec Crawl
            pid = os.fork()
            if pid == 0:
                # Child process
                os.close(master)
                # Make this the controlling terminal
                os.setsid()
                os.dup2(slave, 0)  # stdin
                os.dup2(slave, 1)  # stdout
                os.dup2(slave, 2)  # stderr
                os.close(slave)
                # Execute Crawl
                os.execl('/bin/sh', 'sh', '-c', self.crawl_command)
                os._exit(1)
            else:
                # Parent process
                os.close(slave)
                self.process_fd = master
                self.process_pid = pid
                logger.info("Successfully started local Crawl process with PTY")
                return True

        except Exception as e:
            logger.error(f"Failed to start Crawl with PTY: {e}")
            # Fallback to pipe-based approach
            return self._connect_with_pipes()

    def _connect_with_pipes(self) -> bool:
        """Fallback to pipe-based subprocess."""
        try:
            logger.info("Falling back to pipe-based subprocess")
            
            # Start Crawl process with pipes
            self.process = subprocess.Popen(
                self.crawl_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,  # Unbuffered for real-time I/O
                shell=True
            )
            
            self.process_fd = None
            logger.info("Successfully started local Crawl process with pipes")
            return True

        except Exception as e:
            logger.error(f"Failed to start Crawl: {e}")
            return False

    def _set_terminal_size_pty(self, fd):
        """Set terminal size for PTY."""
        try:
            import fcntl
            import termios
            import struct
            
            # Set terminal size to 120x40 (width x height)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 120, 0, 0))
        except Exception as e:
            logger.debug(f"Could not set PTY terminal size: {e}")

    def _set_pty_raw_mode(self, fd):
        """Set PTY to cbreak mode for Crawl's interactive menu system.
        
        Cbreak mode (raw with echo) allows Crawl to receive individual keypresses
        while also providing echo feedback, which helps us see what's being entered.
        This is the appropriate mode for ncurses applications like Crawl.
        """
        try:
            import termios
            
            # Get current terminal attributes
            attrs = termios.tcgetattr(fd)
            
            # Cbreak mode: character-by-character input with echo and signals
            # Clear ICANON to get character-by-character input (no line buffering)
            # Keep ECHO enabled so we can see input
            # Keep ISIG enabled for signal processing
            
            attrs[3] &= ~termios.ICANON   # Disable canonical mode (character-by-character)
            attrs[3] |= termios.ECHO      # Enable echo
            attrs[3] |= termios.ISIG      # Enable signal processing
            
            # Set min chars to 0 and timeout to 0 for non-blocking reads
            attrs[6][termios.VMIN] = 0
            attrs[6][termios.VTIME] = 0
            
            termios.tcsetattr(fd, termios.TCSAFLUSH, attrs)
            logger.debug("PTY set to cbreak mode (character-by-character with echo)")
        except Exception as e:
            logger.debug(f"Could not set PTY to cbreak mode: {e}")

    def send_command(self, command: str) -> None:
        """
        Send a command to the game.
        
        Args:
            command: Single character command or string
        """
        try:
            if self.process_fd is not None:
                # PTY mode
                os.write(self.process_fd, command.encode('utf-8'))
            elif self.process and self.process.stdin:
                # Pipe mode
                self.process.stdin.write(command.encode('utf-8'))
                self.process.stdin.flush()
            time.sleep(0.1)  # Brief delay for processing
        except Exception as e:
            logger.error(f"Failed to send command: {e}")

    def read_output(self, timeout: float = 1.0) -> str:
        """
        Read available output from the game.
        
        Args:
            timeout: How long to wait for output in seconds
            
        Returns:
            Game output as string
        """
        if self.process_fd is not None:
            return self._read_output_pty(timeout)
        else:
            return self._read_output_pipes(timeout)

    def _read_output_pty(self, timeout: float = 1.0) -> str:
        """Read output from PTY file descriptor."""
        output = ""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                remaining = max(0.01, timeout - (time.time() - start_time))
                
                try:
                    # Use min(remaining, 0.5) to avoid blocking longer than needed per iteration,
                    # but continue looping until full timeout is reached if no data available
                    ready = select.select([self.process_fd], [], [], min(remaining, 0.5))
                    if ready[0]:
                        data = os.read(self.process_fd, 4096)
                        if not data:
                            break
                        output += data.decode('utf-8', errors='ignore')
                        time.sleep(0.05)
                    # If no data ready, continue looping instead of breaking
                    # The while condition will exit when timeout is reached
                except OSError:
                    break
        except Exception as e:
            logger.debug(f"PTY read error: {e}")
        
        return output

    def _read_output_pipes(self, timeout: float = 1.0) -> str:
        """Read output from subprocess pipes."""
        if not self.process or not self.process.stdout:
            return ""

        output = ""
        try:
            start_time = time.time()
            max_iterations = 20  # Increased from 10 for more attempts
            iterations = 0
            got_any_data = False
            total_wait = 0

            while iterations < max_iterations:
                iterations += 1
                elapsed = time.time() - start_time
                remaining = max(0.01, timeout - elapsed)

                if remaining <= 0.01:
                    logger.debug(f"read_output timeout reached after {iterations} iterations, got {len(output)} bytes")
                    break

                # Use select to check if data is available (Unix/Linux only)
                try:
                    # Use longer select timeout to wait for data
                    ready = select.select([self.process.stdout], [], [], min(remaining, 1.0))
                    if ready[0]:
                        # Data is available
                        chunk_data = self.process.stdout.read(4096)
                        if not chunk_data:
                            logger.debug("Process stdout closed")
                            break
                        output += chunk_data.decode('utf-8', errors='ignore')
                        got_any_data = True
                        logger.debug(f"read_output iteration {iterations}: got {len(chunk_data)} bytes (total: {len(output)})")
                        # Wait a bit for any additional buffered data
                        time.sleep(0.1)  # Increased from 0.05 to give more time
                    else:
                        # select timed out - no more data coming right now
                        if got_any_data:
                            logger.debug(f"read_output: select timeout after getting data, returning {len(output)} bytes")
                        break
                except Exception as e:
                    logger.debug(f"select/read error: {e}")
                    break

        except Exception as e:
            logger.debug(f"read_output error: {e}")

        if not output:
            logger.debug(f"read_output returning empty after {iterations} iterations")
        return output

    def read_output_stable(self, timeout: float = 3.0, stability_threshold: float = 0.3) -> str:
        """
        Read output and wait for screen to stabilize before returning.
        
        This method reads output in chunks and continues until the screen stops changing,
        ensuring we have a complete, settled display before analyzing.
        
        Args:
            timeout: Maximum time to wait in seconds
            stability_threshold: Time (in seconds) with no new data before considering stable (default 0.3s)
        
        Returns:
            Stabilized game output as string
        """
        complete_output = ""
        last_chunk_time = time.time()
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if we've been stable for long enough
            time_since_last_chunk = time.time() - last_chunk_time
            if complete_output and time_since_last_chunk >= stability_threshold:
                logger.debug(f"Screen stabilized after {time.time() - start_time:.2f}s with {len(complete_output)} bytes")
                break
            
            # Read with shorter timeout to check for more data frequently
            remaining_time = timeout - (time.time() - start_time)
            if remaining_time <= 0:
                break
            
            chunk = self.read_output(timeout=min(0.2, remaining_time))
            if chunk:
                complete_output += chunk
                last_chunk_time = time.time()
                logger.debug(f"Got chunk: {len(chunk)} bytes (total: {len(complete_output)})")
            else:
                # No data this iteration, check if we're stable
                time_since_last_chunk = time.time() - last_chunk_time
                if complete_output and time_since_last_chunk >= stability_threshold:
                    logger.debug(f"Screen stable - no data for {time_since_last_chunk:.2f}s")
                    break
        
        return complete_output

    def disconnect(self) -> None:
        """Close Crawl process."""
        try:
            if self.process_fd is not None:
                # PTY mode
                try:
                    os.close(self.process_fd)
                except:
                    pass
                if self.process_pid is not None:
                    try:
                        os.kill(self.process_pid, 15)  # SIGTERM
                        os.waitpid(self.process_pid, 0)
                    except:
                        pass
            elif self.process:
                # Pipe mode
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            
            logger.info("Disconnected from local Crawl process")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
        finally:
            self.process = None
            self.process_fd = None
            self.process_pid = None
