---
name: listen
description: Render a segment of the project and play it for quick previewing
disable-model-invocation: false
argument-hint: [start_bar] [end_bar]
---

Quick-preview a segment of the dubstep_drops project.

Project path: `projects/dubstep_drops/dubstep_drops.mmp`

Parse arguments as start_bar and end_bar. Both are required for this skill.
Example: `/listen 7 15` renders and plays bars 7-15.

Call `render` with `play=true`, the bar range, and report what section was played.
After playback, call `render_and_describe` on the same segment to get an audio analysis summary.
