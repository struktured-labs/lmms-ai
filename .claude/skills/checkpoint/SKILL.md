---
name: checkpoint
description: Save a versioned checkpoint of the current LMMS project state
disable-model-invocation: false
argument-hint: [message]
---

Save a project version checkpoint using the LMMS MCP tools.

1. Call `save_project_version` on the active project file at `projects/dubstep_drops/dubstep_drops.mmp`
2. Use the message: $ARGUMENTS (or auto-generate a descriptive message if none provided)
3. Report the commit hash back to the user
