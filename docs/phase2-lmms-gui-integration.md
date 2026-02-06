# Phase 2: Claude AI Integration in LMMS GUI

## Design Document — Staged Changes with Accept/Reject UI

**Status:** Draft
**Date:** 2026-02-05
**Author:** AI-assisted design

---

## 1. Vision

Embed a Claude AI prompt interface directly into the LMMS GUI, allowing users to
describe musical changes in natural language and preview them as staged diffs —
similar to how Cursor IDE and VS Code Copilot show proposed code changes with
inline accept/reject controls.

The user types "add a 4-bar wobble bass fill at bar 32" and sees ghost notes
appear in the piano roll, a new track header outlined in blue, and automation
curves overlaid in green. They audition the result, then accept or reject each
change individually.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                   LMMS GUI (Qt/C++)                  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │Song Editor│  │Piano Roll│  │ AI Prompt Panel   │  │
│  │  (ghost   │  │ (ghost   │  │ ┌───────────────┐ │  │
│  │  tracks)  │  │  notes)  │  │ │ Chat input    │ │  │
│  └─────┬─────┘  └────┬─────┘  │ │ Change list   │ │  │
│        │              │        │ │ Accept/Reject │ │  │
│        └──────┬───────┘        │ └───────────────┘ │  │
│               │                └────────┬──────────┘  │
│         ┌─────▼──────┐                  │             │
│         │ DiffOverlay │◄─────────────────┘             │
│         │  Manager    │                               │
│         └─────┬──────┘                                │
│               │                                       │
│         ┌─────▼──────┐                                │
│         │  ProjectDiff│  (in-memory staged changes)   │
│         │  Model      │                               │
│         └─────┬──────┘                                │
│               │                                       │
└───────────────┼───────────────────────────────────────┘
                │ IPC (WebSocket / Unix domain socket)
         ┌──────▼───────┐
         │  AI Bridge   │  (Python process)
         │  Server      │
         └──────┬───────┘
                │ MCP / Claude API
         ┌──────▼───────┐
         │  Claude      │
         │  (Anthropic) │
         └──────────────┘
```

### Components

| Component | Language | Role |
|-----------|----------|------|
| **AI Prompt Panel** | C++ / Qt | Chat input widget docked in LMMS |
| **ProjectDiff Model** | C++ | Represents staged changes (not yet applied to the Song) |
| **DiffOverlay Manager** | C++ | Renders ghost notes, ghost tracks, overlay curves in existing views |
| **AI Bridge Server** | Python | Translates natural language → MCP tool calls, returns ProjectDiff |
| **Claude API** | Cloud | Generates musical changes from prompts |

---

## 3. The ProjectDiff Model

This is the core data structure — a set of proposed changes that exist alongside
the live project but are not yet committed to it.

```cpp
// ProjectDiff.h
namespace AI {

struct NoteDiff {
    enum Action { Add, Remove, Modify };
    Action action;
    Note originalNote;  // for Remove/Modify
    Note proposedNote;  // for Add/Modify
};

struct AutomationDiff {
    int clipIndex;
    QString clipName;
    QMap<int, float> originalPoints;  // pos -> value
    QMap<int, float> proposedPoints;
};

struct EffectDiff {
    enum Action { Add, Remove, Modify };
    Action action;
    QString effectName;
    QMap<QString, float> oldParams;
    QMap<QString, float> newParams;
};

struct TrackDiff {
    enum Action { Add, Remove, Modify };
    Action action;
    int trackIndex;              // -1 for new tracks
    QString trackName;
    Track::Type trackType;

    // For new/modified tracks:
    QVector<NoteDiff> noteDiffs;
    QVector<AutomationDiff> automationDiffs;
    QVector<EffectDiff> effectDiffs;

    // Mix changes:
    std::optional<float> oldVolume, newVolume;
    std::optional<float> oldPan, newPan;
    std::optional<bool> oldMuted, newMuted;
};

struct ProjectDiff {
    QString description;          // AI's summary of what changed
    QString prompt;               // Original user prompt
    QVector<TrackDiff> trackDiffs;

