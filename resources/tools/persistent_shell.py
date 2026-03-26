import subprocess
import threading
import queue
import time
import os
import sys
import re

current_dir = os.path.dirname(os.path.abspath(__file__)) # resources/tools
resources_dir = os.path.dirname(current_dir) # resources
automas_dir = os.path.dirname(resources_dir) # automas
if automas_dir not in sys.path:
    sys.path.insert(0, automas_dir)

from config.logger import setup_logger

class PersistentShell:
    OUTPUT_PROCESSING_RULES = {}

    def __init__(self):
        self.process = None
        self.output_queue = queue.Queue()
        self.is_alive = False
        self.logger = setup_logger("PersistentShell")

    def _normalize_command_for_match(self, command: str) -> str:
        cmd = (command or "").strip().lower()
        cmd = cmd.replace("\\", "/")
        cmd = re.sub(r"\s+", " ", cmd)
        return cmd

    def _slice_from_last_marker(self, text: str, marker: str, *, include_marker: bool) -> str:
        if not text:
            return text
        if not marker:
            return text
        idx = text.rfind(marker)
        if idx < 0:
            return text
        if include_marker:
            return text[idx:]
        return text[idx + len(marker) :]

    def _slice_from_last_marker_any(self, text: str, markers: list[str], *, include_marker: bool) -> str:
        if not text:
            return text
        best_idx = -1
        best_marker = ""
        for m in markers or []:
            if not m:
                continue
            idx = text.rfind(m)
            if idx > best_idx:
                best_idx = idx
                best_marker = m
        if best_idx < 0:
            return text
        if include_marker:
            return text[best_idx:]
        return text[best_idx + len(best_marker) :]

    def _clip_output(self, text: str, max_len: int = 15000) -> str:
        if text is None:
            return text
        if max_len <= 0:
            return ""
        if len(text) <= max_len:
            return text
        ellipsis = "..."
        if max_len <= len(ellipsis):
            return ellipsis[:max_len]
        keep = max_len - len(ellipsis)
        head_len = keep // 2
        tail_len = keep - head_len
        return f"{text[:head_len]}{ellipsis}{text[-tail_len:]}"

    def _process_output_by_whitelist(self, command: str, output: str) -> str:
        cmd = self._normalize_command_for_match(command)
        for rule in self.OUTPUT_PROCESSING_RULES.values():
            match_any = rule.get("match_any") or []
            if any(s in cmd for s in match_any):
                processor = rule.get("process")
                if callable(processor):
                    return processor(self, output)
        return output

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
                    self.is_alive = False
                    break
                self.output_queue.put(char)
            except ValueError: # file closed
                self.is_alive = False
                break
            except Exception:
                self.is_alive = False
                break

    def _drain_output_queue(self):
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

    def _is_process_running(self) -> bool:
        if not self.process:
            return False
        try:
            return self.process.poll() is None
        except Exception:
            return False

    def _restart_terminal(self):
        try:
            self.close_terminal()
        except Exception:
            pass
        self.output_queue = queue.Queue()
        self.create_terminal()

    def _is_dangerous_command(self, command: str) -> bool:
        cmd = (command or "").strip()
        if not cmd:
            return False
        if cmd == "exit" or cmd.startswith("exit "):
            return True
        if cmd == "logout" or cmd.startswith("logout "):
            return True
        if re.search(r"(^|\s)exec(\s|$)", cmd):
            return True
        if re.search(r"\bkill\b.*\$\$", cmd):
            return True
        return False

    def execute_command(self, command, timeout=300.0):
        """
        Executes a command in the persistent terminal.
        Returns (success, output).
        
        timeout: Idle timeout in seconds. If no output is received within this period,
                 the command is considered stuck and will be interrupted.
        """
        if self._is_dangerous_command(command):
            self.logger.error(f"Blocked dangerous command: {command}")
            return "execute status: False\nstdout:\n[Error: Dangerous command blocked]"

        if (not self.is_alive) or (not self.process) or (not self._is_process_running()):
            self.logger.error("Attempted to execute command but terminal is not running.")
            print("Attempted to execute command but terminal is not running.")
            self._restart_terminal()

        self.logger.info(f"Executing command: {command}")
        print(f"Executing command: {command}")
        
        # Create unique sentinels
        timestamp = int(time.time())
        sentinel = f"__CMD_DONE_{timestamp}__"
        exit_code_marker = f"__EXIT_CODE_{timestamp}__:"
        
        # Wrap command to print exit code and sentinel
        # We use ; so that even if command fails, we get the exit code and sentinel.
        full_command = f"{command}; echo \"{exit_code_marker}$?\"; echo '{sentinel}'\n"
        self._drain_output_queue()
        wrote = False
        for attempt in range(2):
            try:
                self.process.stdin.write(full_command)
                self.process.stdin.flush()
                wrote = True
                break
            except BrokenPipeError:
                self.is_alive = False
                self._restart_terminal()
            except Exception:
                self.is_alive = False
                self._restart_terminal()
        if not wrote:
            return "execute status: False\nstdout:\n[Error: Broken pipe, terminal restarted but write failed]"
        output_buffer = []
        start_time = time.time()
        
        while True:
            # Check for idle timeout
            if time.time() - start_time > timeout:
                self.logger.warning(f"Command execution idle-timed out after {timeout}s (no output): {command}")
                print(f"Command execution idle-timed out after {timeout}s (no output)")
                
                # Attempt 1: Send Ctrl+C (SIGINT)
                try:
                    self.process.stdin.write('\x03')
                    self.process.stdin.flush()
                    # Give it a moment to react
                    time.sleep(0.5)
                except:
                    pass
                
                # Verify if the process is still stuck or outputting (drain queue)
                # If command is truly stuck, Ctrl+C should kill it and return to prompt.
                # But if it's a deep system call or unresponsive, we might need stronger measures.
                # However, killing the shell itself kills the session.
                # We can try sending SIGINT again or multiple times.
                
                # For robust cleanup of the stuck command without killing the shell:
                # 1. We've sent Ctrl+C.
                # 2. We should consume any remaining output until the shell is responsive again?
                # Actually, if we return here, the next command might fail if the previous one is still running.
                # To be safe, if we timeout, we might want to restart the terminal session if possible,
                # or at least ensure we are back at a prompt.
                
                # Strategy: Send Ctrl+C, then try to print a known marker to verify shell is responsive.
                # If that fails, we might need to kill the terminal.
                
                # Let's try to "ping" the shell to see if it's alive and ready.
                try:
                    # Send Ctrl+C again to be sure
                    self.process.stdin.write('\x03\n')
                    self.process.stdin.flush()
                    time.sleep(0.5)
                    
                    # Try to clear out the queue
                    while not self.output_queue.empty():
                         try:
                            self.output_queue.get_nowait()
                         except queue.Empty:
                            break
                except:
                     pass

                result_output = self._clip_output("".join(output_buffer), 15000)
                self.logger.error(f"execute status: False\nstdout:{result_output}\n[Error: Command idle-timed out after {timeout} seconds without output. Sent SIGINT to interrupt.]")
                return f"execute status: False\nstdout:{result_output}\n[Error: Command idle-timed out after {timeout} seconds without output. Sent SIGINT to interrupt.]"

            try:
                # Read with short timeout to allow checking total time
                char = self.output_queue.get(timeout=0.1)
                output_buffer.append(char)
                start_time = time.time()
                
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

                        result = self._process_output_by_whitelist(command, result)

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
            
