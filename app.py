import os
import random
from flask import Flask, render_template, request, jsonify, session
from flask_session import Session  # import flask-session for server-side sessions
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import cohere
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Cohere client using the API key
cohere_api_key = os.getenv('COHERE_API_KEY')
if not cohere_api_key:
    raise ValueError("Cohere API key not found. Please set COHERE_API_KEY environment variable.")
co = cohere.Client(cohere_api_key)

print("Starting application...")

# Initialize Spotify credentials using client ID and client secret from environment variables
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

if not client_id or not client_secret:
    raise ValueError(
        "Spotify credentials not found. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables."
    )

# Setup Spotify client with client credentials
client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

print("Spotify client initialized.")

# Configure Flask app
app = Flask(__name__)
app.secret_key = '41d2qno13n1n32io2n412no4'  # Replace with a secure random secret key

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'  # Can be 'redis', 'memcached', etc.
app.config['SESSION_FILE_DIR'] = './flask_session/'  # Store session files locally
app.config['SESSION_PERMANENT'] = False  # Session does not persist permanently
app.config['SESSION_USE_SIGNER'] = True  # Sign session data for added security

# Initialize the session
Session(app)

# Mood to attributes mapping for generating music recommendations
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

# Classify mood based on user input using Cohere's generation API
def classify_mood_with_generation(user_input):
    prompt = f"""Given this input: '{user_input}', what are the three best words to describe this mood?
Choose three from the following, separated by commas (ONLY PASTE THE WORDS, NOTHING ELSE): {', '.join(MOOD_TO_ATTRIBUTES.keys())}."""

    try:
        # Generate mood classification with Cohere
        response = co.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=10,
            temperature=0.2,  # Lower temperature for more deterministic responses
        )
        classified_moods = response.generations[0].text.strip().lower().split(", ")

        valid_moods = list(MOOD_TO_ATTRIBUTES.keys())  # Filter for moods we handle
        filtered_moods = [mood for mood in classified_moods if mood in valid_moods]
        if len(filtered_moods) == 3:
            return filtered_moods
        else:
            return random.sample(valid_moods, 3)  # Fallback to random moods if necessary

    except Exception as e:
        print(f"Error in mood classification: {str(e)}")
        return random.sample(valid_moods, 3)  # Fallback to 3 random moods in case of error

# Fetch Spotify recommendations based on the classified moods
def get_spotify_recommendations_for_moods(moods):
    all_recommendations = []

    for mood in moods:
        mood_attributes = MOOD_TO_ATTRIBUTES.get(mood, {'energy': 0.5, 'valence': 0.5, 'genre': 'indie'})

        # Randomize energy and valence values for variety
        randomized_energy = max(0.0, min(1.0, mood_attributes['energy'] + random.uniform(-0.5, 0.5)))
        randomized_valence = max(0.0, min(1.0, mood_attributes['valence'] + random.uniform(-0.5, 0.5)))

        try:
            # Retrieve song recommendations from Spotify based on mood attributes
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

# Route to handle mood-based music recommendations
@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form['mood']
    print(f"Received mood input: {user_input}")

    if user_input == 'random':
        user_input = random.choice(list(MOOD_TO_ATTRIBUTES.keys()))  # Pick a random mood

    if 'history' not in session:
        session['history'] = []
        print("Initialized new session history.")

    # Classify mood using Cohere based on user input
    classified_moods = classify_mood_with_generation(user_input)
    print(f"Classified moods: {classified_moods}")

    # Fetch Spotify recommendations for the classified moods
    songs = get_spotify_recommendations_for_moods(classified_moods)
    print(f"Retrieved {len(songs)} songs.")

    # Extract song names and artists for the quote
    song_info = ', '.join([f"'{song['name']}' by {song['artist']}" for song in songs[:3]])

    # Generate a Yoda-style quote using Cohere
    quote_prompt = f"""As Yoda, create a short quote (max two sentences) reflecting the mood '{user_input}' and the following songs: {song_info}. Do wordplay regarding the first songs generated and start and end with 🎵."""

    try:
        quote_response = co.generate(
            model='command-xlarge-nightly',
            prompt=quote_prompt,
            max_tokens=50,
            temperature=0.7,
            stop_sequences=["--"]
        )
        quote = quote_response.generations[0].text.strip()
        if not quote.startswith('🎵'):
            quote = f"🎵 {quote}"
        if not quote.endswith('🎵'):
            quote = f"{quote} 🎵"
    except Exception as e:
        print(f"Error generating quote: {str(e)}")
        quote = ""

    # Store classified moods, recommendations, and quote in session history
    session['history'].insert(0, {
        'mood': user_input,
        'classified_moods': classified_moods,
        'songs': songs,
        'quote': quote
    })
    session['history'] = session['history'][:10]  # Keep only the latest 10 entries

    session.modified = True
    print(f"Updated session history. Total entries: {len(session['history'])}")

    # Return classified moods, recommendations, and quote as JSON
    return jsonify({
        'mood': user_input,
        'classified_moods': classified_moods,
        'songs': songs,
        'quote': quote
    })

# Route to get the history of mood inputs and song recommendations
@app.route('/history', methods=['GET'])
def get_history():
    history = session.get('history', [])
    print(f"Returning history with {len(history)} entries.")
    return jsonify(history)

# Route to clear the session history
@app.route('/clear_history', methods=['POST'])
def clear_history():
    session['history'] = []
    session.modified = True
    print("History cleared.")
    return jsonify({"message": "History cleared successfully"})

# Render the main page
@app.route('/')
def index():
    print("Serving index page.")
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html')

# Start the Flask server when the script is run
if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=False)
