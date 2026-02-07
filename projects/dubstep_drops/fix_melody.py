#!/usr/bin/env python3
"""
Surgical XML editor for dubstep_drops.mmp - adds melody content for bars 48-88.

This script uses raw lxml.etree parsing to surgically add new midiclip and
automationclip elements to specific tracks WITHOUT modifying any existing data.
It follows the CRITICAL design rule: never use the lossy parse->model->write pipeline.
"""

from lxml import etree
import copy
import sys
from pathlib import Path

# ============================================================================
# Constants
# ============================================================================

MMP_PATH = Path("/home/struktured/projects/lmms-ai/projects/dubstep_drops/dubstep_drops.mmp")

# Tick constants
BAR = 768       # ticks per bar
BEAT = 192      # ticks per beat
SIXTEENTH = 48  # ticks per 16th note
THIRTYSECOND = 24  # ticks per 32nd note

# Bar positions (absolute)
BAR_48 = 48 * BAR  # 36864
BAR_56 = 56 * BAR  # 43008
BAR_64 = 64 * BAR  # 49152
BAR_72 = 72 * BAR  # 55296
BAR_80 = 80 * BAR  # 61440
BAR_88 = 88 * BAR  # 67584

# 8 bars in ticks
EIGHT_BARS = 8 * BAR  # 6144

# Echo offset and velocity reduction
ECHO_OFFSET = 96    # half a beat delay
ECHO_VEL_REDUCE = 20
ECHO_VEL_MIN = 25


# ============================================================================
# Helper functions
# ============================================================================

def find_track_by_name(root, name):
    """Find a track element by its name attribute."""
    for track in root.iter("track"):
        if track.get("name") == name:
            return track
    return None


def make_midiclip(name, pos, length, notes):
    """
    Create a midiclip element with the given notes.

    Args:
        name: Clip name string
        pos: Absolute position in ticks
        length: Clip length in ticks
        notes: List of (pos_in_clip, key, length, velocity) tuples

    Returns:
        lxml.etree.Element for the midiclip
    """
    clip = etree.Element("midiclip")
    clip.set("type", "1")
    clip.set("pos", str(pos))
    clip.set("off", "0")
    clip.set("muted", "0")
    clip.set("len", str(length))
    clip.set("name", name)
    clip.set("steps", "16")
    clip.set("autoresize", "1")

    for note_pos, key, note_len, vol in notes:
        note_el = etree.SubElement(clip, "note")
        note_el.set("type", "0")
        note_el.set("pan", "0")
        note_el.set("pos", str(note_pos))
        note_el.set("key", str(key))
        note_el.set("len", str(note_len))
        note_el.set("vol", str(vol))

    return clip


def make_echo_notes(notes):
    """
    Transform notes for echo track: offset by ECHO_OFFSET ticks,
    reduce velocity by ECHO_VEL_REDUCE (minimum ECHO_VEL_MIN).
    """
    echo_notes = []
    for pos, key, length, vol in notes:
        echo_vol = max(ECHO_VEL_MIN, vol - ECHO_VEL_REDUCE)
        echo_notes.append((pos + ECHO_OFFSET, key, length, echo_vol))
    return echo_notes


def make_automationclip(name, pos, length, prog, tens, autoresize, time_points, object_id):
    """
    Create an automationclip element.

    Args:
        name: Clip name
        pos: Absolute position in ticks
        length: Clip length in ticks
        prog: Interpolation type (0=discrete, 1=linear, 2=cubic)
        tens: Tension
        autoresize: "0" or "1"
        time_points: List of (pos_in_clip, value) tuples
        object_id: The object ID to link to

    Returns:
        lxml.etree.Element for the automationclip
    """
    clip = etree.Element("automationclip")
    clip.set("pos", str(pos))
    clip.set("prog", str(prog))
    clip.set("off", "0")
    clip.set("tens", str(tens))
    clip.set("len", str(length))
    clip.set("mute", "0")
    clip.set("name", name)
    clip.set("autoresize", str(autoresize))

    for t_pos, value in time_points:
        time_el = etree.SubElement(clip, "time")
        time_el.set("inTan", "0")
        time_el.set("value", str(value))
        time_el.set("pos", str(t_pos))
        time_el.set("outTan", "0")
        time_el.set("outValue", str(value))
        time_el.set("lockedTan", "0")

    obj_el = etree.SubElement(clip, "object")
    obj_el.set("id", str(object_id))

    return clip


# ============================================================================
# Note data for all clips
# ============================================================================

