import librosa
from key_finder import Tonal_Fragment
from helpers import get_song_chords, get_song_data, replace_chords_with_transposed
from transpose import transpose_progressions
from fastapi import FastAPI, UploadFile, Query
from fastapi.responses import JSONResponse
import pymysql
from dotenv import load_dotenv
from os import environ as env
from helpers import search
from helpers import extract_chords
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()
connection = pymysql.connect(
    host=env.get("MYSQL_HOST"),
    user=env.get("MYSQL_USER"),
    password=env.get("MYSQL_PASSWORD"),
    db=env.get("MYSQL_DATABASE"),
    port=int(env.get("MYSQL_PORT")),
)

cursor = connection.cursor()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "https://autochords.co"],
    allow_credentials=False
)


def split_chord(chord):
    # Define a list of base chords, sorted by length in descending order so that chords with the longer names are matched first
    BASE_CHORDS = sorted(
        ["C", "Csharp", "D", "Eb", "E", "F", "Fsharp", "G", "Gsharp", "Ab", "A", "B", "Bb"],
        key=len,
        reverse=True
    )

    # Handle the slash chords by taking only the part before the slash
    chord = chord.split('/')[0]

    # Replace '#' with 'sharp' in the chord name
    chord = chord.replace('#', 'sharp')

    # Find the base chord and the chord type
    base_chord = None
    chord_type = 'major'

    # Loop through each base chord to find the base chord in the input chord
    for base in BASE_CHORDS:
        if chord.startswith(base):
            base_chord = base
            # Anything after the base chord is considered the chord type
            chord_type = chord[len(base):]
            break

    # Assign chord type based on the suffix
    if chord_type in ['m', 'min']:
        chord_type = 'minor'
    elif chord_type in ['', 'maj', 'M']:
        chord_type = 'major'
    # Other chord types like diminished, augmented, etc., could be added here

    return base_chord, chord_type

@app.get("/get_chords")
async def get_chords(song_name: str = Query(...), username: str = Query(...)):
    # Ensure the uploaded file is not empty
    key = None

    cursor.execute(f"SELECT user_key FROM user WHERE email='{username}'")

    if not cursor.rowcount == 0:
        key = cursor.fetchone()[0]

    song_name_number = song_name.split("-")[-1]
    song = get_song_data(song_name, song_name_number)


    if song is None:
        return JSONResponse(
            content={"error": "Song not found. Please try again with a different song."},
            status_code=400,
        )

    original_chords = song["store"]["page"]["data"]["tab_view"]["wiki_tab"]["content"]
   

    final_chords = original_chords

    progressions = extract_chords(original_chords)

    if len(progressions.keys()) == 0:
        return JSONResponse(
            content={"error": "Song not found. Please try again with a different song."},
            status_code=400,
        )

    original_key = None


    for section, chords in progressions.items():
        if len(chords) > 0:
            original_key = chords[0]
            break
 
    capo_position = 0
    if 'capo' in song["store"]["page"]["data"]["tab_view"]["meta"]:
        capo_position = song["store"]["page"]["data"]["tab_view"]["meta"]["capo"]

    try:
        song_name = song["store"]["page"]["data"]["tab_view"]["versions"][0]['song_name']
        artist_name = song["store"]["page"]["data"]["tab_view"]["versions"][0]['artist_name']
    except IndexError:
        song_name = song["store"]["page"]["data"]["tab"]["song_name"]
        artist_name = song["store"]["page"]["data"]["tab"]["artist_name"]

    # https://tombatossals.github.io/react-chords/media/guitar/chords/Ab/minor/1.svg
    # Get the URL of all the chord images
    # IF the chord ends with m, then it is a minor chord. So, remove the m from the chord name and add minor to the URL
    # Otherwise, add major to the URL
    # it can also be sus, and anhy other signature

    song_images = []


    if key:
        transposed_chords = transpose_progressions(
            progressions, original_key, key
        )

        updated_chords = replace_chords_with_transposed(
            original_chords, progressions, transposed_chords
        )

        final_chords = updated_chords


    progressions = extract_chords(final_chords)
    for section, chords in progressions.items():
        for chord in chords:


            chord_name, chord_type = split_chord(chord)
            
            chord_url = f"https://tombatossals.github.io/react-chords/media/guitar/chords/{chord_name}/{chord_type}/1.svg"
            
            object = {
                "name": chord,
                "url": chord_url
            }   

            song_images.append(object)

    
    # Get the unique values of song_images list
    song_images = [i for n, i in enumerate(song_images) if i not in song_images[n + 1:]]

    return JSONResponse(
        content={
            "chords": final_chords,
            "original_key": original_key,
            "transposed_key": key,
            "capo_position": capo_position,
            "song_name": song_name,
            "artist_name": artist_name,
            "guitar_chord_diagrams": song_images,
            "ukulele_chord_diagrams": [
                {
                    "name": chord["name"],
                    "url": chord["url"].replace("guitar", "ukulele", 1),
                }
                for chord in song_images
            ]
        },
        status_code=200,
    )


