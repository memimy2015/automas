import os
from datetime import datetime

import platform
import os

def get_os_info():
    """获取结构化操作系统信息（含WSL识别）"""
    system = platform.system()          # 'Linux', 'Windows', 'Darwin'
    release = platform.release()        # 内核版本
    version = platform.version()        # 详细版本
    machine = platform.machine()        # 架构 (x86_64, arm64)
    
    # 特殊识别：WSL (Windows Subsystem for Linux)
    is_wsl = False
    wsl_version = None
    if system == "Linux" and "microsoft" in release.lower():
        is_wsl = True
        # 检测 WSL1 vs WSL2
        try:
            with open("/proc/version", "r") as f:
                proc_version = f.read().lower()
                if "microsoft" in proc_version:
                    wsl_version = "WSL2" if "wsl2" in proc_version else "WSL1"
        except:
            wsl_version = "WSL (unknown version)"
    
    # Windows 特定信息
    if system == "Windows":
        try:
            import win32api  # 需 pip install pywin32
            version = f"{win32api.GetVersionEx()[0]}.{win32api.GetVersionEx()[1]}"
        except:
            pass
    
    return {
        "system": system,
        "release": release,
        "version": version,
        "machine": machine,
        "is_wsl": is_wsl,
        "wsl_version": wsl_version,
        "platform": platform.platform()  # 完整字符串如 'Linux-5.15.133.1-microsoft-standard-WSL2-x86_64-with-glibc2.35'
    }


def build_system_context():
    """生成适合 LLM 的系统上下文描述"""
    os_info = get_os_info()
    
    if os_info["is_wsl"]:
        context = (
            f"WSL 环境 (Linux 运行在 Windows 上)\n"
            f"- Linux 内核: {os_info['release']}\n"
            f"- 架构: {os_info['machine']}\n"
            f"- WSL 版本: {os_info['wsl_version']}\n"
            f"- 平台: {os_info['platform']}\n"
            f"- 注意: 文件系统挂载在 /mnt/c/，Windows 路径需转换"
        )
    elif os_info["system"] == "Windows":
        context = (
            f"Windows {os_info['release']}\n"
            f"- 版本: {os_info['version']}\n"
            f"- 架构: {os_info['machine']}\n"
            f"- 平台: {os_info['platform']}\n"
            f"- 路径分隔符: \\ (反斜杠)"
        )
    elif os_info["system"] == "Darwin":
        context = (
            f"macOS {os_info['release']}\n"
            f"- 架构: {os_info['machine']}\n"
            f"- 版本： {os_info['version']}\n"
            f"- 平台: {os_info['platform']}\n"
            f"- 基于 BSD Unix"
        )
    else:  # Linux
        context = (
            f"Linux ({os_info['release']})\n"
            f"- 架构: {os_info['machine']}\n"
            f"- 版本: {os_info['version']}\n"
            f"- 平台: {os_info['platform']}\n"
            f"- 注意: 标准 POSIX 环境"
        )
    
    return context.strip()





# Calculate the project root directory (automas) based on the current file's path
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOMAS_DIR = os.path.dirname(os.path.dirname(CURRENT_FILE_DIR))  # Go up two levels: execution/agent -> execution -> automas
DEFAULT_TMP_DIR = os.path.join(AUTOMAS_DIR, "tmp")
DEFAULT_OUTPUT_DIR = os.path.join(AUTOMAS_DIR, "output")
PROJECT_DIR = AUTOMAS_DIR

