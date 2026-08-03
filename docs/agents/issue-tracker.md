# Issue Tracker Configuration

- **Type**: GitHub Issues (`gh`)
- **External PRs as triage surface**: No
- **CLI tool**: `gh issue`

## Conventions
- Use `gh issue list --label <label>` to query issues by state.
- Use `gh issue create --title "<title>" --body "<body>" --label "<label>"` to file issues.
- Use `gh issue edit <number> --add-label "<label>" --remove-label "<old-label>"` to transition states.
