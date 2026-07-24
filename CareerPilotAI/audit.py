import os
import re

def audit_project():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(app_dir, 'templates')
    routes_dir = os.path.join(app_dir, 'backend', 'routes')
    static_dir = os.path.join(app_dir, 'static')
    
    missing_templates = set()
    used_templates = set()
    missing_static = set()
    used_static = set()
    
    # 1. Scan routes for render_template
    for root, _, files in os.walk(routes_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = re.findall(r"render_template\(['\"]([^'\"]+)['\"]", content)
                    used_templates.update(matches)
    
    # 2. Check app.py for render_template
    with open(os.path.join(app_dir, 'app.py'), 'r', encoding='utf-8') as f:
        content = f.read()
        matches = re.findall(r"render_template\(['\"]([^'\"]+)['\"]", content)
        used_templates.update(matches)

    # 3. Scan templates for url_for('static', filename='...')
    for root, _, files in os.walk(templates_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # regex to match filename='path' or filename="path"
                    matches = re.findall(r"filename\s*=\s*['\"]([^'\"]+)['\"]", content)
                    used_static.update(matches)

    # Check templates
    for template in used_templates:
        if not os.path.exists(os.path.join(templates_dir, template)):
            missing_templates.add(template)
            
    # Check static files
    for static_file in used_static:
        if not os.path.exists(os.path.join(static_dir, static_file)):
            missing_static.add(static_file)
            
    print("Missing Templates:")
    if missing_templates:
        for m in missing_templates:
            print(f"- {m}")
    else:
        print("None!")

    print("\nMissing Static Files:")
    if missing_static:
        for m in missing_static:
            print(f"- {m}")
    else:
        print("None!")

if __name__ == "__main__":
    audit_project()
