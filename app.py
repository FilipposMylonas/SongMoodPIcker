import os
from flask import Flask, render_template, request, jsonify, session
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import cohere
from dotenv import load_dotenv
from difflib import get_close_matches

load_dotenv()

# Initialize Cohere client
cohere_api_key = os.getenv('COHERE_API_KEY')  # Replace with your real API key environment variable
co = cohere.Client(cohere_api_key)

print("Starting application...")

# Set environment variables
os.environ['SPOTIFY_CLIENT_ID'] = 'your_spotify_client_id'
os.environ['SPOTIFY_CLIENT_SECRET'] = 'your_spotify_client_secret'

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Set this to a random secret string

# Spotify setup
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

if not client_id or not client_secret:
    raise ValueError("Spotify credentials not found. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")

client_credentials_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

print("Spotify client initialized.")

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

# Function to classify mood using Cohere's generation API
def classify_mood_with_generation(user_input):
    prompt = f"""How would you classify this input: '{user_input}'? 
    Choose one from the following and only answer with that word: happy, sad, relaxed, energetic, mysterious, romantic, angry, joyful, melancholic, hopeful, 
    anxious, nostalgic, determined, lonely, excited, calm, inspired, frustrated, motivated, confident, peaceful, heartbroken, 
    angsty, playful, curious, grateful, reflective, dreamy, euphoric, serene, restless, indifferent, rebellious, adventurous, 
    gloomy, empowered, nervous, tranquil, surprised, bored, disappointed, satisfied, jealous, content, bitter, optimistic, 
    fearful, shy, tired, brave, lazy, elated, hyper, depressed."""

    try:
        response = co.generate(
            model='command-r-plus-08-2024',
            prompt=prompt,
            max_tokens=10,
            temperature=0.2,  # Lower temperature for more deterministic responses
        )
        classified_mood = response.generations[0].text.strip().lower()

        valid_moods = list(MOOD_TO_ATTRIBUTES.keys())  # Only keep moods we handle
        if classified_mood in valid_moods:
            return classified_mood
        else:
            print(f"Invalid mood classified: '{classified_mood}'. Finding closest match...")
            closest_mood = get_close_matches(classified_mood, valid_moods, n=1, cutoff=0.2)
            if closest_mood:
                return closest_mood[0]
            return "happy"  # Default fallback mood

    except Exception as e:
        print(f"Error in mood classification: {str(e)}")
        return "happy"  # Fallback to 'happy' if something goes wrong

# Function to get recommendations based on classified mood
def get_spotify_recommendations_for_mood(mood):
    mood_attributes = MOOD_TO_ATTRIBUTES.get(mood, {'energy': 0.5, 'valence': 0.5, 'genre': 'indie'})
    try:
        results = sp.recommendations(seed_genres=[mood_attributes['genre']],
                                     limit=10,
                                     target_energy=mood_attributes['energy'],
                                     target_valence=mood_attributes['valence'])
        return [{'name': track['name'],
                 'artist': track['artists'][0]['name'],
                 'url': track['external_urls']['spotify'],
                 'image': track['album']['images'][0]['url'] if track['album']['images'] else "https://via.placeholder.com/50"
                 } for track in results['tracks']]
    except Exception as e:
        print(f"Error getting Spotify recommendations: {str(e)}")
        return []

# Main route to recommend songs based on user mood
@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form['mood']
    print(f"Received mood input: {user_input}")

    if 'history' not in session:
        session['history'] = []

    # Use Cohere to classify the mood from user input
    classified_mood = classify_mood_with_generation(user_input)
    print(f"Classified mood: {classified_mood}")

    # Get Spotify recommendations based on the classified mood
    songs = get_spotify_recommendations_for_mood(classified_mood)

    # Store the classified mood and recommendations in session history
    session['history'].insert(0, {
        'mood': user_input,
        'classified_mood': classified_mood,
        'songs': songs
    })
    session['history'] = session['history'][:10]  # Keep only the latest 10 entries
    session.modified = True

    # Return the classified mood and recommendations to the client
    return jsonify({
        'mood': user_input,
        'classified_mood': classified_mood,
        'songs': songs
    })

# Route to get history
@app.route('/history', methods=['GET'])
def get_history():
    history = session.get('history', [])
    print(f"Returning history: {history}")
    return jsonify(history)

# Route to clear history
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

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True)

