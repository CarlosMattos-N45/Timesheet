---
name: n45-run
description: 'Start or stop the application (dev server, containers, local services)'
disable-model-invocation: true
---

Run the command below via `Bash` and follow the `content` field of the returned JSON:

- **macOS / Linux:** `.n45/bin/n45 init claude -c run`
- **Windows:** `".n45/bin/n45.exe" init claude -c run`

If `status: "error"` → show `message` to the user.
