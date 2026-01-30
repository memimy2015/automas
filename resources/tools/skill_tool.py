import os
import re

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
                        
                        # Extract frontmatter between --- lines
                        match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                        if match:
                            frontmatter = match.group(1)
                            
                            # Simple parsing of name and description
                            name_match = re.search(r'name:\s*(.+)', frontmatter)
                            desc_match = re.search(r'description:\s*(.+)', frontmatter)
                            
                            if name_match and desc_match:
                                name = name_match.group(1).strip()
                                desc = desc_match.group(1).strip()
                                skill_list.append(f"skill name: {name}\nskill description: {desc}\nskill usage instructions: {skill_md_path}\n\n")
                except Exception as e:
                    print(f"Error reading {skill_md_path}: {e}")
                    
    return "\n".join(skill_list)