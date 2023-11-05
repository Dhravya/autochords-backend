import re

key_list = [
    ("A",),
    ("A#", "Bb"),
    ("B",),
    ("C",),
    ("C#", "Db"),
    ("D",),
    ("D#", "Eb"),
    ("E",),
    ("F",),
    ("F#", "Gb"),
    ("G",),
    ("G#", "Ab"),
    ("Am",),
    ("A#m", "Bbm"),
    ("Bm",),
    ("Cm",),
    ("C#m", "Dbm"),
    ("Dm",),
    ("D#m", "Ebm"),
    ("Em",),
    ("Fm",),
    ("F#m", "Gbm"),
    ("Gm",),
    ("G#m", "Abm"),
]

sharp_flat = ["#", "b"]
sharp_flat_preferences = {
    "A": "#",
    "A#": "b",
    "Bb": "b",
    "B": "#",
    "C": "b",
    "C#": "b",
    "Db": "b",
    "D": "#",
    "D#": "b",
    "Eb": "b",
    "E": "#",
    "F": "b",
    "F#": "#",
    "Gb": "#",
    "G": "#",
    "G#": "b",
    "Ab": "b",
    "Am": "b",
    "A#m": "b",
    "Bbm": "b",
    "Bm": "#",
    "Cm": "b",
    "C#m": "b",
    "Dbm": "b",
    "Dm": "#",
    "D#m": "b",
    "Ebm": "b",
    "Em": "#",
    "Fm": "b",
    "F#m": "#",
    "Gbm": "#",
    "Gm": "#",
    "G#m": "b",
    "Abm": "b",
}

key_regex = re.compile(r"[ABCDEFG][#b]?")


def get_index_from_key(source_key):
    source_key = source_key.replace("M", "")
    for key_names in key_list:
        if source_key in key_names:
            return key_list.index(key_names)
    raise Exception("Invalid key: %s" % source_key)


def get_key_from_index(index, to_key):
    key_names = key_list[index % len(key_list)]
    if len(key_names) > 1:
        sharp_or_flat = sharp_flat.index(sharp_flat_preferences[to_key])
        return key_names[sharp_or_flat]
    return key_names[0]


def get_transponation_steps(source_key, target_key):
    """Gets the number of half tones to transpose"""
    root_source = key_regex.match(source_key).group()
    root_target = key_regex.match(target_key).group()

    source_index = get_index_from_key(root_source)
    target_index = get_index_from_key(root_target)
    return target_index - source_index

def normalise_chords(progressions):
    """
    normalises chords to their most common form using regex
    like Em7 to Em
    Cadd9 to C
    DSus4 to D

    for 7th chords, add chords, sus chords, etc
    """

    final_sections = {}

    # Define a list of regex patterns to search for and their replacements
    patterns = [
        (r'(?i)maj7', 'M'),  # major 7th chord e.g., CMaj7 to CM
        (r'(?i)7', ''),  # 7th chord e.g., G7 to G
        (r'(?i)add\d+', ''),  # add chords e.g., Cadd9 to C
        (r'(?i)sus\d+', ''),  # sus chords e.g., DSus4 to D
        (r'(?i)dim\d*', 'dim'),  # diminished chords e.g., Bdim7 to Bdim
        (r'(?i)aug\d*', 'aug'),  # augmented chords e.g., Gaug9 to Gaug
        (r'(?i)6', ''),  # 6th chords e.g., A6 to A
        (r'(?i)9', ''),  # 9th chords e.g., E9 to E
        (r'(?i)11', ''),  # 11th chords e.g., F11 to F
        (r'(?i)13', ''),  # 13th chords e.g., G13 to G
    ]

    # if it is lke  D/F#, then remove the /F#

    for section, chords in progressions.items():
        normalized_chords = []

        for chord in chords:
            for pattern, replacement in patterns:
                chord = re.sub(pattern, replacement, chord)
                chord = chord.split("/")[0]
            normalized_chords.append(chord)

        final_sections[section] = normalized_chords

    return final_sections


def transpose_progressions(progressions, from_key, to_key):
    chords = normalise_chords(progressions)
    direction = get_transponation_steps(from_key, to_key)
    transposed_progressions = {}
    for section, chords in chords.items():
        transposed_chords = [transpose(chord, direction, to_key) for chord in chords]
        transposed_progressions[section] = transposed_chords
    return transposed_progressions


def transpose(source_chord, direction, to_key):
    source_index = get_index_from_key(source_chord)
    return get_key_from_index(source_index + direction, to_key)

