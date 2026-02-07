# Phase 2: Claude AI Integration in LMMS GUI

## Revised Design Document — Prompt / Listen / Iterate Loop

**Status:** Draft v2
**Date:** 2026-02-06
**Supersedes:** Original Phase 2 design (branch `claude/integrate-claude-lmms-staging-wI1TM`)

---

## 1. Vision

A musician types a prompt inside LMMS and **hears the result within seconds**. They
refine with follow-up prompts — "same rhythm but darker," "drop the bass an octave
at bar 16," "try again" — and hear each iteration immediately. When it sounds right,
they keep it. Every step is checkpointed and reversible.

This is not a visual diff tool. Musicians think in sounds, not diffs. The primary
feedback channel is auditory. Visual overlays (ghost notes, colored automation curves)
are a secondary aid, not the decision-making interface.

### Core Loop

```
Type prompt → Hear it → Refine → Hear it again → Keep / Discard
```

Three steps from idea to decision. Everything else is optional power-user surface.

### Non-Goals for MVP

- Per-note / per-element accept/reject (Phase 2b)
- Ghost note rendering in piano roll (Phase 2b)
- Real-time project state sync (Phase 2c)
- Multiple simultaneous AI sessions (future)
- Local model support (future, but architecture should not preclude it)

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   LMMS GUI (Qt/C++)                  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │Song Editor│  │Piano Roll│  │ AI Prompt Panel   │  │
│  │           │  │          │  │ ┌───────────────┐ │  │
│  │           │  │          │  │ │ Chat input    │ │  │
│  │           │  │          │  │ │ Status/stream │ │  │
│  └───────────┘  └──────────┘  │ │ Keep/Discard  │ │  │
│                               │ │ Try Again     │ │  │
│                               │ │ History       │ │  │
│                               │ └───────────────┘ │  │
│                               └────────┬──────────┘  │
│                                        │             │
└────────────────────────────────────────┼─────────────┘
                                         │
                      IPC (WebSocket on localhost)
                                         │
                  ┌──────────────────────▼───────────┐
                  │        AI Bridge Server           │
                  │           (Python)                │
                  │                                   │
                  │  1. Receive prompt + project path  │
                  │  2. Copy project to .tmp/          │
                  │  3. Apply MCP tools to copy        │
                  │  4. Render copy to audio            │
                  │  5. Send audio + diff summary back │
                  │  6. On "Keep": surgical edit real   │
                  │     project + checkpoint           │
                  └──────────┬────────────────────────┘
                             │
                      Claude API (or future: local LLM)
```

### Key Design Decisions

1. **Apply-to-copy, not intercept-and-diff.** The AI Bridge applies MCP tool calls
   to a temporary copy of the project, then renders it. No complex diff model needed
   for MVP. The diff is implicit: the user hears the difference.

2. **Offline rendering, not real-time merge.** Preview audio is pre-rendered from the
   temp copy using LMMS command-line renderer (already works). No audio engine thread
   safety issues, no ghost note merging, no DiffPlaybackProxy. Simple and bulletproof.

3. **Surgical edit on accept.** When the user clicks "Keep," the Bridge replays the
   same MCP tool calls against the real project using surgical XML editing. Then
   auto-checkpoints via `save_project_version()`.

4. **Stateless iterations.** Each "Try Again" starts from the current real project
   state (not from a previous attempt). This avoids stacking diffs and the complexity
   of diff-on-diff. The iteration history stores rendered audio for A/B comparison,
   not project states.

---

## 3. Components

### 3.1 AI Prompt Panel (C++ / Qt)

A dock widget in LMMS, toggled from the menu bar.

**Elements:**
- **Chat input** — Single-line text field + Send button (Ctrl+Enter to submit)
- **Streaming status** — Shows "Thinking...", "Generating bass pattern...", "Rendering..."
  as the Bridge streams progress
- **Audio player** — Inline waveform + play/pause for the rendered preview. Shows the
  change region (e.g., bars 32-48) with a few bars of context on each side.
- **Keep / Discard / Try Again** — Three prominent buttons. "Try Again" re-rolls with
  the same prompt. "Keep" applies + checkpoints. "Discard" throws away the temp copy.
- **Refine input** — When a preview is active, the chat input becomes a refinement
  field. "Same but one octave lower." "More syncopation." "Keep the rhythm, change
  the notes." Submitting a refinement generates a new preview.
- **Iteration history** — Sidebar list of previous attempts for this prompt. Click any
  to re-listen. "Keep" works on any historical attempt, not just the latest.
- **Mute toggle** — "Hear Original / Hear With Changes" button that switches between
  playing the original project audio and the modified version for the same bar range.

**What it does NOT have (in MVP):**
- No change list / diff viewer
- No per-track accept/reject buttons
- No ghost note rendering hooks

```cpp
// src/gui/ai/AIPromptPanel.h
class AIPromptPanel : public QDockWidget {
    Q_OBJECT
public:
    AIPromptPanel(MainWindow* parent);

private:
    QLineEdit* m_promptInput;
    QLabel* m_statusLabel;
    AudioPreviewWidget* m_previewPlayer;  // custom waveform + transport
    QPushButton* m_keepBtn;
    QPushButton* m_discardBtn;
    QPushButton* m_tryAgainBtn;
    QListWidget* m_iterationHistory;
    QPushButton* m_abToggle;              // original vs modified
    QWebSocket* m_socket;