    // Tempo/time sig changes
    std::optional<int> oldBpm, newBpm;
    std::optional<QPair<int,int>> oldTimeSig, newTimeSig;

    // Acceptance state per diff item
    QMap<int, bool> accepted;     // trackDiff index -> accepted?
};

} // namespace AI
```

### Design Principles

1. **Non-destructive** — The live Song is never modified until the user explicitly
   accepts a change. The ProjectDiff is a sidecar.
2. **Granular** — Accept/reject at track level, pattern level, or individual note level.
3. **Serializable** — Can be saved as a `.diff.json` sidecar file for interrupted sessions.
4. **Composable** — Multiple AI prompts can stack diffs before final acceptance.

---

## 4. Visual Design — How Changes Appear in the GUI

### 4.1 Song Editor (Arrangement View)

| Change Type | Visual Treatment |
|------------|-----------------|
| **New track** | Track header with dashed blue border, 50% opacity, blue tint overlay on clips. "✓ Accept / ✗ Reject" buttons in header. |
| **Removed track** | Existing track dimmed with red diagonal hatching overlay. |
| **Modified clips** | Clip regions with green/red split — red overlay on removed regions, green on added. |
| **New clips** | Semi-transparent blue clip blocks at proposed positions. |

### 4.2 Piano Roll (Note View)

This is the closest analogue to code editor ghost text:

| Change Type | Visual Treatment |
|------------|-----------------|
| **Added notes** | Semi-transparent green note rectangles ("ghost notes"). Same dimensions as real notes but with 40% opacity and green tint. |
| **Removed notes** | Existing notes shown with red overlay and diagonal strikethrough hatching. |
| **Modified notes** | Original in red (faded), proposed in green (ghost), with a thin connector line showing the transformation. |
| **Pitch shift** | Arrow connecting old and new positions when pitch changes. |
| **Velocity change** | Velocity bar shows both old (red line) and new (green line) levels. |

### 4.3 Automation Editor (Curve View)

| Change Type | Visual Treatment |
|------------|-----------------|
| **New curve** | Green dashed line overlaid on the automation lane. Shaded area between old and new curves. |
| **Modified points** | Original points shown as red hollow circles, proposed as green filled circles. The interpolated curve shown as green dashed line alongside the existing solid line. |
| **Removed points** | Red X markers on points marked for deletion. |

### 4.4 Mixer / Track Headers

| Change Type | Visual Treatment |
|------------|-----------------|
| **Volume change** | Ghost fader at proposed level (translucent green outline). Annotation: "67% → 80%". |
| **Pan change** | Ghost pan knob position indicator. |
| **Effect added** | Ghost effect slot with dashed border in the FX chain. |
| **Effect param change** | Tooltip diff: "Cutoff: 250Hz → 400Hz". |

---

## 5. Interaction Model

### 5.1 Prompt Flow

```
User types in AI Panel: "add a snare fill at bars 15-16 with increasing velocity"
    │
    ▼
AI Bridge receives prompt + current project state
    │
    ▼
Claude generates MCP tool calls (add_note, set_automation, etc.)
    │
    ▼
Tool calls are intercepted — NOT applied to project
Instead, converted to ProjectDiff
    │
    ▼
ProjectDiff sent to LMMS GUI via IPC
    │
    ▼
DiffOverlay Manager renders ghost notes/tracks/curves
    │
    ▼
