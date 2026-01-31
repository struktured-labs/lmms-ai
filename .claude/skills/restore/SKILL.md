---
name: restore
description: Restore the LMMS project to a previous version
disable-model-invocation: false
argument-hint: [version_hash]
---

Restore the dubstep_drops project to a previous version.

Project path: `projects/dubstep_drops/dubstep_drops.mmp`

If a version hash is provided ($ARGUMENTS), restore to that specific version using `restore_project_version`.

If no hash is provided:
1. Call `list_project_versions` to show recent versions
2. Present the list to the user so they can pick one