    QString m_currentPrompt;
    int m_iterationCount;

signals:
    void previewReady(const QString& audioPath, int startBar, int endBar);
    void changesApplied(const QString& checkpointHash);
    void changesDiscarded();

private slots:
    void onSendClicked();
    void onKeep();
    void onDiscard();
    void onTryAgain();
    void onRefine();
    void onMessageReceived(const QString& message);
    void onIterationSelected(int index);
    void onABToggle();
};
```

### 3.2 Audio Preview Widget (C++ / Qt)

A minimal waveform display with transport controls, embedded in the AI Panel.

- Loads rendered `.wav` or `.flac` from the Bridge
- Shows waveform with bar markers
- Play / Pause / Seek
- Highlights the change region (colored bar range overlay)
- Loop toggle for the change region
- Auto-plays when a new preview arrives (configurable)

This is a self-contained widget with no dependency on the LMMS audio engine. It plays
audio files directly via Qt Multimedia (`QMediaPlayer` / `QAudioOutput`). This avoids
all threading issues with the main audio engine.

### 3.3 AI Bridge Server (Python)

Extends the existing `lmms-mcp-server` codebase.

```python
# src/ai_bridge/server.py
class AIBridgeServer:
    """WebSocket server that handles prompt → preview → accept flow."""

    def __init__(self, api_key: str, project_dir: str):
        self.claude = anthropic.Anthropic(api_key=api_key)
        self.mcp_tools = load_mcp_tools()
        self.project_dir = project_dir
        self.tmp_dir = Path(project_dir) / ".tmp" / "ai_previews"
        self.iterations: dict[str, list[Iteration]] = {}  # prompt_id -> attempts

    async def handle_prompt(self, ws, msg):
        """Generate changes and render a preview."""
        prompt_id = make_id()
        project_path = msg["context"]["project_path"]
        prompt = msg["text"]

        # 1. Copy project to temp
        tmp_project = self.tmp_dir / f"{prompt_id}.mmp"
        shutil.copy2(project_path, tmp_project)

        await ws.send(status("Thinking..."))

        # 2. Ask Claude to generate MCP tool calls
        tool_calls = await self.generate_tool_calls(prompt, project_path, msg["context"])

        # 3. Apply tool calls to the temp copy
        await ws.send(status("Applying changes..."))
        for call in tool_calls:
            await self.apply_tool(call, tmp_project)

        # 4. Render the modified region
        await ws.send(status("Rendering preview..."))
        start_bar = detect_change_region_start(tool_calls)
        end_bar = detect_change_region_end(tool_calls)
        context_bars = 4  # extra bars before/after for context

        preview_audio = self.tmp_dir / f"{prompt_id}_preview.flac"
        render(tmp_project, preview_audio,
               start_bar=max(0, start_bar - context_bars),
               end_bar=end_bar + context_bars)

        # 5. Also render the original for A/B comparison
        original_audio = self.tmp_dir / f"{prompt_id}_original.flac"
        render(project_path, original_audio,
               start_bar=max(0, start_bar - context_bars),
               end_bar=end_bar + context_bars)

        # 6. Store iteration for history
        iteration = Iteration(
            prompt=prompt,
            tool_calls=tool_calls,
            preview_audio=preview_audio,
            original_audio=original_audio,
            start_bar=start_bar,
            end_bar=end_bar,
            tmp_project=tmp_project,
        )
        self.iterations.setdefault(prompt_id, []).append(iteration)

        # 7. Send preview to GUI
        await ws.send(json.dumps({
            "type": "preview",
            "prompt_id": prompt_id,
            "iteration": 0,
            "description": summarize_changes(tool_calls),
            "preview_audio": str(preview_audio),
            "original_audio": str(original_audio),
            "start_bar": start_bar,
            "end_bar": end_bar,
        }))

    async def handle_keep(self, ws, msg):
        """Apply the selected iteration to the real project via surgical edits."""
        prompt_id = msg["prompt_id"]
        iteration_idx = msg.get("iteration", -1)  # default: latest
        iteration = self.iterations[prompt_id][iteration_idx]

        # Replay tool calls against the real project using surgical editing
        for call in iteration.tool_calls:
            await self.apply_tool_surgical(call, iteration.original_project_path)

        # Auto-checkpoint
        checkpoint = save_project_version(
            iteration.original_project_path,
            f"AI: {iteration.prompt}"
        )

        await ws.send(json.dumps({
            "type": "applied",
            "prompt_id": prompt_id,
            "checkpoint": checkpoint,
        }))

        # Cleanup temp files for this prompt
        self.cleanup(prompt_id)

    async def handle_try_again(self, ws, msg):
        """Re-generate with the same prompt (new Claude call, fresh variation)."""
        # Same as handle_prompt but appends to existing iterations list
        ...

    async def handle_refine(self, ws, msg):
        """Generate a new preview with a refinement prompt."""
        # Builds on the original prompt: "Original: X. Refinement: Y"
        # Applies to a fresh copy of the real project (not the previous temp)
        ...
