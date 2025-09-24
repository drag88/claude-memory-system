# Project Context Template

This template defines how project context is displayed during session initialization.

## Default Template

```markdown
## 📋 Project Context: {project_name}
**Type:** {project_type} | **Language:** {primary_language}
**Size:** {estimated_size} ({code_files} code files)

### 🔧 Available Commands
{commands_section}

### 💻 Tech Stack
{tech_stack}

### 📁 Project Structure
```
{directory_structure}
```

### 🔄 Recent Changes
{recent_commits}

*Context auto-generated and cached for 7 days*
```

## Template Variables

Available variables for customization:

### Basic Information
- `{project_name}` - Detected project name
- `{project_type}` - Project type (Python, Node.js, etc.)
- `{primary_language}` - Primary programming language
- `{project_path}` - Full path to project

### Metrics
- `{estimated_size}` - Project size estimate (Small/Medium/Large)
- `{total_files}` - Total number of files
- `{code_files}` - Number of code files

### Commands
- `{commands_section}` - Formatted available commands
- `{test_command}` - Specific test command
- `{build_command}` - Specific build command
- `{lint_command}` - Specific lint command

### Structure & History
- `{directory_structure}` - Formatted directory tree
- `{tech_stack}` - Detected technologies
- `{recent_commits}` - Recent git commits
- `{key_files}` - Important project files

### Metadata
- `{gathered_at}` - When context was gathered
- `{cache_status}` - Cache validity information

## Project Type Templates

### Python Project Template
```markdown
## 🐍 Python Project: {project_name}
**Framework:** {detected_framework} | **Size:** {estimated_size}

### Quick Start
- **Test:** `{test_command}`
- **Lint:** `{lint_command}`
- **Format:** `{format_command}`

### Dependencies
{python_dependencies}

### Structure
{directory_structure}
```

### Node.js Project Template
```markdown
## 🟢 Node.js Project: {project_name}
**Framework:** {detected_framework} | **Size:** {estimated_size}

### Scripts
{npm_scripts}

### Dependencies
{node_dependencies}

### Structure
{directory_structure}
```

### Full-Stack Project Template
```markdown
## 🌐 Full-Stack Project: {project_name}
**Frontend:** {frontend_tech} | **Backend:** {backend_tech}

### Development
- **Frontend:** `{frontend_dev_command}`
- **Backend:** `{backend_dev_command}`
- **Full Stack:** `{fullstack_dev_command}`

### Services
{detected_services}

### Structure
{directory_structure}
```

## Customization

To customize templates:

1. Create project-specific template in `.claude/templates/context.md`
2. Use standard template variables
3. Add custom sections as needed
4. Template will be used instead of default

Example custom template:
```markdown
## My Custom Project: {project_name}

### Quick Commands
- Test: {test_command}
- Deploy: {deploy_command}

### Notes
This is my special project with custom workflows.
```