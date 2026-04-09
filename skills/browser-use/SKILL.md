---
name: browser-use
description: |
Automates browser interactions for web testing, form filling, screenshots, and data extraction. Use when the user needs to navigate websites, interact with web pages, fill forms, take screenshots, or extract information from web pages.
Use it when:
  1. You need to work on multiple websites.
  2. You need to navigate websites, interact with web pages, fill forms, take screenshots, or extract information from web pages. (Interact with web pages)
  3. You need something like web-scraping.
allowed-tools: Bash(browser-use:*), Bash(python:*)
---



# Browser Automation with browser-use CLI

The `browser-use` command provides fast, persistent browser automation. It maintains browser sessions across commands, enabling complex multi-step workflows. It also provide some scripts to help you extract webpage data.

## Before You Start

If you already knows target url to extract data from, then you can try to use this scripts first.
```bash
python {PROJECT_DIR}/skills/browser-use/scripts/web_scraping.py {target_url}
```
If it fails, then you can try to use `browser-use` to navigate to that url first. And the follow content will help you learn how to use it.
Additionally, never use
```bash
browser-use get html # get full html
```
That will return the full html of the page, which contains loads of unnecessary information and it might be very large that overflow your context window.
Instead, use 
```bash
python {PROJECT_DIR}/skills/browser-use/scripts/web_scraping.py {target_url}
```
That will return the filtered data of the page, which is more useful for you.
## Installation

```bash
# Run without installing (recommended for one-off use)
uvx "browser-use[cli]" open https://example.com

# Or install permanently
uv pip install "browser-use[cli]"

# Install browser dependencies (Chromium)
browser-use install
```

## Setup

**One-line install (recommended)**

```bash
curl -fsSL https://browser-use.com/cli/install.sh | bash
```

This interactive installer lets you choose your installation mode and configures everything automatically.

**Installation modes:**

```bash
curl -fsSL https://browser-use.com/cli/install.sh | bash -s -- --local-only   # Local browser only
```

| Install Mode   | Available Browsers | Default  | Use Case          |
| -------------- | ------------------ | -------- | ----------------- |
| `--local-only` | chromium, real     | chromium | Local development |

When only one mode is installed, it becomes the default and no `--browser` flag is needed.

**Verify installation:**

```bash
browser-use doctor
```

**Setup wizard (first-time configuration):**

```bash
browser-use setup                         # Interactive setup
browser-use setup --mode local            # Configure for local browser only
browser-use setup --yes                   # Skip interactive prompts
```

**Generate template files:**

```bash
browser-use init                          # Interactive template selection
browser-use init --list                   # List available templates
browser-use init --template basic         # Generate specific template
browser-use init --output my_script.py    # Specify output file
browser-use init --force                  # Overwrite existing files
```

## Quick Start

Choose ONE `open` mode:

If the site returns "Access denied", a bot check/challenge, or renders incorrectly in headless mode, prefer `--headed` (it behaves more like a real user browser and is less likely to be blocked).

**Option A: headless (default)**

```bash
browser-use open https://example.com
```

**Option B: headed (visible window)**

```bash
browser-use --headed open https://example.com
```

Then continue:

```bash
browser-use state                              # Get page elements with indices
browser-use click 5                            # Click element by index
browser-use type "Hello World"                 # Type text
browser-use screenshot                         # Take screenshot
browser-use close                              # Close browser
```

When using `--headed`, always run `browser-use close` after you're done (or after each headed `open`) to avoid stale sessions if the window is closed manually. What's more, it's recommended to run `browser-use close` (single session)or `browser-use close --all` (multiple sessions) to close old and stale session.

## Core Workflow

1. **Navigate**: `browser-use open <url>` - Opens URL (starts browser if needed; default: headless)
2. **Inspect**: `browser-use state` - Returns clickable elements with indices
3. **Interact**: Use indices from state to interact (`browser-use click 5`, `browser-use input 3 "text"`)
4. **Verify**: `browser-use state` or `browser-use screenshot` to confirm actions
5. **Repeat**: Browser stays open between commands

## Browser Modes

```bash
browser-use --browser chromium open <url>      # Default: headless Chromium
browser-use --browser chromium --headed open <url>  # Visible Chromium window
browser-use --browser real open <url>          # User's Chrome with login sessions
```

- **chromium**: Fast, isolated, headless by default
- **real**: Uses your Chrome with cookies, extensions, logged-in sessions

## Commands

## Help

```bash
browser-use -h
```

Example output (excerpt):