```

### 3.4 Surgical Applicator (Python)

The `apply_tool_surgical()` method is the critical safety layer. It replays MCP tool
calls using surgical XML editing — never the lossy parse→model→write pipeline.

**Current surgical functions:**
- `surgical_update_automation_points()` — proven, battle-tested

**New surgical functions needed for MVP:**
- `surgical_add_notes()` — Insert `<note>` elements into a specific `<midiclip>`
  without touching anything else in the track
- `surgical_remove_notes()` — Remove specific `<note>` elements by position+key
- `surgical_add_track()` — Append a new `<track>` element to the `<song>` without
  modifying existing tracks (create-only, inherently safe)
- `surgical_set_track_volume()` — Modify a single attribute on a `<track>` element
- `surgical_set_track_pan()` — Same pattern

**Each surgical function MUST:**
1. Parse raw XML with `etree.fromstring()` (NOT through the model)
2. Navigate to the specific element
3. Modify ONLY the target attributes/children
4. Write raw XML back
5. Round-trip validate: re-parse, verify only intended changes exist
6. On failure: restore original bytes, return error

This is the same pattern documented in CLAUDE.md under "CRITICAL: MCP XML Editing
Design Rules." No exceptions.

---

## 4. IPC Protocol (WebSocket)

### Why WebSocket
- Qt has `QWebSocket` (add `Qt5::WebSockets` to CMake)
- Python has `websockets` (already in our stack)
- Bidirectional streaming for progress updates
- Cross-platform (Linux now, macOS/Windows later)
- JSON messages, no binary protocol to debug

### Connection Lifecycle
1. LMMS launches → AI Panel starts WebSocket client connecting to `ws://localhost:19840`
2. If Bridge not running, Panel shows "AI Bridge offline. Start with: `uv run ai-bridge`"
3. Bridge starts → accepts connection → sends `{"type": "hello", "version": "1"}`
4. Panel shows "Connected" status
5. On disconnect: Panel shows "Disconnected", auto-reconnects every 5s
6. Heartbeat ping every 30s to detect dead connections

