import os
import re
from typing import Dict, List, Optional, Tuple

def _extract_frontmatter(content: str) -> Optional[str]:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return None
    return "\n".join(lines[1:end_idx]).rstrip("\n")


def _fold_block_scalar(lines: List[str]) -> str:
    out: List[str] = []
    buf: List[str] = []
    for line in lines:
        if line.strip() == "":
            if buf:
                out.append(" ".join(buf).strip())
                buf = []
            out.append("")
        else:
            buf.append(line.strip())
    if buf:
        out.append(" ".join(buf).strip())
    return "\n".join(out).strip()


def _parse_frontmatter(frontmatter: str) -> Dict[str, str]:
    lines = frontmatter.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    fields: Dict[str, str] = {}
    i = 0
    key_re = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = key_re.match(line)
        if not m:
            i += 1
            continue
        key = m.group(1).strip()
        raw_value = m.group(2)
        value = raw_value.strip()

        if value in {"|", ">", "|-", ">-"}:
            i += 1
            block_lines: List[str] = []
            min_indent: Optional[int] = None
            while i < len(lines):
                l = lines[i]
                if l.strip() == "":
                    block_lines.append("")
                    i += 1
                    continue
                indent = len(l) - len(l.lstrip(" "))
                if indent == 0 and key_re.match(l):
                    break
                if min_indent is None:
                    min_indent = indent
                if min_indent is not None and indent >= min_indent:
                    block_lines.append(l[min_indent:])
                else:
                    block_lines.append(l.lstrip(" "))
                i += 1
            if value.startswith(">"):
                fields[key] = _fold_block_scalar(block_lines)
            else:
                fields[key] = "\n".join(block_lines).strip()
            continue

        fields[key] = value
        i += 1

    return fields

def get_skill_list():
    """
    Reads SKILL.md files from subdirectories in the skills directory 
    and returns a formatted string containing the name and description of each skill.
    """
    # Determine the project root (assuming resources/tools/skill_tool.py -> resources -> root)
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_file_dir))
    skills_dir = os.path.join(project_root, 'skills')
    
    if not os.path.exists(skills_dir):
        return ""

    skill_list = []
    
    # Iterate through all subdirectories in skills directory
    for item in os.listdir(skills_dir):
        skill_path = os.path.join(skills_dir, item)
        if os.path.isdir(skill_path):
            skill_md_path = os.path.join(skill_path, 'SKILL.md')
            if os.path.exists(skill_md_path):
                try:
                    with open(skill_md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        frontmatter = _extract_frontmatter(content)
                        if frontmatter:
                            fields = _parse_frontmatter(frontmatter)
                            if fields:
                                lines_out = []
                                for k, v in fields.items():
                                    lines_out.append(f"{k}: {v}")
                                lines_out.append(f"skill usage instructions: {skill_md_path}")
                                skill_list.append("\n".join(lines_out) + "\n")
                except Exception as e:
                    print(f"Error reading {skill_md_path}: {e}")
                    
    return "\n".join(skill_list)

if __name__ == "__main__":
    print(get_skill_list())