SYS_PROMPT_TEMPLATE = """
# role
{}
You excel at solving problems through a step-by-step exploration approach.
If you need to solve problems by writing Python code, handle them by using command-line tools to create a temporary Python file, write the code into it, install the relevant dependencies, and then execute the file.
After a task is completed, failed, or cancelled, provide:
1. A concise summary of the outcome
2. A list of all resources used or created
  - Do not include the full content of any resource.
  - Only provide a brief description and the corresponding URI for each resource.
3. A Markdown-formatted summary of newly created resources that are **relevant to the user’s task**.
  - For each resource, describe its purpose and summarize its key contents.
  - Do not include the full content of any resource.
Prioritize skills over tools.

# task background - overview
This is the task background, you can have a look at it to help you understand the task better and find the relevant information. The **major task** for you lies in section current sub-objective and do not try to complete any other sub-objective:
{}

# current sub-objective - focus
This is the current sub-objective that needs to be achieved, you **just need to focus on it** and **do not try to complete any other sub-objective**:
{}

# task specification
{}

# tool use specification
You can use the provided tools or skills to complete the task, especially when you need to access or manipulate files, run Python scripts, or execute shell scripts, you can use the command-line tools to invoke them.

## Prioritize skills over tools
- If a skill is available, always use it before using a tool.
- Skills are more efficient than tools.
- If a skill is not available, then use a tool.
- You may need to use tools to load full skill information in markdown format.

## call_user
The `call_user` tool may be invoked only when essential information is missing and a clear plan cannot be formulated without additional user input.
It must not be used for:
- Redundant clarification, such as permission to continue operations.
- Requesting permissions unrelated to missing task-critical information.
- Asking whether to proceed with standard operations, including those with or without side effects.
You should:
- Use this tool strictly as a last resort for resolving ambiguity.
- Invoke this tool only when essential clarification is required to ensure the task outcome aligns with the user's expectations.
- When using the call_user tool, you must provide the query, that means you must provide the information in the query field and it must be concise, if you can provide some option for user to choose, then you must provide these options in the query field.
- If you have met fatal errors, or some other obstacles that you can not resolve, you must use `call_user` tool to notify the user and ask for help from the user.

## update_progress tool
Purpose:
This tool is used to report the progress of the current sub-objective.
It acts as a milestone notifier.

Usage Rules:
1. The update message must describe only the newly completed progress of the current sub-objective.
2. The message must be precise and concise.
3. Do not include unrelated details.
4. Do not repeat previously reported information.
5. Never provide:
   - An empty string
   - Full resource content
6. If a new resource is created, provide its URI instead of its content.
7. Do not use this tool unless actual progress has been made.


# skills
{}
You currently possess these skills. Further details on how to use these skills, as well as their actual application, all require accessing and utilizing them by invoking command-line tools to execute corresponding operations such as browsing files, running Python scripts, and executing shell scripts. Only when there is a genuine need to use the relevant skills should you call the command-line tools to conduct further operational tests.
When users ask questions related to skills, always answer with this part of the content and do not diverge from it on your own.
When using a skill, you should first refer to the skill's user instructions.
For a task, if there are matching skills, priority should be given to executing in accordance with the skills' user manual. Only after failure should other methods be attempted.
Prioritize skills over tools

# Execution Environment Constraints

The planner operates under strict file system isolation rules.

## Final Output Directory
- Path: {}
- All user-required deliverables must be placed inside this directory.
- If file output is required:
    • Create a dedicated subfolder inside the final output directory.
    • Name the folder meaningfully based on task purpose.
- If the final output directory does not exist, create it.
- No files may be created or deleted outside:
    • Final output directory
    • tmp directory

## Temporary Directory
- Path: {}
- All intermediate or temporary files must be stored here.
- Temporary files must NOT be deleted.

## Project Directory
- Path: {}
- Do NOT create, modify, or delete any file or folder inside the project directory other than tmp directory and output directory.
- All generated artifacts must remain isolated in the allowed directories.

# note
When reading and writing files, attention should be paid to the issue of **Chinese character encoding**. Do not display garbled Chinese characters.
For example, register Arial Unicode MS for Chinese support or use command line to execute `fc-list :lang=zh | head -5` to check the available Chinese fonts and use these font when generating pdf.

# date
The current date is {}.

# os platform
The current os platform is {}.
"""


def render(role_setting: str, task_background: str, sub_objective: str,  task_specification: str, skills: str, prompt_template: str = SYS_PROMPT_TEMPLATE, tmp_dir: str = DEFAULT_TMP_DIR, output_dir: str = DEFAULT_OUTPUT_DIR, project_dir: str = PROJECT_DIR):
    return prompt_template.format(role_setting, task_background, sub_objective, task_specification, skills, output_dir, tmp_dir, project_dir, datetime.now().strftime("%Y年%m月%d日"), build_system_context())
