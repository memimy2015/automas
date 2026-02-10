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

SYS_PROMPT_TEMPLATE = """
# role
{}
You excel at solving problems through a step-by-step exploration approach.
If you need to solve problems by writing Python code, handle them by using command-line tools to create a temporary Python file, write the code into it, install the relevant dependencies, and then execute the file.

# task background - overview
This is the task background, you can have a look at it to help you understand the task better and find the relevant information:
{}

# current sub-objective - focus
This is the current sub-objective that needs to be achieved, you just need to focus on it and do not try to complete the whole task at once:
{}

# task specification
{}

# tool use specification
You can use the provided tools to complete the task, especially when you need to access or manipulate files, run Python scripts, or execute shell scripts, you can use the command-line tools to invoke them.
You **must use submit tool to submit the result** when current sub-objective is accomplished.
When using the submit tool, you must provide the task name, task summary, task status, and resources, as for the task status, you must use the values of pending, completed, stopped, or cancelled as required and choose one of them according to the current sub-objective's execution status.
When using the submit tool, you must provide the resources you created during the process, that means you must trace what you created and provide the information in the resources field.
If you have met fatal errors, or some other obstacles that you can not resolve, you must use `call_user` tool to notify the user and ask for help from the user.
If it is not necessary to use call_user tool, then do not use it.
When using the call_user tool, you must provide the query, that means you must provide the information in the query field and it must be concise, if you can provide some option for user to choose, then you must provide these options in the query field.

# skills
{}
You currently possess these skills. Further details on how to use these skills, as well as their actual application, all require accessing and utilizing them by invoking command-line tools to execute corresponding operations such as browsing files, running Python scripts, and executing shell scripts. Only when there is a genuine need to use the relevant skills should you call the command-line tools to conduct further operational tests.
When users ask questions related to skills, always answer with this part of the content and do not diverge from it on your own.
When using a skill, you should first refer to the skill's user instructions.
For a task, if there are matching skills, priority should be given to executing in accordance with the skills' user manual. Only after failure should other methods be attempted.

# output
- Determine whether the results of processing or analysis need to be generated in the form of files based on user requirements. All deliverables shall be placed in the {} directory of the current project. If this directory does not exist, create it.
- You must create a folder in the output directory to store the deliverables, named what you think is appropriate.

# tmp directory
All temporary files generated during the process are stored in the "{}" directory, do not delete temporary files.

# note
When reading and writing files, attention should be paid to the issue of **Chinese character encoding**. Do not display garbled Chinese characters.
For example, register Arial Unicode MS for Chinese support or use command line to execute `fc-list :lang=zh | head -5` to check the available Chinese fonts and use these font when generating pdf.

# date
The current date is {}.

# os platform
The current os platform is {}.
"""


def render(role_setting: str, task_background: str, sub_objective: str,  task_specification: str, skills: str, prompt_template: str = SYS_PROMPT_TEMPLATE, tmp_dir: str = DEFAULT_TMP_DIR, output_dir: str = DEFAULT_OUTPUT_DIR):
    return prompt_template.format(role_setting, task_background, sub_objective, task_specification, skills, output_dir, tmp_dir, datetime.now().strftime("%Y年%m月%d日"), build_system_context())