User enters REVIEW MODE
```

### 5.2 Review Mode

When a ProjectDiff is active, the GUI enters a review state:

1. **Preview playback** — A toggle button ("Preview Changes" / "Original") lets the
   user hear the project *as if* all proposed changes were accepted. Internally,
   the audio engine temporarily merges the diff during playback without modifying
   the Song.

2. **A/B toggle** — Keyboard shortcut (e.g., `Ctrl+Shift+A`) instantly toggles
   between "with changes" and "without changes" playback.

3. **Granular review** — Three levels of acceptance:
   - **All** — "Accept All" / "Reject All" buttons in the AI Panel
   - **Per-track** — Accept/Reject buttons on each ghost track header
   - **Per-element** — Right-click any ghost note, automation point, or effect
     for individual accept/reject context menu

4. **Iterative refinement** — User can type follow-up prompts while in review mode.
   New diffs merge with or replace existing staged changes.

5. **Commit** — Accepting changes triggers surgical XML edits (using the existing
   `surgical_update_*` pattern), then auto-checkpoints via `save_project_version()`.

### 5.3 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Enter` | Submit prompt to AI |
| `Ctrl+Shift+A` | Toggle A/B preview |
| `Ctrl+Shift+Y` | Accept all changes |
| `Ctrl+Shift+N` | Reject all changes |
| `Tab` | Accept current highlighted change |
| `Esc` | Exit review mode (reject pending) |
| `↑/↓` | Navigate between change items |

---

## 6. IPC: LMMS ↔ AI Bridge Communication

### 6.1 Protocol Choice: WebSocket

**Why WebSocket over other options:**

| Option | Pros | Cons |
|--------|------|------|
| **File-based (current MCP)** | Simple, proven | No real-time updates, requires file reload |
| **Unix domain socket** | Fast, no network | Platform-specific |
| **WebSocket** | Bidirectional, streaming, cross-platform | Slight overhead |
| **gRPC** | Strong typing, streaming | Heavy dependency |
| **Shared memory** | Fastest | Complex, no message framing |

WebSocket wins because it supports:
- Bidirectional streaming (AI can stream partial results as they generate)
- Cross-platform (works on Linux, macOS, Windows)
- Simple JSON message protocol
- Qt has `QWebSocket` built in
- Python has `websockets` library (or `aiohttp`)

### 6.2 Message Protocol

```json
// Client (LMMS) → Server (AI Bridge)

// Submit a prompt
{
    "type": "prompt",
    "id": "msg_001",
    "text": "add a wobble bass fill at bars 32-36",
    "context": {
        "project_path": "/path/to/project.mmp",
        "selected_tracks": [5],
        "selected_bars": [32, 36],
        "cursor_position": { "track": 5, "bar": 32, "beat": 0 }
    }
}

// Accept/reject a change
{
    "type": "accept",
    "diff_id": "diff_001",
    "track_diffs": [0, 1],     // indices to accept
    "reject_track_diffs": [2]   // indices to reject
}

// Server (AI Bridge) → Client (LMMS)

// Streaming status
{
    "type": "status",
    "id": "msg_001",
    "text": "Generating bass pattern..."
}

// Proposed diff
{
    "type": "diff",
    "id": "diff_001",
    "prompt_id": "msg_001",
    "description": "Added 4-bar wobble bass fill with automation",
    "track_diffs": [
        {
            "action": "modify",
            "track_index": 5,
            "track_name": "Wobble Bass",
            "note_diffs": [
                { "action": "add", "note": { "key": 36, "pos": 24576, "len": 768, "vol": 90 } },
                ...
            ],
            "automation_diffs": [
                {
                    "clip_name": "Filter Cutoff",
                    "proposed_points": [[32, 200], [33, 800], [34, 200], [35, 1200]]
                }
            ]
        }
    ]
}

// Applied confirmation
{
    "type": "applied",
    "diff_id": "diff_001",
    "checkpoint": "abc1234"
}
```

### 6.3 Context Awareness

The AI Bridge needs project context to generate meaningful changes. Two approaches:

**Option A: Full project snapshot** — Send the entire `.mmp` XML on each prompt.
Simple but heavy (dubstep_drops.mmp is ~50KB, manageable).

**Option B: Incremental state** — AI Bridge maintains a parsed model, LMMS sends
deltas when the user makes changes. More complex but enables real-time awareness.

**Recommendation:** Start with Option A. The project XML is small enough, and the
existing MCP `read_project()` already parses it. Graduate to Option B when
real-time collaboration features arrive.

---

## 7. Implementation Plan

### Phase 2a: Foundation (Weeks 1-4)

**Goal:** Basic prompt → diff → accept flow working end-to-end.

