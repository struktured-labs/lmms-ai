# Soundfonts for LMMS-AI

This directory contains SoundFont (SF2) files for use with the LMMS MCP tools.

## Download

Soundfonts are not committed to git due to their size. Run the download script:

```bash
./download.sh
```

Or install system packages (Ubuntu/Debian):
```bash
sudo apt install fluid-soundfont-gm timgm6mb-soundfont
```

## Available Soundfonts

| File | Size | Description |
|------|------|-------------|
| `FluidR3_GM.sf2` | 142 MB | High-quality General MIDI soundfont with realistic instruments |
| `GeneralUser GS v1.471.sf2` | 30 MB | Efficient GM/GS soundfont, great balance of quality/size |
| `TimGM6mb.sf2` | 5.7 MB | Lightweight GM soundfont for quick loading |
| `HS TR-808 Drums.sf2` | 398 KB | Classic Roland TR-808 drum machine sounds |

## Usage with MCP Tools

```python
# Add a piano track using FluidR3 GM
add_sf2_track(
    path="project.mmp",
    name="Piano",
    sf2_path="assets/soundfonts/FluidR3_GM.sf2",
    bank=0, patch=0,  # Acoustic Grand Piano
    reverb_on=True
)

# Add 808 drums
add_sf2_track(
    path="project.mmp",
    name="808 Drums",
    sf2_path="assets/soundfonts/HS TR-808 Drums.sf2",
    bank=0, patch=0
)
```

## General MIDI Patch Numbers (Bank 0)

Common instruments available in GM soundfonts:

### Piano (0-7)
- 0: Acoustic Grand Piano
- 1: Bright Acoustic Piano
- 4: Electric Piano 1
- 5: Electric Piano 2

### Bass (32-39)
- 32: Acoustic Bass
- 33: Electric Bass (finger)
- 38: Synth Bass 1
- 39: Synth Bass 2

### Strings (40-47)
- 40: Violin
- 48: String Ensemble 1
- 44: Tremolo Strings

### Brass (56-63)
- 56: Trumpet
- 57: Trombone
- 61: Brass Section

### Synth (80-87)
- 80: Lead 1 (square)
- 81: Lead 2 (sawtooth)

Use `list_gm_patches()` tool for complete reference.

## Sources

- [GeneralUser GS](https://schristiancollins.com/generaluser.php) - S. Christian Collins
- [FluidR3 GM](https://member.keymusician.com/member/FluidR3_GM/) - Frank Wen
- [HammerSound TR-808](http://www.hammersound.net/) - Thomas Hammer