```bash
usage: browser-use [-h] [--session SESSION] [--browser {chromium,real}] [--headed] [--profile PROFILE] [--json] [--api-key API_KEY] [--mcp] [--template TEMPLATE]
                   {install,init,open,click,type,input,scroll,back,screenshot,state,switch,close-tab,keys,select,eval,extract,hover,dblclick,rightclick,cookies,wait,get,python,run,sessions,close,server,profile}

positional arguments:
  install      Install Chromium browser + system dependencies
  init         Generate browser-use template file
  open         Navigate to URL
  click        Click element by index
  type         Type text
  input        Type text into specific element
  scroll       Scroll page
  back         Go back in history
  screenshot   Take screenshot
  state        Get browser state (URL, title, elements)
  switch       Switch to tab
  close-tab    Close tab
  keys         Send keyboard keys
  select       Select dropdown option
  eval         Execute JavaScript
  extract      Extract data using LLM
  hover        Hover over element
  dblclick     Double-click element
  rightclick   Right-click element
  cookies      Cookie operations
  wait         Wait for conditions
  get          Get information
  python       Execute Python code
  run          Run agent task (requires API key)
  sessions     List active sessions
  close        Close session
  server       Server control
  profile      Manage browser profiles

options:
  -h, --help            show this help message and exit
  --session SESSION     Session name (default: default)
  --browser {chromium,real}, -b {chromium,real}
                        Browser mode 
  --headed              Show browser window
  --profile PROFILE     Chrome profile (real browser mode)
  --json                Output as JSON
  --api-key API_KEY     Browser-Use API key
  --mcp                 Run as MCP server (JSON-RPC via stdin/stdout)
  --template TEMPLATE   Generate template file (use with --output for custom path)
```

Project usage note:

- Do NOT use `extract`, `run`, `--mcp`, `--api-key`, `remote`or  `--template` in this project. Prefer deterministic CLI commands (`open/state/click/input/get/eval/python`).

### Navigation

Choose ONE `open` mode:

```bash
browser-use open <url>                    # Default: headless
# browser-use --headed open <url>          # Optional: visible window
browser-use back                          # Go back in history
browser-use scroll down                   # Scroll down
browser-use scroll up                     # Scroll up
browser-use scroll down --amount 1000     # Scroll by specific pixels (default: 500)
```

### Page State

```bash
browser-use state                         # Get URL, title, and clickable elements
browser-use screenshot                    # Take screenshot (outputs base64)
browser-use screenshot path.png           # Save screenshot to file
browser-use screenshot --full path.png    # Full page screenshot
```
Prefer saving screenshots to files (instead of base64). Then reference the saved image path when you need to inspect the UI or extract visual details.

### Interactions (use indices from `browser-use state`)

```bash
browser-use click <index>                 # Click element
browser-use type "text"                   # Type text into focused element
browser-use input <index> "text"          # Click element, then type text
browser-use keys "Enter"                  # Send keyboard keys
browser-use keys "Control+a"              # Send key combination
browser-use select <index> "option"       # Select dropdown option
```

### Tab Management

```bash
browser-use switch <tab>                  # Switch to tab by index
browser-use close-tab                     # Close current tab
browser-use close-tab <tab>               # Close specific tab
```

### Cookies

```bash
browser-use cookies get                   # Get all cookies
browser-use cookies get --url <url>       # Get cookies for specific URL
browser-use cookies set <name> <value>    # Set a cookie
browser-use cookies set name val --domain .example.com --secure --http-only
browser-use cookies set name val --same-site Strict  # SameSite: Strict, Lax, or None
browser-use cookies set name val --expires 1735689600  # Expiration timestamp
browser-use cookies clear                 # Clear all cookies
browser-use cookies clear --url <url>     # Clear cookies for specific URL
browser-use cookies export <file>         # Export all cookies to JSON file
browser-use cookies export <file> --url <url>  # Export cookies for specific URL
browser-use cookies import <file>         # Import cookies from JSON file
```

### Wait Conditions

```bash
browser-use wait selector "h1"            # Wait for element to be visible
browser-use wait selector ".loading" --state hidden  # Wait for element to disappear
browser-use wait selector "#btn" --state attached    # Wait for element in DOM
browser-use wait text "Success"           # Wait for text to appear
browser-use wait selector "h1" --timeout 5000  # Custom timeout in ms
```

### Additional Interactions

```bash
browser-use hover <index>                 # Hover over element (triggers CSS :hover)
browser-use dblclick <index>              # Double-click element
browser-use rightclick <index>            # Right-click element (context menu)
```

### Information Retrieval

