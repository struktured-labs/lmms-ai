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

**Status:** ✓ GUI round-trip compatibility FULLY RESOLVED! Ready for production use.
**Location:** `projects/dubstep_drops/dubstep_drops.mmp`
**Latest Commits:**
- 36fa490 (lmms-mcp-server) - Fix version attribute to prevent LMMS upgrade corruption
- 5e9c6ab (dubstep project) - Fix version attribute: set to 31 to prevent LMMS upgrade corruption
- a535491 (lmms-mcp-server) - Fix LMMS 1.3.0-alpha format compatibility: midiclip and automationclip
- f602ab1 (dubstep project) - Fixed kick volume to 67% and re-applied bass amplitude envelope
- Tagged: version-fix-v1.1, gui-roundtrip-fix-v1.0

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
- Status: 6 commits ahead of origin/main (includes version fix)
- Working tree: clean
- Latest commit: 36fa490 - Fix version attribute to prevent LMMS upgrade corruption
- Tagged: version-fix-v1.1, gui-roundtrip-fix-v1.0
- **Action needed: Restart MCP server to load new code, then push commits to origin**

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

### ✓ RESOLVED: Version Attribute Pitch Corruption (2026-01-10)

**Problem:**
- Bass and tracks sounded octave higher after LMMS GUI loaded MCP-written projects
- Originally thought to be GUI playback vs render discrepancy
- Actually caused by LMMS running upgrade methods on every load

**Root Cause Identified:**
- MCP writer had uncommitted code setting `version="31"`
- But MCP server was running cached bytecode that wrote `version="1.0"`
- LMMS 1.3.0-alpha has 31 upgrade methods: `if (m_fileVersion < 31) { upgrade(); }`
- Upgrade #20 (`upgrade_extendedNoteRange()`) adds +12 semitones to all notes
- **Result:** Every GUI load shifted pitch up by one octave

**Fix Applied (commit 36fa490):**
Updated `/home/struktured/projects/lmms-ai/lmms-mcp-server/src/lmms_mcp/xml/writer.py`:
1. `create_xml()`: Set `version="31"` instead of `"1.0"` (line 60)
2. `update_xml()`: Force `version="31"` when modifying projects (line 169)

**Why version="31":**
- LMMS has exactly 31 upgrade methods in `UPGRADE_METHODS` array (DataFile.cpp line 73)
- Setting version="31" means "already at latest format, skip all upgrades"
- GUI will preserve `version="31"` when saving (it reads and maintains the version)

**Verification:**
- ✓ All MCP-written files now have `version="31"`
- ✓ LMMS GUI loads projects with correct pitch
- ✓ GUI save preserves `version="31"` (doesn't revert to "1.0")
- ✓ Multiple round-trips preserve pitch perfectly

**Project Files Updated:**
- Committed changes to lmms-mcp-server (commit 36fa490)
- Updated dubstep_drops.mmp to `version="31"` (commit 5e9c6ab)

### Known Issues
None currently!

---
*Last updated: 2026-01-10*
*Next session: Push commits to origin, consider SoundCloud upload*
