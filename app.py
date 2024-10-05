import os
import random
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session  # import flask-session for server-side sessions
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import cohere
from dotenv import load_dotenv

#  load environment variables from .env file
load_dotenv()

#  initialize cohere client using the api key
cohere_api_key = os.getenv('COHERE_API_KEY')  #  ensure this environment variable is set
if not cohere_api_key:
    raise ValueError("Cohere API key not found. Please set COHERE_API_KEY environment variable.")
co = cohere.Client(cohere_api_key)

print("Starting application...")

# initialize spotify credentials using client id and client secret from environment variables
client_id = os.getenv('SPOTIFY_CLIENT_ID')  # ensure this environment variable is set
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')  # ensure this environment variable is set

if not client_id or not client_secret:
    raise ValueError(
        "Spotify credentials not found. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")

# setup spotify client with client credentials
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

print("Spotify client initialized.")

# configure flask app
app = Flask(__name__)
app.secret_key = '41d2qno13n1n32io2n412no4'  # replace with a secure random secret key

# configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'  # can be 'redis', 'memcached', etc.
app.config['SESSION_FILE_DIR'] = './flask_session/'  # store session files locally
app.config['SESSION_PERMANENT'] = False  # session does not persist permanently
app.config['SESSION_USE_SIGNER'] = True  # sign session data for added security

# initialize the session
Session(app)

# mood to attributes mapping for generating music recommendations
MOOD_TO_ATTRIBUTES = {
    'happy': {'energy': 0.8, 'valence': 0.9, 'genre': 'pop'},
    'sad': {'energy': 0.2, 'valence': 0.2, 'genre': 'acoustic'},
    'relaxed': {'energy': 0.3, 'valence': 0.7, 'genre': 'chill'},
    'energetic': {'energy': 0.9, 'valence': 0.8, 'genre': 'dance'},
    'mysterious': {'energy': 0.4, 'valence': 0.3, 'genre': 'ambient'},
    'romantic': {'energy': 0.5, 'valence': 0.7, 'genre': 'love'},
    'angry': {'energy': 0.9, 'valence': 0.1, 'genre': 'metal'},
    'excited': {'energy': 0.9, 'valence': 0.9, 'genre': 'edm'},
    'calm': {'energy': 0.2, 'valence': 0.8, 'genre': 'ambient'},
    'frustrated': {'energy': 0.8, 'valence': 0.3, 'genre': 'punk'},
}


# classify mood based on user input using cohere's generation api
def classify_mood_with_generation(user_input):
    prompt = f"""Given this input: '{user_input}', what are the three best words to describe this mood?
Choose three from the following, separated by commas (ONLY PASTE THE WORDS, NOTHING ELSE): {', '.join(MOOD_TO_ATTRIBUTES.keys())}."""

    try:
        # generate mood classification with cohere
        response = co.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=10,
            temperature=0.2,  # lower temperature for more deterministic responses
        )
        classified_moods = response.generations[0].text.strip().lower().split(", ")

        valid_moods = list(MOOD_TO_ATTRIBUTES.keys())  # filter for moods we handle
        filtered_moods = [mood for mood in classified_moods if mood in valid_moods]
        if len(filtered_moods) == 3:
            return filtered_moods
        else:
            return random.sample(valid_moods, 3)  # fallback to random moods if necessary

    except Exception as e:
        print(f"Error in mood classification: {str(e)}")
        return random.sample(valid_moods, 3)  # fallback to 3 random moods in case of error


# fetch spotify recommendations based on the classified moods
def get_spotify_recommendations_for_moods(moods):
    all_recommendations = []

    for mood in moods:
        mood_attributes = MOOD_TO_ATTRIBUTES.get(mood, {'energy': 0.5, 'valence': 0.5, 'genre': 'indie'})

        # randomize energy and valence values for variety
        randomized_energy = max(0.0, min(1.0, mood_attributes['energy'] + random.uniform(-0.5, 0.5)))
        randomized_valence = max(0.0, min(1.0, mood_attributes['valence'] + random.uniform(-0.5, 0.5)))

        try:
            # retrieve song recommendations from spotify based on mood attributes
            results = sp.recommendations(
                seed_genres=[mood_attributes['genre']],
                limit=10,
                target_energy=randomized_energy,
                target_valence=randomized_valence
            )

            recommendations = [{
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'url': track['external_urls']['spotify'],
                'image': track['album']['images'][0]['url'] if track['album'][
                    'images'] else "https://via.placeholder.com/50"
            } for track in results['tracks']]

            all_recommendations.extend(recommendations)

        except Exception as e:
            print(f"Error getting Spotify recommendations: {str(e)}")

    return all_recommendations


# route to handle mood-based music recommendations
@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form['mood']
    print(f"Received mood input: {user_input}")

    if user_input == 'random':
        user_input = random.choice(list(MOOD_TO_ATTRIBUTES.keys()))  # Pick a random mood

    if 'history' not in session:
        session['history'] = []
        print("Initialized new session history.")

    # classify mood using cohere based on user input
    classified_moods = classify_mood_with_generation(user_input)
    print(f"Classified moods: {classified_moods}")

    # fetch spotify recommendations for the classified moods
    songs = get_spotify_recommendations_for_moods(classified_moods)
    print(f"Retrieved {len(songs)} songs.")

    # store classified moods and recommendations in session history
    session['history'].insert(0, {
        'mood': user_input,
        'classified_moods': classified_moods,
        'songs': songs
    })
    session['history'] = session['history'][:10]  # keep only the latest 10 entries

    session.modified = True
    print(f"Updated session history. Total entries: {len(session['history'])}")

    # return classified moods and recommendations as json
    return jsonify({
        'mood': user_input,
        'classified_moods': classified_moods,
        'songs': songs
    })


# route to get the history of mood inputs and song recommendations
@app.route('/history', methods=['GET'])
def get_history():
    history = session.get('history', [])
    print(f"Returning history with {len(history)} entries.")
    return jsonify(history)


# route to clear the session history
@app.route('/clear_history', methods=['POST'])
def clear_history():
    session['history'] = []
    session.modified = True
    print("History cleared.")
    return jsonify({"message": "History cleared successfully"})


# render the main page
@app.route('/')
def index():
    print("Serving index page.")
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html')


# start the flask server when the script is run
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=False)