#### 7.1 AI Prompt Panel Widget (C++)

New Qt dock widget in LMMS:

```cpp
// src/gui/ai/AIPromptPanel.h
class AIPromptPanel : public QDockWidget {
    Q_OBJECT
public:
    AIPromptPanel(MainWindow* parent);

private:
    QTextEdit* m_chatHistory;      // Scrollable chat log
    QLineEdit* m_promptInput;      // Text input field
    QPushButton* m_sendButton;
    QListWidget* m_changesList;    // List of proposed changes
    QPushButton* m_acceptAllBtn;
    QPushButton* m_rejectAllBtn;
    QWebSocket* m_socket;          // Connection to AI Bridge

    AI::ProjectDiff m_currentDiff;

signals:
    void diffReceived(const AI::ProjectDiff& diff);
    void diffAccepted(const AI::ProjectDiff& diff);
    void diffRejected();

private slots:
    void onSendClicked();
    void onMessageReceived(const QString& message);
    void onAcceptAll();
    void onRejectAll();
};
```

**Integration point:** Add to `MainWindow` as a toggleable dock widget, similar to
how the Mixer and Controller Rack are managed.

#### 7.2 DiffOverlay Manager (C++)

Manages rendering of ghost elements across all views:

```cpp
// src/gui/ai/DiffOverlayManager.h
class DiffOverlayManager : public QObject {
    Q_OBJECT
public:
    void setDiff(const AI::ProjectDiff& diff);
    void clearDiff();
    bool hasDiff() const;
    bool isPreviewMode() const;

    // Called by view paint methods
    void paintTrackOverlay(QPainter& p, TrackView* tv, int trackIdx);
    void paintNoteOverlay(QPainter& p, PianoRoll* pr, int trackIdx, int clipIdx);
    void paintAutomationOverlay(QPainter& p, AutomationEditor* ae, int trackIdx, int clipIdx);
    void paintMixerOverlay(QPainter& p, MixerChannelView* mv, int trackIdx);

    // Preview playback support
    void mergeNotesForPlayback(MidiClip* clip, int trackIdx, NoteVector& out);
    float mergeAutomationForPlayback(AutomationClip* clip, int trackIdx, TimePos pos);

public slots:
    void togglePreviewMode();
    void acceptTrackDiff(int trackIdx);
    void rejectTrackDiff(int trackIdx);

signals:
    void overlayChanged();
    void previewModeChanged(bool enabled);
};
```

**Integration points:**
- `SongEditor::paintEvent()` — call `paintTrackOverlay()`
- `PianoRoll::paintEvent()` — call `paintNoteOverlay()`
- `AutomationEditor::paintEvent()` — call `paintAutomationOverlay()`
- `MixerChannelView::paintEvent()` — call `paintMixerOverlay()`

#### 7.3 AI Bridge Server (Python)

Extends the existing MCP server architecture:

```python
# src/ai_bridge/server.py
import asyncio
import websockets
from lmms_mcp.xml.parser import parse_project
from lmms_mcp.xml.writer import surgical_update_automation_points

class AIBridgeServer:
    def __init__(self, claude_api_key: str):
        self.claude = anthropic.Anthropic(api_key=claude_api_key)
        self.mcp_tools = load_mcp_tools()

    async def handle_prompt(self, ws, message):
        prompt = message["text"]
        context = message["context"]
        project = parse_project(context["project_path"])

        # Build Claude prompt with project context
        system = build_system_prompt(project, context)

        # Stream Claude's response, intercepting tool calls
        diff = ProjectDiff()
        async for event in self.claude.messages.stream(...):
            if event.type == "tool_use":
                # Convert MCP tool call to diff entry instead of executing
                track_diff = tool_call_to_diff(event.tool_use, project)
                diff.track_diffs.append(track_diff)
                await ws.send(json.dumps({"type": "status", "text": f"Planning: {event.tool_use.name}"}))

        # Send complete diff
        await ws.send(json.dumps({
            "type": "diff",
            "id": make_id(),
            "description": diff.description,
            "track_diffs": serialize_diffs(diff.track_diffs)
        }))

    async def handle_accept(self, ws, message):
        """Apply accepted diffs using surgical XML editing."""
        diff_id = message["diff_id"]
        accepted = message.get("track_diffs", [])

        for idx in accepted:
            track_diff = self.pending_diffs[diff_id].track_diffs[idx]
            apply_surgical_edit(track_diff, project_path)

        # Auto-checkpoint
        save_project_version(project_path, f"AI: {self.pending_diffs[diff_id].description}")
        await ws.send(json.dumps({"type": "applied", "diff_id": diff_id}))
```