### Message Types

**Client (LMMS) → Server (Bridge):**

```json
// Submit a new prompt
{
    "type": "prompt",
    "id": "msg_001",
    "text": "add a snare fill at bars 15-16 with rising velocity",
    "context": {
        "project_path": "/path/to/project.mmp",
        "selected_tracks": [2],
        "cursor_bar": 15,
        "loop_start": 12,
        "loop_end": 20,
        "bpm": 140,
        "track_names": ["Kick", "Hi-Hat", "Snare", "Wobble Bass"]
    }
}

// Keep a specific iteration
{
    "type": "keep",
    "prompt_id": "prompt_001",
    "iteration": 2
}

// Discard all iterations for a prompt
{ "type": "discard", "prompt_id": "prompt_001" }

// Try again with same prompt
{ "type": "try_again", "prompt_id": "prompt_001" }

// Refine the current direction
{
    "type": "refine",
    "prompt_id": "prompt_001",
    "text": "same rhythm but one octave lower"
}

// Undo last accepted change
{ "type": "undo" }
```

**Server (Bridge) → Client (LMMS):**

```json
// Connection established
{ "type": "hello", "version": "1" }

// Streaming progress
{ "type": "status", "prompt_id": "prompt_001", "text": "Generating snare pattern..." }

// Preview ready
{
    "type": "preview",
    "prompt_id": "prompt_001",
    "iteration": 0,
    "description": "Added 16th-note snare fill with velocity ramp 60→120",
    "preview_audio": "/path/to/.tmp/ai_previews/prompt_001_preview.flac",
    "original_audio": "/path/to/.tmp/ai_previews/prompt_001_original.flac",
    "start_bar": 15,
    "end_bar": 16
}

// Changes applied to real project
{
    "type": "applied",
    "prompt_id": "prompt_001",
    "checkpoint": "abc1234",
    "message": "AI: add a snare fill at bars 15-16 with rising velocity"
}

// Error
{
    "type": "error",
    "prompt_id": "prompt_001",
    "message": "Claude API timeout, try again"
}
```

### Context Awareness

The prompt message includes lightweight context (track names, cursor position, BPM,
loop region) rather than the full project XML. The Bridge reads the project file
directly from disk when needed. This avoids sending large XML payloads over WebSocket
and avoids the lossy-model problem entirely.

The Bridge uses the existing `parse_project()` for read-only context (building Claude's
system prompt), but NEVER for writes.

---

## 5. The Iteration Cycle

This is the most important interaction in the entire system.

### Fast Path (80% of users)

```
1. User types: "add a wobble bass fill at bar 32"
2. Status: "Thinking..." → "Applying changes..." → "Rendering..."
3. Audio auto-plays the modified region (bars 28-36 with context)
4. User clicks "Keep" → surgical edit + checkpoint → done
```

Three clicks: type, listen, keep. Target: under 15 seconds from prompt to audio.

### Iteration Path (Refining an Idea)

```
1. User types: "add a drum fill at bar 16"
2. Preview plays. Sounds okay but too busy.
3. User types in refine box: "simpler, just snare and kick"
4. New preview plays. Better but too quiet.
5. User types: "louder, velocity 100+"
6. New preview plays.
7. User clicks "Keep"
```

Each refinement is a fresh generation informed by the conversation history. The Bridge
maintains the full prompt chain for Claude's context.

### A/B Comparison Path

```
1. User gets a preview
2. Clicks "Hear Original" — plays the same bar range from the unmodified project
3. Clicks "Hear With Changes" — plays the modified version
4. Toggles back and forth
5. Decides and clicks Keep or Discard
```