# --- Main Melody: "nes_soundfont" track ---

CLIP_1_POST_DROP = {
    "name": "Post-Drop Call-Response",
    "pos": BAR_48,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 48: Quick C minor arpeggio burst (8th notes)
        (0, 60, 96, 100),      # C4 beat 1
        (96, 63, 96, 95),      # Eb4 beat 2
        (192, 67, 96, 100),    # G4 beat 3
        (384, 72, 48, 90),     # C5 quick accent beat 3
        (480, 70, 48, 85),     # Bb4
        (576, 67, 96, 90),     # G4

        # Bar 49: Rest first half, then response
        (960, 63, 48, 95),     # Eb4
        (1008, 65, 48, 90),    # F4
        (1056, 67, 96, 100),   # G4
        (1248, 60, 48, 80),    # C4 pickup

        # Bar 50: Syncopated hits
        (1536, 72, 48, 100),   # C5
        (1632, 70, 48, 90),    # Bb4
        (1728, 67, 96, 95),    # G4
        (1920, 65, 48, 85),    # F4
        (2016, 63, 96, 90),    # Eb4

        # Bar 51: Short response
        (2304, 60, 48, 90),    # C4
        (2400, 63, 48, 85),    # Eb4
        (2496, 67, 48, 95),    # G4
        (2640, 72, 48, 100),   # C5 accent

        # Bar 52: Repeat bar 48 variation
        (3072, 67, 96, 100),   # G4
        (3168, 63, 96, 90),    # Eb4
        (3264, 60, 96, 85),    # C4
        (3456, 63, 48, 90),    # Eb4
        (3504, 65, 48, 95),    # F4
        (3552, 67, 48, 100),   # G4

        # Bar 53: Ascending run
        (3840, 60, 48, 90),    # C4
        (3888, 63, 48, 90),    # Eb4
        (3936, 65, 48, 95),    # F4
        (3984, 67, 48, 100),   # G4
        (4128, 70, 96, 95),    # Bb4
        (4320, 72, 48, 90),    # C5

        # Bar 54: Descending with syncopation
        (4608, 72, 48, 100),   # C5
        (4704, 70, 48, 90),    # Bb4
        (4800, 67, 96, 95),    # G4
        (4992, 65, 48, 85),    # F4
        (5088, 63, 96, 90),    # Eb4
        (5280, 60, 48, 80),    # C4

        # Bar 55: Tension builder - repeated note pattern
        (5376, 67, 48, 95),    # G4
        (5424, 67, 48, 100),   # G4
        (5472, 67, 48, 95),    # G4
        (5568, 70, 48, 100),   # Bb4
        (5616, 70, 48, 95),    # Bb4
        (5712, 72, 96, 100),   # C5 held
    ],
}

