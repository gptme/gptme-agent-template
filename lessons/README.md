# Lessons

This directory contains learned lessons and constraints that help prevent known failure modes and improve reliability. These are distinct from general knowledge files in that they are specifically focused on preventing mistakes and enforcing constraints.

## What is a Lesson?

A lesson is:
- **Concise rule or constraint** that prevents known failure modes
- Specific behavior to adopt or avoid
- Often derived from past failures or near-misses
- Designed to be automatically included when relevant (via keywords)

**Key principle**: Lessons should be **actionable and context-efficient**. They guide behavior in the moment without requiring extensive reading.

## Two-File Architecture

Lessons use a two-file format for token efficiency:

### Primary Lesson (`lessons/category/lesson-name.md`)
**Purpose**: Runtime LLM guidance (auto-included via keywords)

**Length**: 30-50 lines target, 100 lines max

**Content**:
- **Rule**: One-sentence imperative (what to do)
- **Context**: When this applies (trigger condition)
- **Detection**: Observable signals (how to recognize need)
- **Pattern**: Minimal correct example (2-10 lines)
- **Outcome**: What happens when you follow it
- **Related**: Link to companion doc + related lessons

### Companion Documentation (`knowledge/lessons/lesson-name.md`)
**Purpose**: Implementation roadmap + deep context

**Length**: Unlimited (comprehensive)

**Content**:
- **Rationale**: Full explanation of why this matters
- **Examples**: Multiple detailed examples (positive and negative)
- **Verification Strategies**: How to measure adherence
- **Implementation Roadmap**: How to automate into tools
- **Origin Story**: When/why created
- **Related Work**: Dependencies, similar patterns

*Note: Companion docs are optional. Create them when you need deep context or implementation guidance.*

## Keyword Selection

Keywords determine when lessons are automatically included in context.

### Best Practices

**Use precise trigger phrases** that balance inclusion frequency with relevance:

1. **Error Messages** (Reactive): `["No module named pip", "Permission denied"]`
2. **Context Indicators** (Proactive): `["git commit", "autonomous run"]`
3. **Anti-Pattern Phrases**: `["documenting instead of executing"]`

**Precision Spectrum**:
- **Narrow** (tool lessons): Specific commands, error messages
- **Medium** (workflow lessons): Context-specific phrases
- **Broad** (core patterns): Common situations, multi-word phrases

**What to avoid**: Single generic words like `git`, `python`, `test`

### Examples

```yaml
# Good: Precise multi-word phrases
keywords: ["git commit -m", "shell output", "autonomous run"]

# Bad: Generic single words
keywords: ["git", "shell", "run"]  # Too broad, pollutes context
```

## Directory Structure

- `tools/` - Tool-specific lessons
  - Usage constraints and limitations
  - Common pitfalls with specific tools
  - Tool interaction patterns

- `patterns/` - General pattern lessons
  - Cross-tool patterns and practices
  - Task management approaches
  - Context handling

- `social/` - Human interaction lessons
  - Communication patterns
  - Social media best practices
  - Community engagement

- `workflow/` - Workflow-related lessons
  - Task management
  - Version control
  - Documentation

- `strategic/` - Strategic decision-making
  - Frameworks and principles
  - Trade-off analysis

## Lesson Format

See `TEMPLATE.md` for the standard primary lesson format.

**Required sections**:
- Rule, Context, Detection, Pattern, Outcome, Related

**Optional sections**:
- Anti-pattern examples
- Multiple pattern variations
- Exceptions

## Writing Effective Lessons

### Clarity and Brevity
- Use precise, actionable statements
- "Do X when Y" beats "Consider doing X"
- Front-load the key insight
- Remove redundancy between sections

### Concrete Examples
- Show minimal correct code/command
- Include both anti-pattern and recommended pattern
- 2-10 lines for pattern examples
- Use real commands that can be copied

### Progressive Loading
- Primary lesson gives you enough to act immediately
- Companion provides depth when needed
- Related links enable exploring connected concepts

## Best Practices

1. **Keep it Specific**:
   - Focus on one specific issue
   - Provide concrete detection signals
   - Be explicit about constraints

2. **Provide Context**:
   - Explain when lesson applies
   - Include relevant background
   - Link to related resources

3. **Make it Enforceable**:
   - Include verification checklist (in companion)
   - Add automation hooks (in companion)
   - Note exceptions explicitly

4. **Maintain Quality**:
   - Regular reviews for relevance
   - Update with new learnings
   - Migrate verbose lessons to two-file format

## Example Lessons

- [Shell Heredoc](./tools/shell-heredoc.md) - Multiline command handling
- See [TEMPLATE.md](./TEMPLATE.md) for lesson structure

## Contributing

When adding a new lesson:

1. **Choose format**: Use two-file format for new lessons
2. **Create primary lesson**: Use TEMPLATE.md, keep concise (30-50 lines)
3. **Create companion** (optional): Full implementation details in `knowledge/lessons/`
4. **Place in appropriate directory**: tools/, patterns/, workflow/, etc.
5. **Link bidirectionally**: Primary → companion, companion → primary
6. **Update this README**: Add to example lessons if notable

## Validation

All lessons can be validated using pre-commit hooks:
- Checks required sections
- Validates frontmatter
- Verifies links

Install validation: `pre-commit install`

## Related

- **Architecture**: See ARCHITECTURE.md for overall agent design
- **Knowledge Base**: knowledge/lessons/ for companion documentation