Both audio files are pre-rendered. No real-time audio engine involvement. Toggle is
instant (just switching which audio file plays).

### Try Again Path (Want a Different Take)

```
1. User types: "add a chord progression over bars 1-8"
2. Preview plays. Not feeling it.
3. User clicks "Try Again"
4. New Claude call with same prompt, temperature ensures variation
5. New preview plays.
6. User can browse iteration history: "Attempt 1", "Attempt 2", "Attempt 3"
7. Clicks any iteration to re-listen, then "Keep" on the one they like
```

### Undo Path

```
1. User accepted a change
2. Realizes it clashes with the next section
3. Clicks "Undo" in AI Panel (or Ctrl+Z if integrated with LMMS undo)
4. Bridge restores from the auto-checkpoint
5. Project returns to pre-accept state
```

This uses the existing `restore_project_version()` infrastructure, which is already
battle-tested.

---

## 6. LMMS C++ Changes

### New Files

| File | Purpose |
|------|---------|
| `include/gui/ai/AIPromptPanel.h` | Dock widget header |
| `src/gui/ai/AIPromptPanel.cpp` | Chat + preview + keep/discard UI |
| `include/gui/ai/AudioPreviewWidget.h` | Waveform player header |
| `src/gui/ai/AudioPreviewWidget.cpp` | Self-contained audio file player |

### Modified Files

| File | Change |
|------|--------|
| `src/gui/MainWindow.cpp` | Add AI Panel toggle to View menu, instantiate dock widget |
| `CMakeLists.txt` | Add new source files, `find_package(Qt5 COMPONENTS WebSockets Multimedia REQUIRED)` |

### What We Do NOT Modify (in MVP)

- `PianoRoll.cpp` — no ghost note rendering
- `AutomationEditor.cpp` — no overlay curves
- `SongEditor.cpp` — no ghost track rendering
- `MidiClipView.cpp` — untouched
- `AudioEngine.cpp` — untouched (no real-time merge)
- `ProjectJournal` — untouched (checkpointing via git, not journal)

**Total C++ surface area: 4 new files, 2 modified files.** This is deliberately
minimal to reduce risk and get to a working prototype fast.

### Build Toggle

```cmake
option(LMMS_BUILD_AI_INTEGRATION "Build AI prompt panel and bridge client" OFF)

if(LMMS_BUILD_AI_INTEGRATION)
    find_package(Qt5 COMPONENTS WebSockets Multimedia REQUIRED)
    add_subdirectory(src/gui/ai)
endif()
```

Off by default. Our fork enables it. Does not affect upstream LMMS builds.

---

## 7. Python-Side Changes

### New Files in `lmms-mcp-server/`

| File | Purpose |
|------|---------|
| `src/ai_bridge/server.py` | WebSocket server, prompt handling, iteration management |
| `src/ai_bridge/renderer.py` | Wrapper around LMMS CLI renderer for preview generation |
| `src/ai_bridge/prompt_builder.py` | Builds Claude system prompt with project context |
| `src/ai_bridge/surgical.py` | Surgical XML editing functions (notes, tracks, effects) |

### New Surgical Functions

Priority order for MVP:

1. **`surgical_add_notes(project_path, track_index, clip_index, notes)`**
   - Finds `<track>` by index → `<midiclip>` by index
   - Appends `<note>` elements with pos, len, key, vol, pan, type attributes
   - Does NOT touch existing notes or any other element

2. **`surgical_add_track(project_path, track_xml)`**
   - Appends a complete `<track>` element (pre-built by the Bridge) before `</song>`
   - Does NOT modify existing tracks
   - The track XML is generated by the Bridge using known-good templates

3. **`surgical_set_track_attribute(project_path, track_index, attr, value)`**
   - Sets a single attribute (vol, pan, muted, etc.) on a `<track>` element
   - Minimal, targeted, safe

4. **`surgical_update_automation_points()`** — already exists and works

Each function follows the existing pattern from `writer.py:surgical_update_automation_points()`.

