# Project Assistant Instructions

Use this folder for project-specific assistant notes, skills, and repeatable workflows.

## Current Guidance

- Keep the repository as a monolith unless the project requirements change.
- Prefer FastAPI, Pydantic, SQLAlchemy, PostgreSQL, uv, and Ruff for the backend.
- Keep iOS-specific project files under `ios/`.
- Document external datasets before importing them.
- Do not use git commands in any case, I will handle that manually.
- Do not make any changes to the project structure or files without my permission.
- Do not make any assumptions about any task. If you are not sure about something, ask me.

**Code quality:**
- DO NOT use fallbacks unless you really have to. Try to raise value errors etc when there is an issue. Always raise from the caught exception using "raise ... from e" when writing except blocks.
- Do not assume data structures - always verify by checking where DataKeys are created.
- Do not copy patterns from other nodes if they contradict this request or not requested at all - pause and ask if unsure.
- Keep code DRY - if repeating full methods across nodes, ask if we should use mixins or a base node (an abstract base node that also inherits from Node) instead.
- Check that DataKey types match actual data structures
- Enums: Use existing enums rather than strings when it is more preferred, and suggest new Enums when needed. Don't place Enums into node class files if it can be used by different nodes from different folders.
- Ask confirmations before writing anything