```bash
browser-use get title                     # Get page title
browser-use get html                      # Get full page HTML
browser-use get html --selector "h1"      # Get HTML of specific element
browser-use get text <index>              # Get text content of element
browser-use get value <index>             # Get value of input/textarea
browser-use get attributes <index>        # Get all attributes of element
browser-use get bbox <index>              # Get bounding box (x, y, width, height)
```

#### Warning
Be careful, **never** use
```bash
browser-use get html # get full html
```
That will return the full html of the page, which contains loads of unnecessary information and it might be very large that **overflow your context window**.

Instead, use 
```bash
python {PROJECT_DIR}/skills/browser-use/scripts/web_scraping.py {target_url}
```
That will return the filtered data of the page, which is more useful for you.

### JavaScript Execution (eval)

```bash
browser-use eval "document.title"
browser-use eval "location.href"
browser-use eval "document.querySelector('h1')?.textContent"
browser-use eval "Array.from(document.querySelectorAll('a')).slice(0, 5).map(a => a.href)"
browser-use eval "window.location.href"
```

### Python Execution (Persistent Session)

```bash
browser-use python "x = 42"               # Set variable
browser-use python "print(x)"             # Access variable (outputs: 42)
browser-use python "print(browser.url)"   # Access browser object
browser-use python --vars                 # Show defined variables
browser-use python --reset                # Clear Python namespace
browser-use python --file script.py       # Execute Python file
```

### Scroll and state

When you find state command doesn't return enough information, you can use scroll command to scroll down or up, you can use `--amount` to specify the amount of pixels to scroll.

```bash
browser-use state                         # Get page elements with indices, but find that it doesn't return enough information
browser-use scroll down                   # Scroll down
browser-use state                         # state again to get more information
```

The Python session maintains state across commands. The `browser` object provides:

- `browser.url` - Current page URL
- `browser.title` - Page title
- `browser.html` - Get page HTML
- `browser.goto(url)` - Navigate
- `browser.click(index)` - Click element
- `browser.type(text)` - Type text
- `browser.input(index, text)` - Click element, then type
- `browser.keys(keys)` - Send keyboard keys (e.g., "Enter", "Control+a")
- `browser.screenshot(path)` - Take screenshot
- `browser.scroll(direction, amount)` - Scroll page
- `browser.back()` - Go back in history
- `browser.wait(seconds)` - Sleep/pause execution

### Extract Data

For simple data extraction, you can use cli command in previous content. However, when you come across data extraction task that failed for many times, you can use the following method:

**Key Strategy**: Use vision to extract data that cannot be extracted by regex or other rules.

#### Practice

```bash
browser-use screenshot path.png           # Save screenshot to file, filename can be customized
```

Then you must read/load this screenshot file to extract the data you want.

If you find that the screenshot file doesn't contain the data you want or it does not capture enough content of the page, you can:
1. Take a full page screenshot to capture more content.
```bash
browser-use screenshot --full path.png    # Full page screenshot
```

2. Scroll down or up and then take a screenshot to capture more content.
```bash
browser-use scroll down                   # Scroll down, use --amount to specify the amount of pixels to scroll.
browser-use scroll up                     # Scroll up, use --amount to specify the amount of pixels to scroll.
```



### Session Management

```bash
browser-use sessions                      # List active sessions
browser-use close                         # Close current session
browser-use close --all                   # Close all sessions
```

### Profile Management

#### Local Chrome Profiles (`--browser real`)

```bash
browser-use -b real profile list          # List local Chrome profiles
```

**Before opening a real browser (`--browser real`)**, always ask the user if they want to use a specific Chrome profile or no profile. Use `profile list` to show available profiles:

```bash
browser-use -b real profile list
# Output: Default: Person 1 (user@gmail.com)
#         Profile 1: Work (work@company.com)

# With a specific profile (has that profile's cookies/logins)
browser-use --browser real --profile "Profile 1" open https://gmail.com

# Without a profile (fresh browser, no existing logins)
browser-use --browser real open https://gmail.com

# Headless mode (no visible window) - useful for cookie export
browser-use --browser real --profile "Default" cookies export /tmp/cookies.json
```

Each Chrome profile has its own cookies, history, and logged-in sessions. Choosing the right profile determines whether sites will be pre-authenticated.

### Server Control

```bash
browser-use server status                 # Check if server is running
browser-use server stop                   # Stop server
browser-use server logs                   # View server logs
```

## Global Options

