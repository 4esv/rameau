# Verification report

## Gold gate (dual-derivation agreement)

| metric | value |
|---|---|
| distinct shapes | 845 |
| instances (shape x key) | 5715 |
| instances dropped | 0 |
| chords attempted | 27480 |
| chord disagreements | 0 |
| **chord agreement rate** | **100.000%** |
| total records | 21940 |

## Distribution

- by source: {'curated': 230, 'single': 1440, 'grammar': 20270}
- by cadence: {'PAC': 7902, 'HC': 3903, None: 1458, 'DC': 4460, 'IAC': 3645, 'PC': 572}

## Same progression, four framings (brief example in C major)

- **symbol_to_rn**
  - in:  `key: C major  //  progression: Dm7 G7 Cmaj7`
  - out: `ii7 V7 IM7  //  cadence: PAC`
- **notes_to_rn**
  - in:  `key: C major  //  notes: D4 F4 A4 C5 | G4 B4 D5 F5 | C4 E4 G4 B4`
  - out: `ii7 V7 IM7  //  cadence: PAC`
- **pcset_to_rn**
  - in:  `key: C major  //  pitch classes: [2 5 9 0] | [7 11 2 5] | [0 4 7 11]`
  - out: `ii7 V7 IM7  //  cadence: PAC`
- **key_id**
  - in:  `notes: D4 F4 A4 C5 | G4 B4 D5 F5 | C4 E4 G4 B4`
  - out: `C major`

## Grammar phrases (notes_to_rn, in C major / A minor)

- `A minor`  A4 C5 E5 | D5 F5 A5 | B4 D5 G#5 | E5 G#5 B5 D6 | F5 A5 C6
  -> `i iv viio6 V7 VI` (DC)
- `A minor`  A4 C5 E5 | C5 E5 A5 | D5 F5 B5 | E5 G#5 B5
  -> `i i6 iio6 V` (HC)
- `C major`  C4 E4 G4 | F4 A4 D5 | G4 C5 E5 | G4 B4 D5
  -> `I ii6 I64 V` (HC)
- `A minor`  A4 C5 E5 | A4 C#5 E5 G5 | D5 F5 A5 | E5 G#5 B5
  -> `i V7/iv iv V` (HC)
- `A minor`  A4 C5 E5 | F5 A5 C6 | B4 D5 F5 A5 | E5 G#5 B5 D6 | F5 A5 C6
  -> `i VI ii%7 V7 VI` (DC)
- `C major`  C4 E4 G4 | D4 F4 A4 C5 | D4 F4 B4 | G4 B4 D5 F5 | A4 C5 E5
  -> `I ii7 viio6 V7 vi` (DC)
- `C major`  C4 E4 G4 | E4 G4 B4 | A4 C5 E5 | F4 A4 C5 | G4 B4 D5
  -> `I iii vi IV V` (HC)
- `A minor`  A4 C5 E5 | C5 E5 A5 | D5 F5 A5 | E5 G#5 B5
  -> `i i6 iv V` (HC)
- `A minor`  C5 E5 A5 | D5 F5 A5 | D5 F5 B5 | E5 G#5 B5 | A4 C5 E5
  -> `i6 iv iio6 V i` (PAC)
- `A minor`  A4 C5 E5 | C5 E5 A5 | D5 F5 A5 | B4 D5 G#5 | E5 G#5 B5 D6 | F5 A5 C6
  -> `i i6 iv viio6 V7 VI` (DC)
- `A minor`  A4 C5 E5 | F5 A5 C6 | C5 E5 G5 | D5 F5 A5 | E5 G#5 B5 | F5 A5 C6
  -> `i VI III iv V VI` (DC)
- `A minor`  A4 C5 E5 | F5 A5 C6 | D5 F5 A5 | E5 G#5 B5
  -> `i VI iv V` (HC)