---

## 8. Rendering Strategy

Preview rendering uses the LMMS command-line renderer, which already works perfectly
with our project format.

```python
async def render_preview(project_path: Path, output_path: Path,
                         start_bar: int, end_bar: int, bpm: int = 140):
    """Render a segment of the project to audio for preview."""
    cmd = [
        str(LMMS_BINARY),
        "--render", str(project_path),
        "--output", str(output_path),
        "--format", "wav",           # wav for faster encode (no FLAC overhead)
        "--samplerate", "44100",
        "--loop",                     # render only the specified region
    ]
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.wait()
```

**Performance target:** Render 4-8 bars in under 3 seconds. The LMMS renderer is
fast for short segments. If it becomes a bottleneck, we can reduce sample rate to
22050 for previews (sufficient for auditioning).

**Two renders per preview:** One of the modified project (what the AI changed) and
one of the original project (same bar range). Both are needed for A/B comparison.
These can run in parallel.

---

## 9. Checkpointing and Undo

Every accepted change is automatically checkpointed using the existing
`save_project_version()` MCP tool, which creates a git commit in the project
directory.

**Undo flow:**
1. User clicks "Undo" in AI Panel
2. Bridge calls `restore_project_version()` with the previous checkpoint hash
3. Project file is restored to pre-accept state
4. Bridge sends `{"type": "restored", "checkpoint": "prev_hash"}` to GUI
5. GUI reloads the project (or, if we implement it later, hot-reloads via IPC)

**Checkpoint naming convention:**
```
AI: add a snare fill at bars 15-16 with rising velocity
AI: same rhythm but one octave lower (refinement)
AI: undo - restored to checkpoint abc1234
```

This gives a readable git log of all AI-assisted changes.

---

## 10. Implementation Phases

### Phase 2a: The Loop (8-10 weeks)

**Goal:** Working prompt → listen → iterate → keep/discard cycle.

| Week | Deliverable |
|------|-------------|
| 1-2 | AI Bridge Server: WebSocket, prompt handling, temp copy + render pipeline |
| 3-4 | AI Prompt Panel: Qt dock widget, chat input, WebSocket client, status display |
| 4-5 | Audio Preview Widget: waveform display, play/pause, A/B toggle |
| 5-6 | End-to-end integration: prompt → Claude → MCP tools → render → play in GUI |
| 6-7 | Surgical applicator: `surgical_add_notes()`, `surgical_add_track()` |
| 7-8 | Keep/Discard/Undo flow with auto-checkpointing |
| 8-9 | Try Again + Refine + iteration history |
| 9-10 | Testing, edge cases, reconnection handling, error states |

**Milestone gate:** Can type a prompt, hear the result, refine it, and keep the
version I like — all from within the LMMS GUI. The dubstep_drops project serves as
the integration test.

### Phase 2b: Visual Feedback (6-8 weeks after 2a)

- Ghost note rendering in piano roll (green semi-transparent notes for additions)
- Ghost automation curves in automation editor
- Per-track accept/reject (change list in AI Panel with checkboxes)
- Diff summary panel ("Added 32 notes to Snare, modified Wobble Bass automation")
- Auto-loop around change region during preview playback

### Phase 2c: Deep Integration (8-12 weeks after 2b)

- Hot-reload: GUI reflects accepted changes without full project reload
- Context-aware prompts: AI sees selected track, cursor position, loop region
- "Explain this section" — AI reads selected bars and describes them
- Smart suggestions: "This sounds like it needs a breakdown here"
- Real-time project sync (IPC socket for bidirectional state)

### Phase 2d: Advanced (future)

- Collaborative: multiple AI sessions with mergeable suggestions
- Alternative gallery: generate 3-4 variations, audition each, pick favorite
- Mix assistant: "the bass and kick are fighting" → EQ + sidechain suggestions
- Reference track analysis: "match the energy of this section"
- Local model backend (Ollama / llama.cpp) for offline use
- Voice input: speak prompts instead of typing

---

## 11. Comparison with Existing Tools