#### 7.4 LMMS C++ Changes Summary

| File | Change |
|------|--------|
| `include/ai/ProjectDiff.h` | New — ProjectDiff data model |
| `include/ai/DiffOverlayManager.h` | New — Overlay rendering manager |
| `src/gui/ai/AIPromptPanel.cpp` | New — Chat + review dock widget |
| `src/gui/ai/DiffOverlayManager.cpp` | New — Overlay paint implementations |
| `src/gui/MainWindow.cpp` | Modified — Add AI panel toggle, menu entry |
| `src/gui/editors/PianoRoll.cpp` | Modified — Call overlay paint in `paintEvent()` |
| `src/gui/editors/AutomationEditor.cpp` | Modified — Call overlay paint |
| `src/gui/editors/SongEditor.cpp` | Modified — Call overlay paint for tracks |
| `src/gui/clips/MidiClipView.cpp` | Modified — Ghost note rendering |
| `src/gui/clips/AutomationClipView.cpp` | Modified — Ghost curve rendering |
| `src/gui/MixerChannelView.cpp` | Modified — Ghost fader rendering |
| `CMakeLists.txt` | Modified — Add new source files, WebSocket dep |

### Phase 2b: Polish (Weeks 5-8)

- Streaming token display in chat (typewriter effect)
- Per-note and per-point accept/reject (right-click context menus)
- A/B preview playback toggle
- Keyboard shortcuts
- Change list navigation with arrow keys
- Multiple stacked diffs
- Undo integration (accepted changes go through JournallingObject)

### Phase 2c: Advanced (Weeks 9-12)

- Real-time project state sync (Option B: incremental)
- "Explain this section" — AI reads selected bars and describes them
- Smart context: AI sees cursor position, selected track, loop region
- Template suggestions: "This sounds like it needs a breakdown at bar 24"
- Multi-turn conversations with context memory
- Collaborative mode: multiple AI sessions can stack changes

---

## 8. Preview Playback Architecture

The most technically challenging feature. The audio engine needs to play notes
that don't exist in the Song yet.

### Approach: Temporary Merge

```cpp
// In AudioEngine or a new PlaybackProxy:

class DiffPlaybackProxy {
    // When preview mode is ON, intercept these audio engine calls:

    // For MidiClip::play():
    //   Merge ghost notes from ProjectDiff into the note list
    //   before the audio engine processes them.

    NoteVector getMergedNotes(MidiClip* clip, int trackIdx) {
        NoteVector notes = clip->notes();  // original
        if (m_overlayManager->isPreviewMode()) {
            m_overlayManager->mergeNotesForPlayback(clip, trackIdx, notes);
        }
        return notes;
    }

    // For AutomationClip::valueAt():
    //   Override with proposed values when preview is on.

    float getAutomationValue(AutomationClip* clip, int trackIdx, TimePos pos) {
        if (m_overlayManager->isPreviewMode()) {
            return m_overlayManager->mergeAutomationForPlayback(clip, trackIdx, pos);
        }
        return clip->valueAt(pos);
    }
};
```

**Thread safety:** Uses `AudioEngine::RequestChangesGuard` when toggling preview
mode to safely swap note lists. Ghost notes are stored in the DiffOverlay, not
in the Song model, so no risk of accidental persistence.

---

## 9. Comparison with Cursor/VS Code