CLIP_2_BUILD_RISING = {
    "name": "Build Rising",
    "pos": BAR_56,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 56: Simple ascending phrase
        (0, 60, 96, 90),       # C4
        (96, 63, 96, 95),      # Eb4
        (192, 65, 96, 100),    # F4
        (288, 67, 96, 100),    # G4
        (480, 70, 48, 90),     # Bb4
        (576, 72, 96, 95),     # C5

        # Bar 57: Higher variation
        (768, 67, 96, 95),     # G4
        (864, 70, 96, 100),    # Bb4
        (960, 72, 96, 100),    # C5
        (1152, 70, 48, 90),    # Bb4
        (1200, 67, 48, 85),    # G4
        (1296, 65, 48, 90),    # F4
        (1344, 63, 48, 85),    # Eb4

        # Bar 58: Faster 16ths
        (1536, 60, 48, 90),    # C4
        (1584, 63, 48, 90),    # Eb4
        (1632, 65, 48, 95),    # F4
        (1680, 67, 48, 95),    # G4
        (1728, 70, 48, 100),   # Bb4
        (1776, 72, 48, 100),   # C5
        (1824, 70, 48, 95),    # Bb4
        (1872, 67, 48, 90),    # G4
        (1920, 65, 48, 90),    # F4
        (1968, 63, 48, 85),    # Eb4
        (2016, 60, 48, 85),    # C4
        (2064, 63, 48, 90),    # Eb4

        # Bar 59: Ascending with energy
        (2304, 65, 48, 95),    # F4
        (2352, 67, 48, 100),   # G4
        (2400, 70, 48, 100),   # Bb4
        (2448, 72, 48, 100),   # C5
        (2592, 70, 48, 95),    # Bb4
        (2640, 72, 48, 100),   # C5
        (2688, 70, 48, 95),    # Bb4
        (2736, 72, 48, 100),   # C5 stuttered

        # Bar 60: Rapid ascending
        (3072, 60, 48, 85),    # C4
        (3120, 63, 48, 90),    # Eb4
        (3168, 65, 48, 95),    # F4
        (3216, 67, 48, 95),    # G4
        (3264, 70, 48, 100),   # Bb4
        (3312, 72, 48, 100),   # C5
        (3360, 70, 48, 95),    # Bb4
        (3408, 72, 48, 100),   # C5

        # Bar 61: Held high note tension
        (3840, 72, 192, 100),  # C5 held
        (4032, 70, 96, 90),    # Bb4
        (4128, 72, 192, 100),  # C5 held again
        (4416, 70, 48, 90),    # Bb4
        (4464, 72, 48, 100),   # C5

        # Bar 62: Rising intensity
        (4608, 67, 48, 90),    # G4
        (4656, 70, 48, 95),    # Bb4
        (4704, 72, 48, 100),   # C5
        (4752, 70, 48, 95),    # Bb4
        (4800, 72, 48, 100),   # C5
        (4848, 70, 48, 100),   # Bb4
        (4896, 72, 48, 100),   # C5
        (4944, 72, 48, 100),   # C5

        # Bar 63: Final buildup - rapid stutter
        (5376, 72, 24, 100),   # C5 32nd
        (5400, 72, 24, 100),   # C5 32nd
        (5424, 72, 24, 100),   # C5 32nd
        (5448, 72, 24, 100),   # C5 32nd
        (5472, 72, 24, 100),   # C5 32nd
        (5520, 72, 24, 100),   # C5 32nd
        (5568, 72, 24, 100),   # C5 32nd
        (5616, 72, 24, 100),   # C5 32nd
        (5664, 72, 24, 100),   # C5 32nd
        (5712, 72, 24, 100),   # C5 32nd
        (5760, 72, 24, 100),   # C5 32nd
    ],
}

CLIP_3_DROP_SPARSE = {
    "name": "Drop Sparse",
    "pos": BAR_64,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 64-65: SILENCE -- let the bass drop hit

        # Bar 66: Single accent note
        (1536, 72, 48, 70),    # C5 soft accent

        # Bar 67: Nothing

        # Bar 68: Two soft accents
        (3072, 67, 48, 60),    # G4 very soft
        (3264, 72, 48, 65),    # C5 very soft

        # Bar 69-71: SILENCE
    ],
}

CLIP_4_BREAKDOWN = {
    "name": "Breakdown Melody",
    "pos": BAR_72,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 72: Opening phrase - simple and beautiful
        (0, 72, 192, 90),      # C5 half note
        (192, 70, 96, 85),     # Bb4 quarter
        (288, 67, 192, 80),    # G4 half note

        # Bar 73: Response phrase
        (768, 65, 192, 85),    # F4 half note
        (960, 63, 96, 80),     # Eb4 quarter
        (1056, 60, 288, 75),   # C4 dotted half

        # Bar 74: Rising emotion
        (1536, 63, 96, 80),    # Eb4
        (1632, 65, 96, 85),    # F4
        (1728, 67, 288, 90),   # G4 long
        (2016, 70, 96, 85),    # Bb4

        # Bar 75: Climax of the phrase
        (2304, 72, 384, 95),   # C5 whole-ish
        (2688, 70, 96, 85),    # Bb4

        # Bar 76: Repeat opening transposed feel
        (3072, 70, 192, 85),   # Bb4 half
        (3264, 67, 96, 80),    # G4 quarter
        (3360, 65, 192, 80),   # F4 half

        # Bar 77: Descending resolution
        (3840, 67, 192, 85),   # G4
        (4032, 65, 96, 80),    # F4
        (4128, 63, 192, 75),   # Eb4
        (4416, 60, 96, 70),    # C4

        # Bar 78: Final echo phrase
        (4608, 63, 96, 75),    # Eb4
        (4704, 65, 96, 80),    # F4
        (4800, 67, 192, 85),   # G4
        (4992, 72, 96, 80),    # C5
        (5088, 70, 192, 75),   # Bb4

        # Bar 79: Fade into outro
        (5376, 67, 192, 70),   # G4 soft
        (5568, 63, 192, 60),   # Eb4 softer
        (5760, 60, 192, 50),   # C4 softest
    ],
}

