---
name: render
description: Render the LMMS project to audio and play it
disable-model-invocation: false
argument-hint: [start_bar end_bar]
---

Render the dubstep_drops project and play the result.

Project path: `projects/dubstep_drops/dubstep_drops.mmp`

If arguments are provided, parse them as start_bar and end_bar:
- `/render` - render full track
- `/render 7 15` - render bars 7 through 15
- `/render 40 48` - render bars 40 through 48

Call `render` with `play=true` and the appropriate bar range.
Report the output file path when done.
