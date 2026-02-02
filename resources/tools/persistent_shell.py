import subprocess
import threading
import queue
import time
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__)) # resources/tools
resources_dir = os.path.dirname(current_dir) # resources
automas_dir = os.path.dirname(resources_dir) # automas
if automas_dir not in sys.path:
    sys.path.insert(0, automas_dir)

from config.logger import setup_logger

class PersistentShell:
    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()
        self.is_alive = False
        self.logger = setup_logger("PersistentShell")

    def create_terminal(self):
        """
        Creates a persistent terminal environment (shell).
        """
        self.logger.info("Creating new terminal session...")
        # Use a shell that supports interactive mode well. 
        # /bin/bash or /bin/zsh is common on macOS/Linux.
        shell = os.environ.get('SHELL', '/bin/bash')
        
        self.process = subprocess.Popen(
            [shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Merge stderr into stdout for simplicity
            text=True,
            bufsize=0, # Unbuffered
            universal_newlines=True
        )
        self.is_alive = True
        
        # Start a thread to read output continuously
        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()
        self.logger.info(f"Terminal session started (PID: {self.process.pid})")
        print(f"Terminal session started (PID: {self.process.pid})")
        return self.process.pid

    def _read_output(self):
        """
        Internal method to read stdout from the process and put it in a queue.
        """
        while self.is_alive and self.process and self.process.stdout:
            try:
                # Read character by character to handle prompts and lack of newlines
                char = self.process.stdout.read(1)
                if not char:
                    break
                self.output_queue.put(char)
            except ValueError: # file closed
                break
            except Exception:
                break

    def execute_command(self, command, timeout=30.0):
        """
        Executes a command in the persistent terminal.
        Returns (success, output).
        
        timeout: Total time in seconds to wait for command completion.
        """
        if not self.is_alive or not self.process:
            self.logger.error("Attempted to execute command but terminal is not running.")
            print("Attempted to execute command but terminal is not running.")
            raise RuntimeError("Terminal is not running. Call create_terminal() first.")

        self.logger.info(f"Executing command: {command}")
        print(f"Executing command: {command}")
        
        # Create unique sentinels
        timestamp = int(time.time())
        sentinel = f"__CMD_DONE_{timestamp}__"
        exit_code_marker = f"__EXIT_CODE_{timestamp}__:"
        
        # Wrap command to print exit code and sentinel
        # We use ; so that even if command fails, we get the exit code and sentinel.
        full_command = f"{command}; echo \"{exit_code_marker}$?\"; echo '{sentinel}'\n"
        
        self.process.stdin.write(full_command)
        self.process.stdin.flush()
        output_buffer = []
        start_time = time.time()
        
        while True:
            # Check for timeout
            if time.time() - start_time > timeout:                
                # Try to interrupt the process (Ctrl+C)
                try:
                    self.process.stdin.write('\x03')
                    self.process.stdin.flush()
                except:
                    pass
                
                result_output = "".join(output_buffer)
                self.logger.error(f"execute status: False\nstdout:{result_output}\n[Error: Command timed out after {timeout} seconds]")
                return f"execute status: False\nstdout:{result_output}\n[Error: Command timed out after {timeout} seconds]"
            try:
                # Read with short timeout to allow checking total time
                char = self.output_queue.get(timeout=0.1)
                output_buffer.append(char)
                
                # Optimization: check sentinel only if char matches end of sentinel
                if char == sentinel[-1]:
                     # Check tail of buffer
                     # Sentinel is fairly long, checking last 50 chars is safe enough
                     tail = "".join(output_buffer[-len(sentinel)-50:])
                     if sentinel in tail:
                        # Found sentinel, process output
                        full_output = "".join(output_buffer)
                        
                        # Remove sentinel
                        temp_output = full_output.replace(sentinel, "").strip()
                        
                        # Extract exit code
                        success = False
                        result = temp_output
                        
                        if exit_code_marker in temp_output:
                            parts = temp_output.rsplit(exit_code_marker, 1)
                            result = parts[0].strip()
                            try:
                                exit_code = int(parts[1].strip())
                                success = (exit_code == 0)
                            except ValueError:
                                self.logger.warning("Could not parse exit code")
                        else:
                            self.logger.warning("Exit code marker not found")

                        self.logger.info(f"execute status: {success}\nstdout:\n{result}")
                        print(f"execute status: {success}\nstdout:\n{result}")
                        return f"execute status: {success}\nstdout:\n{result}"

            except queue.Empty:
                continue

    def close_terminal(self):
        """
        Releases the terminal environment.
        """
        if self.process and self.is_alive:
            self.is_alive = False
            # Send exit command
            try:
                self.process.stdin.write("exit\n")
                self.process.stdin.flush()
            except:
                pass
                
            self.process.terminate()
            self.process.wait()
            self.logger.info("Terminal session closed.")
            self.process = None
            