| Option           | Description                            |
| ---------------- | -------------------------------------- |
| `--session NAME` | Use named session (default: "default") |
| `--browser MODE` | Browser mode: chromium, real           |
| `--headed`       | Show browser window (chromium mode)    |
| `--profile NAME` | Browser profile (local name)           |
| `--json`         | Output as JSON                         |
| `--mcp`          | Run as MCP server via stdin/stdout     |

**Session behavior**: All commands without `--session` use the same "default" session. The browser stays open and is reused across commands. Use `--session NAME` to run multiple browsers in parallel.

## Examples

### Form Submission

```bash
browser-use open https://example.com/contact           # Default: headless
# browser-use --headed open https://example.com/contact  # Optional: visible window
browser-use state
# Shows: [0] input "Name", [1] input "Email", [2] textarea "Message", [3] button "Submit"
browser-use input 0 "John Doe"
browser-use input 1 "john@example.com"
browser-use input 2 "Hello, this is a test message."
browser-use click 3
browser-use state  # Verify success
browser-use close # Always use close when current task is finished
```

### Multi-Session Workflows

```bash
browser-use --session work open https://work.example.com
browser-use --session personal open https://personal.example.com
# Add --headed to any open when you need a visible window:
# browser-use --session work --headed open https://work.example.com
# browser-use --session personal --headed open https://personal.example.com
browser-use --session work state    # Check work session
browser-use --session personal state  # Check personal session
browser-use close --all             # Close both sessions
```

### Data Extraction with Python

```bash
browser-use open https://example.com/products           # Default: headless
# browser-use --headed open https://example.com/products  # Optional: visible window
browser-use python "
products = []
for i in range(20):
    browser.scroll('down')
browser.screenshot('products.png')
"
browser-use python "print(f'Captured {len(products)} products')"
browser-use close # Always use close when current task is finished
```

### Using Real Browser (Logged-In Sessions)

```bash
browser-use --browser real open https://gmail.com
# Uses your actual Chrome with existing login sessions
browser-use state  # Already logged in!
```

## Common Patterns

### Screenshot Loop for Visual Verification

```bash
browser-use open https://example.com           # Default: headless
# browser-use --headed open https://example.com  # Optional: visible window
for i in 1 2 3 4 5; do
  browser-use scroll down
  browser-use screenshot "page_$i.png"
done
browser-use close # Always use close when current task is finished
```

## Tips

1. **Always run** **`browser-use state`** **first** to see available elements and their indices
2. **Use** **`--headed`** **for debugging** to see what the browser is doing, or just let user to see real time operation
3. **Prefer** **`--headed`** **when needed**: debugging, manual login/verification, or when a site blocks headless (e.g., "Access denied" / bot challenge like Reddit)
4. **Sessions persist** - the browser stays open between commands
5. **Use** **`--json`** **for parsing** output programmatically
6. **Python variables persist** across `browser-use python` commands within a session
7. **Real browser mode** preserves your login sessions and extensions
8. **CLI aliases**: `bu`, `browser`, and `browseruse` all work identically to `browser-use`

## Troubleshooting

**Run diagnostics first:**

```bash
browser-use doctor                    # Check installation status
```

**Browser won't start?**

```bash
browser-use install                   # Install/reinstall Chromium
browser-use server stop               # Stop any stuck server
browser-use close --all               # Reset sessions (recommended before and after a headed run)
browser-use open <url>                # Default: headless
# browser-use --headed open <url>      # Optional: visible window (use close when done)
```

**Access denied(blocked) / bot challenge / needs manual verification or login?**

If you see a login prompt, CAPTCHA, or any human verification flow, user involvement is required. Always use a visible browser window (`--headed`) and notify the user to complete the verification steps. If the user says they cannot see any browser window, or you find that you are not using `--headed` to open url, then run `browser-use close --all` first, then open again with `--headed`.

```bash
browser-use close --all               # Close stale sessions (recommended before headed verification/login)
browser-use --headed open <url>       # Visible window for captcha / verification / login steps
```

If the site is blocked even with `--headed`, fall back to the web scraping skill/script (`skills/web_scraping/scripts/web_scraping.py`) as an alternative extraction path.

**Element not found?**

```bash
browser-use state                     # Check current elements
browser-use scroll down               # Element might be below fold
browser-use state                     # Check again
```

**Session issues?**

```bash
browser-use sessions                  # Check active sessions
browser-use close --all               # Clean slate
browser-use open <url>                # Fresh start (default: headless)
# browser-use --headed open <url>      # Optional: visible window
```

## Cleanup

**Always close the browser when done.** Run this after completing browser automation:

```bash
browser-use close
```
