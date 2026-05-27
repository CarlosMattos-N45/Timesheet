---
name: n45-fix
description: "Something isn't working? Investigate and fix bugs, errors, or unexpected behavior"
---

Run the command below via `Bash` and follow the `content` field of the returned JSON:

- **macOS / Linux:** `.n45/bin/n45 init claude -c fix`
- **Windows:** `".n45/bin/n45.exe" init claude -c fix`

If `status: "error"` → show `message` to the user.