CLIP_5_OUTRO = {
    "name": "Outro Farewell",
    "pos": BAR_80,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 80: Final melody statement
        (0, 60, 192, 75),      # C4
        (192, 63, 96, 70),     # Eb4
        (288, 67, 288, 80),    # G4 long
        (672, 72, 96, 75),     # C5

        # Bar 81: Echoing
        (768, 70, 192, 65),    # Bb4
        (960, 67, 288, 60),    # G4 long

        # Bar 82: Sparse notes
        (1536, 63, 192, 55),   # Eb4
        (1824, 60, 192, 50),   # C4

        # Bar 83: Even sparser
        (2304, 67, 288, 45),   # G4 very soft
        (2688, 63, 96, 40),    # Eb4

        # Bar 84: Near silence
        (3072, 60, 384, 35),   # C4 long, very soft

        # Bars 85-87: SILENCE -- fade to nothing
    ],
}

MAIN_MELODY_CLIPS = [
    CLIP_1_POST_DROP,
    CLIP_2_BUILD_RISING,
    CLIP_3_DROP_SPARSE,
    CLIP_4_BREAKDOWN,
    CLIP_5_OUTRO,
]

# --- Retro Zaps clips ---

ZAPS_BUILD = {
    "name": "Zaps Build",
    "pos": BAR_56,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 60: Quick zap burst
        (3072, 60, 3, 120),    # C4
        (3075, 63, 3, 120),    # Eb4
        (3078, 67, 3, 120),    # G4
        (3081, 72, 3, 120),    # C5

        # Bar 61: Another burst
        (3840, 72, 3, 120),    # C5
        (3843, 70, 3, 120),    # Bb4
        (3846, 67, 3, 120),    # G4
        (3849, 63, 3, 120),    # Eb4

        # Bar 62: Rapid alternation
        (4608, 60, 3, 120),
        (4611, 67, 3, 120),
        (4614, 60, 3, 120),
        (4617, 67, 3, 120),
        (4620, 60, 3, 120),
        (4623, 67, 3, 120),
        (4626, 60, 3, 120),
        (4629, 67, 3, 120),

        # Bar 63: Dense ascending run
        (5376, 60, 3, 120),
        (5379, 63, 3, 120),
        (5382, 65, 3, 120),
        (5385, 67, 3, 120),
        (5388, 70, 3, 120),
        (5391, 72, 3, 120),
        (5394, 70, 3, 120),
        (5397, 72, 3, 120),
        (5400, 70, 3, 120),
        (5403, 72, 3, 120),
    ],
}

ZAPS_BREAKDOWN = {
    "name": "Zaps Breakdown",
    "pos": BAR_72,
    "length": EIGHT_BARS,
    "notes": [
        # Bar 72: Gentle descending
        (0, 72, 3, 80),
        (3, 70, 3, 80),
        (6, 67, 3, 80),
        (9, 63, 3, 80),

        # Bar 74: Another gentle burst
        (1536, 63, 3, 80),
        (1539, 67, 3, 80),
        (1542, 70, 3, 80),
        (1545, 72, 3, 80),

        # Bar 76: Final burst
        (3072, 72, 3, 70),
        (3075, 67, 3, 70),
        (3078, 63, 3, 70),
        (3081, 60, 3, 70),
    ],
}

RETRO_ZAPS_CLIPS = [ZAPS_BUILD, ZAPS_BREAKDOWN]

# --- Automation clip for nes_echo_fade track ---

ECHO_VOLUME_AUTOMATION = {
    "name": "Echo Volume Second Half",
    "pos": BAR_48,        # 36864
    "length": 24576,      # 32 bars (bar 48 to bar 80)
    "prog": 2,            # cubic interpolation
    "tens": 1,
    "autoresize": 0,
    "object_id": 4182771,
    "time_points": [
        (0, 5.0),         # bar 48: moderate echo
        (6144, 2.0),      # bar 56: quieter during build
        (12288, 0.5),     # bar 64: very quiet during drop
        (18432, 12.0),    # bar 72: loud echo for breakdown
        (24576, 1.0),     # bar 80: fade out
    ],
}


# ============================================================================
# Main script
# ============================================================================