| Feature | Cursor/VS Code | LMMS AI |
|---------|---------------|---------|
| Ghost text | Semi-transparent code at cursor | Ghost notes in piano roll |
| Inline diff | Red/green line highlighting | Red/green note overlays |
| Side-by-side | Two-pane editor | A/B toggle playback |
| Accept (Tab) | Inserts code | Commits note to Song XML |
| Reject (Esc) | Removes ghost text | Clears ghost notes |
| Partial accept | Word-by-word | Per-note, per-track |
| Multi-file changes | File tree with diffs | Track list with diffs |
| Working set | File scope selector | Track scope selector |
| Undo after accept | Editor undo | JournallingObject undo |
| Preview | N/A (code is visual) | A/B playback toggle |

The key difference: music changes need **auditory preview**, not just visual.
This is actually an advantage — the user gets more information about a proposed
change by hearing it than a code developer gets from reading a diff.

---

## 10. Security & Performance Considerations

### API Key Management
- Claude API key stored in LMMS config (encrypted at rest)
- Never transmitted to the AI Bridge in plain text
- AI Bridge runs locally, no cloud relay

### Performance
- Ghost note rendering: Minimal overhead — just additional QPainter calls
  with alpha blending
- Preview playback: Negligible — merging a few dozen ghost notes is O(n)
- WebSocket: Local loopback, sub-millisecond latency
- Claude API: 2-10 second response time for complex prompts (stream for
  perceived responsiveness)

### Data Privacy
- Project data sent to Claude API for generation
- Option to use local models (Ollama, llama.cpp) as alternative backend
- AI Bridge abstracts the LLM provider — swap Claude for local model
  with a config change

---

## 11. Open Questions

1. **Conflict resolution** — What happens if the user edits the Song while a diff
   is pending? Options: invalidate diff, auto-rebase, or warn.

2. **Undo granularity** — Should accepting a multi-track diff create one undo
   entry or one per track?

3. **Diff persistence** — Save pending diffs to disk on project save? Or
   treat them as ephemeral?

4. **Plugin parameters** — How deep should AI control go? Only high-level
   (notes, automation) or also synth internals (oscillator waveform,
   filter type)?

5. **Real-time collaboration** — Can two AI sessions propose changes
   simultaneously? How to merge?

6. **Local model support** — Priority for Ollama/llama.cpp backend? Smaller
   models may produce lower-quality musical suggestions.

---

## 12. File Structure

```
lmms/
├── include/ai/
│   ├── ProjectDiff.h              # Diff data model
│   ├── DiffOverlayManager.h       # Overlay rendering
│   ├── AIBridgeClient.h           # WebSocket client
│   └── DiffPlaybackProxy.h        # Preview playback merge
├── src/gui/ai/
│   ├── AIPromptPanel.cpp          # Chat dock widget
│   ├── DiffOverlayManager.cpp     # Paint overlays
│   └── AIBridgeClient.cpp         # IPC client
└── src/core/ai/
    ├── ProjectDiff.cpp            # Diff serialization
    └── DiffPlaybackProxy.cpp      # Audio merge logic

lmms-mcp-server/
└── src/ai_bridge/
    ├── server.py                  # WebSocket server
    ├── diff_builder.py            # Convert tool calls → ProjectDiff
    ├── prompt_builder.py          # Build Claude system prompt
    └── surgical_applicator.py     # Apply accepted diffs to XML
```

---

## 13. Prototype Milestones

| Milestone | Deliverable | Validates |
|-----------|------------|-----------|
| **P1** | AI Panel widget renders in LMMS, text input works | Qt integration, dock widget |
| **P2** | WebSocket handshake between LMMS and AI Bridge | IPC layer |
| **P3** | Hardcoded diff renders ghost notes in piano roll | Overlay rendering |
| **P4** | Claude prompt → diff → ghost notes (end-to-end) | Full pipeline |
| **P5** | Accept button applies diff via surgical XML edit | Commitment flow |
| **P6** | A/B preview playback toggle | Audio preview |
| **P7** | Per-track accept/reject in change list | Granular review |

---

*This document will be updated as implementation progresses.*
