# LMMS AI Project - State of Affairs

## LMMS Fork

This project uses a **custom LMMS fork** (version 1.3.0-alpha) for tight AI integration.

**Fork Location:** `/home/struktured/projects/lmms-ai/lmms/`
**Purpose:** Enable bidirectional compatibility between LMMS GUI and MCP tools
**Modifications:** Format updates, API enhancements, and integration features for AI-driven music production

**Key Changes:**
- Support for MCP-driven project manipulation
- Enhanced XML format compatibility (midiclip vs pattern elements)
- Real-time updates for AI collaboration (future: Phase 2)

**Philosophy:** Minimal changes to core LMMS, but improve schema and APIs for better agent interaction.

## Project: Dubstep Drops

**Status:** ✓ GUI round-trip compatibility FIXED! Ready for production use.
**Location:** `projects/dubstep_drops/dubstep_drops.mmp`
**Latest Commits:**
- a535491 (lmms-mcp-server) - Fix LMMS 1.3.0-alpha format compatibility: midiclip and automationclip
- f602ab1 (dubstep project) - Fixed kick volume to 67% and re-applied bass amplitude envelope
- ac6c405 (main) - Add SoundCloud MCP server as git submodule
- Tagged: gui-roundtrip-fix-v1.0

### Track Details
- **Length:** 48 bars
- **BPM:** 140
- **Time Signature:** 4/4

### Tracks
1. **Kick** - Volume 67%, distorted kick sample
2. **Hi-Hat** - Closed hi-hat pattern
3. **Snare** - Nasty snare sample
4. **Splash** - Crash cymbal at 60%
5. **Low Crash** - Secondary crash at 60%
6. **Wobble Bass** - Triple oscillator with:
   - Moog filter (cutoff 250Hz)
   - Pitch automation (bars 16-48, drops from 0 to -24 semitones)
   - Delay effect with automation ramp (bars 32-48)
   - Amplitude envelope: 20ms attack, amount=1, sustain=1 (prevents clipping)
   - Waveshaper and compressor for grit
7. **Bass Pitch Drop** - Automation track controlling bass pitch
8. **Delay Ramp** - Automation track controlling delay wet mix
9. **Retro Zaps** - SF2 track (NES soundfont patch 112 "Tinkle Bell")
   - Chromatic oscillation pattern at bars 40-48
   - XXXX.... rhythm (4 notes on, 4 gaps off)
   - Volume 60%

### ✓ RESOLVED: Format Version Mismatch (2026-01-08)

**Root Cause Identified:**
- LMMS 1.2.0 uses `<pattern>` and `<automationpattern>` elements
- LMMS 1.3.0-alpha uses `<midiclip>` and `<automationclip>` instead
- MCP writer was generating 1.2.0 format, but our fork runs 1.3.0-alpha
- **Result:** GUI didn't recognize old elements and stripped them on save

**Fix Applied (commit a535491):**
Updated `/home/struktured/projects/lmms-ai/lmms-mcp-server/src/lmms_mcp/xml/`:
1. **writer.py**: Generate `<midiclip>` and `<automationclip>` elements with required attributes
   - Added `steps="16"`, `off="0"`, `autoresize="1"` for midiclip
   - Added `type="0"` for note elements
   - Added `off="0"`, `autoresize="1"` for automationclip
2. **parser.py**: Support both old and new formats for backward compatibility

**Verification (Round-Trip Test):**
- MCP write → GUI save → MCP read preserves 100% of data:
  - ✓ 9 tracks
  - ✓ 7 patterns
  - ✓ 857 notes
  - ✓ 3 automation clips
- **GUI save is now safe and reliable!**

### MCP Server Status
- Branch: main
- Status: 5 commits ahead of origin/main
- Working tree: clean
- Latest commit: a535491 - Fix LMMS 1.3.0-alpha format compatibility: midiclip and automationclip
- Tagged: gui-roundtrip-fix-v1.0
- Action needed: Push commits to origin

### Git Version History (Recent)
- f602ab1 - Fixed kick volume to 67% and re-applied bass amplitude envelope
- 8a0323b - Fixed Retro Zaps with XXXX.... rhythm pattern (4 on, 4 off), volume at 60%
- ccb42e9 - Added chromatic oscillation to Retro Zaps track (512 notes, 16th speed)
- c8b3ade - Fixed pitch automation: increased pitchrange from 1 to 24 semitones
- (and more - see `list_project_versions()` for full history)

### Next Steps
- **TODO:** Consider uploading to SoundCloud
  - Export final render to appropriate format (MP3/FLAC)
  - Create cover art
  - Add metadata (title, description, tags)
  - Consider licensing/creative commons options

### Project Structure
```
lmms-ai/
├── CLAUDE.md                           # This file
├── docs/
│   └── phase2-lmms-gui-integration.md  # Future GUI integration design
├── lmms-mcp-server/                    # MCP server for LMMS control
│   └── src/lmms_mcp/
│       ├── tools/                      # MCP tool implementations
│       ├── xml/                        # Project parser/writer
│       └── models/                     # Data models
└── projects/
    └── dubstep_drops/
        ├── dubstep_drops.mmp           # Main project file
        ├── dubstep_drops.flac          # Latest full render
        └── soundfonts/
            ├── nes_soundfont.sf2       # NES-style sounds
            └── gbfont.sf2              # Game Boy sounds
```

### Rendering
- Full track: `mcp__lmms-mcp__render(path, play=true)`
- Segments: Use `start_bar` and `end_bar` parameters
- Latest render: `/home/struktured/projects/lmms-ai/projects/dubstep_drops/dubstep_drops.flac`

### Workflow Notes
1. ✓ **GUI save is now safe!** MCP tools and LMMS GUI can be used interchangeably
2. Always commit versions before major changes using `save_project_version()`
3. Restore corrupted files with `restore_project_version(version_hash)`
4. Use git tags for milestones via `tag_project_milestone()`

### Known Issues
1. **Bass Frequency Discrepancy** (observed 2026-01-08)
   - GUI playback: Bass sounds lower frequency than expected
   - Render output: Bass sounds correct
   - Possible causes: Real-time playback optimizations, pitch automation processing differences
   - Status: To investigate

---
*Last updated: 2026-01-08*
*Next session: Push commits, investigate bass frequency issue, consider SoundCloud upload*