def main():
    print(f"Reading MMP file: {MMP_PATH}")

    # Parse the raw XML
    with open(MMP_PATH, "rb") as f:
        raw_xml = f.read()

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.fromstring(raw_xml, parser)

    # Track counters for summary
    clips_added = 0
    notes_added = 0
    automation_clips_added = 0

    # ----------------------------------------------------------------
    # 1. Add melody clips to "nes_soundfont" track
    # ----------------------------------------------------------------
    nes_main = find_track_by_name(tree, "nes_soundfont")
    if nes_main is None:
        print("ERROR: Could not find track 'nes_soundfont'")
        sys.exit(1)

    print(f"\nFound track: nes_soundfont")
    for clip_data in MAIN_MELODY_CLIPS:
        clip_el = make_midiclip(
            clip_data["name"],
            clip_data["pos"],
            clip_data["length"],
            clip_data["notes"],
        )
        nes_main.append(clip_el)
        n_notes = len(clip_data["notes"])
        clips_added += 1
        notes_added += n_notes
        print(f"  + Added clip '{clip_data['name']}' at pos {clip_data['pos']} "
              f"(bar {clip_data['pos'] // BAR}) with {n_notes} notes")

    # ----------------------------------------------------------------
    # 2. Add echo clips to "nes_soundfont_echo_fade" track
    # ----------------------------------------------------------------
    nes_echo = find_track_by_name(tree, "nes_soundfont_echo_fade")
    if nes_echo is None:
        print("ERROR: Could not find track 'nes_soundfont_echo_fade'")
        sys.exit(1)

    print(f"\nFound track: nes_soundfont_echo_fade")
    for clip_data in MAIN_MELODY_CLIPS:
        echo_notes = make_echo_notes(clip_data["notes"])
        echo_name = f"{clip_data['name']} (Echo)"
        clip_el = make_midiclip(
            echo_name,
            clip_data["pos"],
            clip_data["length"],
            echo_notes,
        )
        nes_echo.append(clip_el)
        n_notes = len(echo_notes)
        clips_added += 1
        notes_added += n_notes
        print(f"  + Added clip '{echo_name}' at pos {clip_data['pos']} "
              f"(bar {clip_data['pos'] // BAR}) with {n_notes} notes")

    # ----------------------------------------------------------------
    # 3. Add zap clips to "Retro Zaps" track
    # ----------------------------------------------------------------
    retro_zaps = find_track_by_name(tree, "Retro Zaps")
    if retro_zaps is None:
        print("ERROR: Could not find track 'Retro Zaps'")
        sys.exit(1)

    print(f"\nFound track: Retro Zaps")
    for clip_data in RETRO_ZAPS_CLIPS:
        clip_el = make_midiclip(
            clip_data["name"],
            clip_data["pos"],
            clip_data["length"],
            clip_data["notes"],
        )
        retro_zaps.append(clip_el)
        n_notes = len(clip_data["notes"])
        clips_added += 1
        notes_added += n_notes
        print(f"  + Added clip '{clip_data['name']}' at pos {clip_data['pos']} "
              f"(bar {clip_data['pos'] // BAR}) with {n_notes} notes")

    # ----------------------------------------------------------------
    # 4. Add automation clip to "nes_echo_fade" track
    # ----------------------------------------------------------------
    nes_auto = find_track_by_name(tree, "nes_echo_fade")
    if nes_auto is None:
        print("ERROR: Could not find track 'nes_echo_fade'")
        sys.exit(1)

    print(f"\nFound track: nes_echo_fade")
    auto_data = ECHO_VOLUME_AUTOMATION
    auto_clip = make_automationclip(
        auto_data["name"],
        auto_data["pos"],
        auto_data["length"],
        auto_data["prog"],
        auto_data["tens"],
        auto_data["autoresize"],
        auto_data["time_points"],
        auto_data["object_id"],
    )
    nes_auto.append(auto_clip)
    automation_clips_added += 1
    print(f"  + Added automation clip '{auto_data['name']}' at pos {auto_data['pos']} "
          f"(bar {auto_data['pos'] // BAR}), length {auto_data['length']} ticks, "
          f"{len(auto_data['time_points'])} time points, linked to object id={auto_data['object_id']}")

    # ----------------------------------------------------------------
    # 5. Write back the modified XML
    # ----------------------------------------------------------------
    output_xml = etree.tostring(
        tree,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=False,
    )

    with open(MMP_PATH, "wb") as f:
        f.write(output_xml)

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Midiclips added:       {clips_added}")
    print(f"  Notes added:           {notes_added}")
    print(f"  Automation clips added: {automation_clips_added}")
    print(f"  File written:          {MMP_PATH}")
    print(f"{'='*60}")
    print(f"\nDone! Melody content for bars 48-88 has been surgically added.")


if __name__ == "__main__":
    main()
