---
name: n45-status
description: 'View current roadmap progress: active phase, tasks done/pending, and blockers'
disable-model-invocation: true
---

Run the command below via `Bash` and follow the `content` field of the returned JSON:

- **macOS / Linux:** `.n45/bin/n45 init claude -c status`
- **Windows:** `".n45/bin/n45.exe" init claude -c status`

If `status: "error"` → show `message` to the user.
