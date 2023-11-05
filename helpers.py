import requests
from bs4 import BeautifulSoup
import re
import json
from googlesearch import search


def get_song_key(song_name: str):
    query = song_name + "site:songbpm.com"
    result = search(query, num_results=1, lang="en")

    result = next(result)

    answer = requests.get(result)

    soup = BeautifulSoup(answer.content, "html.parser")

    # get this class class="mt-1 text-3xl font-semibold text-gray-900"
    data = soup.find("dd", {"class": "mt-1 text-3xl font-semibold text-gray-900"})
    data = data.text

    return data

def get_song_data(song_name: str, result_num: int = 1):
    if result_num > 10:
        raise ValueError("Result number cannot be greater than 10")

    query = song_name + " site:tabs.ultimate-guitar.com"

    result = search(query, num_results=result_num, lang="en")

    for i in result:
        song_url = i

    answer = requests.get(song_url)

    soup = BeautifulSoup(answer.text, "html.parser")

    data = soup.find("div", {"class": "js-store"})

    # Get only the data-content attribute
    data = data["data-content"]

    return json.loads(data)


def extract_chords(text):
    # Extract section headers that are not chords (not in ch tag), without the \n and brackets
    sections = re.findall(r"(?<!\[ch\])(\[[^\]]*\])", text)
    new_sections = [
        section
        for section in sections
        if section not in ["[tab]", "[/tab]", "[ch]", "[/ch]"]
    ]

    final_sections = {}
    start_idx = 0

    for i in range(len(new_sections)):
        section = new_sections[i]
        start_idx = text.find(
            section, start_idx
        )  # Update the starting index based on the last search

        if i < len(new_sections) - 1:
            next_section = new_sections[i + 1]
            end_idx = text.find(next_section, start_idx)
        else:
            end_idx = len(text)

        chords = re.findall(r"\[ch\](.*?)\[/ch\]", text[start_idx:end_idx])

        # If no chords found, use a regex to identify the chords like A, Am, G, C, A#m7, B7sus4, etc, not in ch tags this time.
        if len(chords) == 0:
            # use this regex \b[CDEFGAB](?:#{1,2}|b{1,2})?(?:maj7?|min7?|sus2?)\b/g
            chords = re.findall(
                r"\b[CDEFGAB](?:#{1,2}|b{1,2})?(?:maj7?|min7?|sus2?)\b",
                text[start_idx:end_idx],
            )

        section_name = section.replace("[", "").replace("]", "")

        final_sections[section_name] = chords
        start_idx = end_idx  # Update the starting index for the next iteration

    return final_sections


def get_song_chords(song_name: str):
    got_results = False
    current_try = 1

    while not got_results:
        if current_try > 10:
            print("No results found")
            break

        data = get_song_data(song_name)

        # Extract the song's chord progressions
        progressions = extract_chords(
            data["store"]["page"]["data"]["tab_view"]["wiki_tab"]["content"]
        )

        is_empty_value = False

        # create a list of all values in the dictionary
        values = list(progressions.values())

        if len(values) == 0:
            is_empty_value = True
        else:
            return progressions

        if not is_empty_value:
            got_results = True

        current_try += 1
        print(current_try)

    return None


def replace_chords_with_transposed(
    text, original_progressions, transposed_progressions
):
    """Replace original chords in the song text with transposed chords."""

    # Loop through sections and replace the chords
    for section, chords in original_progressions.items():
        for idx, chord in enumerate(chords):
            # Replace all occurrences of the original chord with the transposed chord in the section
            transposed_chord = transposed_progressions[section][idx]
            text = text.replace(f"[ch]{chord}[/ch]", f"[ch]{transposed_chord}[/ch]")

            # Also handle cases where chords are mentioned without the [ch] tags
            # Note: This might unintentionally replace other words if they match chord names.
            # Ideally, you'd have a more robust way of distinguishing chords from other text.
            text = text.replace(f"\n{chord}", f"\n{transposed_chord}")
            text = text.replace(f" {chord}", f" {transposed_chord}")

    return text

def split_chord(chord):
    """Splits a chord into its root and quality."""
    if chord[-3:] == 'dim':
        return chord[:-3], 'dim'
    if chord[-1] == 'm':
        return chord[:-1], 'm'
    return chord, ''

def transpose_to_easy_key(song_structure):
    """TODO: A WAY TO TRANSPOSE TO EASY CHORDS WITH CAPO"""
    # Define transposition table
    chords = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    easy_keys = {
        'G': ['G', 'Am', 'Bm', 'C', 'D', 'Em', 'F#dim'],
        'C': ['C', 'Dm', 'Em', 'F', 'G', 'Am', 'Bdim']
    }

    # Function to determine number of steps to transpose from chord1 to chord2
    def steps_between_chords(chord1, chord2):
        root1, _ = split_chord(chord1)
        root2, _ = split_chord(chord2)
        index1 = chords.index(root1)
        index2 = chords.index(root2)
        return (index2 - index1) % 12
    
    # Determine best key to transpose to
    best_key = None
    fewest_steps = float('inf')
    capo_position = 0

    for key, key_chords in easy_keys.items():
        total_steps = 0
        for section, section_chords in song_structure.items():
            for chord in section_chords:
                min_steps = min([steps_between_chords(chord, key_chord) for key_chord in key_chords])
                total_steps += min_steps
        if total_steps < fewest_steps:
            best_key = key
            fewest_steps = total_steps

    # Now transpose the song to the best key
    new_song_structure = {}
    for section, section_chords in song_structure.items():
        new_song_structure[section] = []
        for chord in section_chords:
            root, quality = split_chord(chord)
            steps_to_key = steps_between_chords(chord, best_key)
            new_chord_index = (chords.index(root) + steps_to_key) % 12
            new_chord = chords[new_chord_index] + quality
            new_song_structure[section].append(new_chord)

    capo_position = steps_between_chords('C', best_key)

    return capo_position, new_song_structure
