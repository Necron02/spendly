---
description: List every custom subagent defined in the current project's .claude/agents directory, whether running or not
---

# List All Project Agents

Display a complete inventory of the custom subagent definitions in this project's `.claude/agents/` directory.

## Instructions

1. Use your existing file-reading and directory-listing tools to inspect `.claude/agents/` directly.
2. Find every `.md` file in that directory, including Markdown files in nested subdirectories.
3. Read each file's YAML frontmatter and extract its `name` and `description`.
4. List every agent definition found, regardless of whether the agent is currently running, idle, or has never been used.
5. Display the results alphabetically by agent name.

## Output format

# All Project Agents

For each discovered agent, display:

- **Name:** The agent's `name` from its frontmatter, or the filename if missing.
- **Description:** The agent's `description`, or `Not specified` if missing.
- **File:** Its relative path within the project.

Finish with:

- **Total agent files:** Number of Markdown files discovered.
- **Valid agent definitions:** Number of files with valid agent frontmatter and a usable agent name.

## Constraints

- This is a read-only inventory operation.
- DO NOT create, edit, or delete any files.
- DO NOT create `inventory.py`, any other Python script, a JavaScript script, a shell script, or any helper utility.
- DO NOT install packages or run setup commands.
- DO NOT launch, invoke, or delegate to any subagents.
- DO NOT inspect runtime sessions to determine which agents are active.
- DO NOT list only running agents. Include every agent definition discovered on disk.
- DO NOT include globally installed agents from `~/.claude/agents/`; inspect only this project's `.claude/agents/` directory.
- If the directory does not exist or contains no Markdown files, report that clearly.
- If a file has missing or invalid frontmatter, include it in the inventory and identify the issue.
- Do not guess or invent agents. Report only what is actually present on disk.
- Keep the output concise. Do not explain your implementation or propose creating helper files.