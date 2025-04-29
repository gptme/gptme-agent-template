# Lessons

This directory contains learned lessons and constraints that help prevent known failure modes and improve reliability. These are distinct from general knowledge files in that they are specifically focused on preventing mistakes and enforcing constraints.

## What is a Lesson?

A lesson is:

- A specific constraint or rule learned from experience
- Often derived from past failures or near-misses
- Highly contextual and prescriptive
- Includes concrete examples of both correct and incorrect approaches
- Designed to prevent known failure modes

## Directory Structure

- `tools/` - Tool-specific lessons

  - Usage constraints and limitations
  - Common pitfalls with specific tools
  - Tool interaction patterns
  - Examples: patch syntax, shell limitations, browser capabilities

- `patterns/` - General pattern lessons

  - Cross-tool patterns and practices
  - Task management approaches
  - Context handling
  - Examples: tool availability checking, context preservation, error handling

- `social/` - Human interaction lessons

  - Communication patterns
  - Social media best practices
  - Community engagement
  - Examples: Twitter best practices, user interaction patterns

- `workflow/` - Workflow-related lessons
  - Task management
  - Version control
  - Documentation
  - Examples: commit message format, branch management

## Lesson Format

Each lesson should include:

### Required Fields

- Context: When is this lesson relevant?
- Problem: What went wrong?
- Constraint: What rules should be followed?
- Explanation: Why does this happen?
- Examples: Both incorrect and correct approaches
- Origin: When/how was this learned?

### Optional Fields

- Notes: Additional context or considerations
- Impact: Severity/frequency of the issue
- Alternatives: Other approaches to consider

## Best Practices

1. **Keep it Specific**

   - Focus on one specific issue
   - Provide concrete examples
   - Be explicit about constraints

2. **Provide Context**

   - Explain when the lesson applies
   - Include relevant background
   - Link to related resources

3. **Show Both Sides**

   - Include incorrect examples
   - Show correct alternatives
   - Explain the differences

4. **Maintain Quality**
   - Regular reviews for relevance
   - Update with new learnings
   - Remove outdated lessons

## Example Lessons

- [Shell Heredoc](./tools/shell-heredoc.md) - Proper multiline command handling

## Contributing

When adding a new lesson:

1. Use the established format
2. Place in appropriate directory
3. Include concrete examples
4. Link from relevant documentation
5. Update this README if needed
