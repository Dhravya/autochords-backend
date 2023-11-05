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


def get_user_chords(song_name: str, recording: bytes):
    """This is the main function.
    It accepts song_name and sample recording as an input.
    Then, it extracts the chords of the song, tranposes it
    to the recording's key and returns the updated chords with lyrics.
    """

    progressions = get_song_chords(song_name)

    y, sr = librosa.load("recording.wav")
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    unebarque_fsharp_maj = Tonal_Fragment(y_harmonic, sr, tend=22)

    song_key = progressions[list(progressions.keys())[0]][0]
    transposed_chords = transpose_progressions(
        progressions, song_key, unebarque_fsharp_maj.get_max_key()
    )

    song_data = get_song_data(song_name)
    original_text = song_data["store"]["page"]["data"]["tab_view"]["wiki_tab"][
        "content"
    ]

    # Replace the original chords with the transposed chords
    updated_text = replace_chords_with_transposed(
        original_text, progressions, transposed_chords
    )

    return updated_text


@app.get("/get_chords")
async def get_chords(song_name: str = Query(...), username: str = Query(...)):
    # Ensure the uploaded file is not empty
    key = None

    cursor.execute(f"SELECT user_key FROM user WHERE email='{username}'")

    if not cursor.rowcount == 0:
        key = cursor.fetchone()[0]

    song = get_song_data(song_name)

    original_chords = song["store"]["page"]["data"]["tab_view"]["wiki_tab"]["content"]

    final_chords = original_chords

    progressions = extract_chords(original_chords)

    original_key = progressions[list(progressions.keys())[0]][0]

    with open("data.json", "w") as f:
        import json
        json.dump(song, f, indent=2)

    capo_position = 0
    if 'capo' in song["store"]["page"]["data"]["tab_view"]["meta"]:
        capo_position = song["store"]["page"]["data"]["tab_view"]["meta"]["capo"]

    song_name = song["store"]["page"]["data"]["tab_view"]["versions"][0]['song_name']
    artist_name = song["store"]["page"]["data"]["tab_view"]["versions"][0]['artist_name']

    # https://tombatossals.github.io/react-chords/media/guitar/chords/Ab/minor/1.svg
    # Get the URL of all the chord images
    # IF the chord ends with m, then it is a minor chord. So, remove the m from the chord name and add minor to the URL
    # Otherwise, add major to the URL
    # it can also be sus, and anhy other signature

    song_images = []

    for section, chords in progressions.items():
        for chord in chords:
            chord_name = chord.replace("m", "").replace("sus", "").replace("add", "")
            chord_type = "minor" if "m" in chord else "major"
            chord_url = f"https://tombatossals.github.io/react-chords/media/guitar/chords/{chord_name}/{chord_type}/1.svg"
            
            object = {
                "name": chord,
                "url": chord_url
            }   

            song_images.append(object)

    if key:
        transposed_chords = transpose_progressions(
            progressions, progressions[list(progressions.keys())[0]][0], key
        )

        updated_chords = replace_chords_with_transposed(
            original_chords, progressions, transposed_chords
        )

        final_chords = updated_chords

    
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
        song_name + " site:tabs.ultimate-guitar.com", num_results=5, lang="en"
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

    y, sr = librosa.load("recording.wav")
    y_harmonic, y_percussive = librosa.effects.hpss(y)
    unebarque_fsharp_maj = Tonal_Fragment(y_harmonic, sr, tend=22)

    print(user_email)

    cursor.execute(
        f"INSERT INTO user (email, user_key) VALUES ('{user_email}', '{unebarque_fsharp_maj.get_max_key()}')"
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


if __name__ == "__main__":
    # song_name = input("Enter song name: ")

    # recording = record_audio()

    # song = get_user_chords(song_name, 'recording')

    # print(song)

    import uvicorn

    uvicorn.run(app)
