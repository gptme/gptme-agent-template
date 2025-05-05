# Lesson: Avoid Heredoc in Shell Commands

## Context
When using the shell tool to execute commands in gptme

## Problem
Agents sometimes try to use EOF/heredoc syntax for multiline input, but this isn't supported by gptme's shell tool and will fail.

## Constraint
Never use heredoc/EOF syntax in shell commands.
Use alternative approaches like:
- echo with pipes
- writing to file first
- using printf
- using command substitution

## Explanation
The shell tool executes commands line by line and cannot handle heredoc syntax.
Attempting to use heredoc will result in syntax errors or unexpected behavior.

## Example - Incorrect
```shell
cat << EOF > config.yaml
name: myproject
version: 1.0.0
EOF
```

## Example - Correct
```shell
echo "name: myproject
version: 1.0.0" > config.yaml
```

Or using the save tool:
```save config.yaml
name: myproject
version: 1.0.0
```

## Origin
- Date: 2024-12-05
- Source: Common failure pattern in gptme
- Impact: Medium (frequently attempted, but has clear alternatives)
- Fixed by: Adding this constraint to RAG context

## Notes
- The save tool is often a better choice for writing files
- For complex multiline content, prefer the save tool over shell commands
- When shell commands are needed, use echo or printf