@app.get("/search_results")
async def search_results(song_name: str = Query(...)):
    results = search(
        song_name
    )

    results = list(results)

    new_results = []

    for i, result in enumerate(results):
        result = result.replace("https://tabs.ultimate-guitar.com/tab/", "")
        result = result.split("/")
        new_results.append(
            {
                "index": i,
                "artist": result[0],
                "song": result[1].replace("-", " ").title(),
                "url": results[i].replace("https://tabs.ultimate-guitar.com/tab/", ""),
                "id": result[1].split("-")[-1],
            }
        )

    return JSONResponse(content={"results": new_results}, status_code=200)


@app.post("/user_recording")
async def upload_song(file: UploadFile = UploadFile(...), user_email: str = Query(...)):
    # Ensure the uploaded file is not empty
    if not file.filename:
        return JSONResponse(content={"error": "No file provided"}, status_code=400)

    # Ensure the uploaded file is a valid audio file
    if not file.filename.endswith(".mp3") and not file.filename.endswith(".wav"):
        return JSONResponse(
            content={"error": "Only mp3 files are supported"}, status_code=400
        )
    
    with open("recording.wav", "wb") as buffer:
        buffer.write(file.file.read())

    y, sr = librosa.load('recording.wav')
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    unebarque_fsharp_maj = Tonal_Fragment(y_harmonic, sr, tend=22)


    cursor.execute(
        f"SELECT user_key FROM user WHERE email='{user_email}'"
    )
    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            f"INSERT INTO user (email, user_key) VALUES ('{user_email}', '{unebarque_fsharp_maj.get_max_key()}')"
        )
    else:
        cursor.execute(
            f"UPDATE user SET user_key='{unebarque_fsharp_maj.get_max_key()}' WHERE email='{user_email}'"
        )

    connection.commit()

    return JSONResponse(
        content={"key": unebarque_fsharp_maj.get_max_key()}, status_code=200
    )


@app.get("/get_user_key")
async def get_user_key(user_email: str):
    cursor.execute(f"SELECT user_key FROM user WHERE email='{user_email}'")

    if cursor.rowcount == 0:
        return JSONResponse(content={"error": "User not found"}, status_code=400)

    return JSONResponse(content={"key": cursor.fetchone()[0]}, status_code=200)


@app.get("/save_song")
async def save_song(song_url: str, user_email: str):
    cursor.execute(f"SELECT user_key FROM user WHERE email='{user_email}'")

    if cursor.rowcount == 0:
        return JSONResponse(content={"error": "User not found"}, status_code=400)

    user_key = cursor.fetchone()[0]

    song_name = song_url.split("/")[-1].split("-")[:-1]
    song_name = "-".join(song_name)

    cursor.execute(
        f"SELECT * FROM songs WHERE song_name='{song_name}' AND email='{user_email}'"
    )

    if cursor.rowcount == 0:
        cursor.execute(
            f"INSERT INTO songs (song_name, song_url, email) VALUES ('{song_name}', '{song_url}', '{user_email}')"
        )
    else:
        cursor.execute(
            f"UPDATE songs SET song_url='{song_url}' WHERE song_name='{song_name}' AND email='{user_email}'"
        )

    connection.commit()

    return JSONResponse(content={"message": "Song saved successfully"}, status_code=200)

@app.get("/get_saved_songs")
async def get_saved_songs(user_email: str):
    cursor.execute(f"SELECT * FROM songs WHERE email='{user_email}'")

    if cursor.rowcount == 0:
        return JSONResponse(content={"error": "User not found"}, status_code=400)

    songs = cursor.fetchall()

    songs = [
        {
            "song_name": song[0],
            "song_url": song[1],
            "email": song[2]
        } for song in songs
    ]

    return JSONResponse(content={"songs": songs}, status_code=200)

if __name__ == "__main__":
    # song_name = input("Enter song name: ")

    # recording = record_audio()

    # song = get_user_chords(song_name, 'recording')

    import uvicorn

    uvicorn.run(app, host="0.0.0.0")