| Feature | Suno/Udio | Mozart AI | MCP Servers | This Project |
|---------|-----------|-----------|-------------|-------------|
| Natural language input | Yes | Yes | Yes (via Claude) | Yes |
| Editable output | No (audio blob) | Yes (their DAW) | Yes (DAW-native) | Yes (LMMS-native) |
| Preview before commit | No | Unknown | No | **Yes** |
| Iteration/refinement | No | Unknown | Manual re-prompt | **First-class** |
| Auto-checkpoint | No | No | No | **Yes** |
| A/B comparison | No | No | No | **Yes** |
| Open source | No | No | Mostly yes | **Yes** |
| Works offline | No | No | Partially | Future (local LLM) |
| Runs in real DAW | No | Own DAW | Yes | **Yes** |

The unique value: **real DAW + natural language + auditory preview + iteration loop +
full editability + auto-checkpointing.** No existing tool combines all of these.

---

## 12. Open Questions

1. **Project reload on accept.** When the Bridge surgically edits the project XML,
   does the LMMS GUI need to reload the file to see changes? If yes, can we trigger
   a reload programmatically? If not, the user clicks File → Revert (acceptable for
   MVP but not ideal).

2. **Render region detection.** How does the Bridge determine which bars were affected
   by the tool calls? Options: (a) parse the tool call arguments for position info,
   (b) diff the temp project XML against the original, (c) always render the full
   project (slower but simpler).

3. **Claude context management.** Large projects may exceed Claude's context window
   when building the system prompt. Strategy: include track names + structure summary,
   not full note data. Only include detailed note data for tracks referenced in the
   prompt.

4. **Instrument selection for new tracks.** When Claude says "add a bass track," how
   does it specify the instrument plugin (TripleOscillator, SF2, ZynAddSubFX)?
   Approach: define a curated set of instrument templates with known-good presets.

5. **BB tracks.** The current design focuses on song tracks. Beat/bassline patterns
   have a different editing model (step sequencer). Support in Phase 2b or later.

---

## 13. File Structure

```
lmms-ai/
├── docs/
│   └── phase2-lmms-gui-integration.md   # This document
├── lmms/                                 # LMMS fork
│   ├── include/gui/ai/
│   │   ├── AIPromptPanel.h
│   │   └── AudioPreviewWidget.h
│   ├── src/gui/ai/
│   │   ├── AIPromptPanel.cpp
│   │   └── AudioPreviewWidget.cpp
│   └── CMakeLists.txt                    # Modified: AI build toggle
├── lmms-mcp-server/
│   └── src/
│       ├── lmms_mcp/
│       │   └── xml/
│       │       ├── writer.py             # Existing surgical functions
│       │       └── parser.py             # Read-only, unchanged
│       └── ai_bridge/
│           ├── server.py                 # WebSocket server
│           ├── renderer.py               # Preview rendering
│           ├── prompt_builder.py         # Claude prompt construction
│           └── surgical.py               # New surgical edit functions
└── projects/
    └── dubstep_drops/
        └── .tmp/
            └── ai_previews/              # Temp copies + rendered audio (gitignored)
```

---

## 14. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Surgical edit corrupts project | Round-trip validation on every edit. Auto-checkpoint means instant rollback. |
| Claude generates bad MCP calls | Apply to temp copy first. User hears the result before anything touches the real project. |
| Render too slow for iteration | Render only affected bars + 4 bar context. Use WAV (fast encode). Reduce sample rate for previews if needed. |
| WebSocket connection drops | Auto-reconnect with exponential backoff. Panel shows clear "offline" state. |
| Claude API rate limits / errors | Graceful error messages. Retry with backoff. Queue prompts if needed. |
| Context window overflow | Summarize project structure instead of including full XML. Only detail tracks referenced in prompt. |
| LMMS fork divergence | Wrap all AI code behind `LMMS_BUILD_AI_INTEGRATION` cmake flag. Keep changes isolated to `src/gui/ai/`. |

---

*This is a living document. Updated as implementation progresses.*
