import os
from flask import Flask, render_template, request, jsonify, session
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import cohere
from dotenv import load_dotenv
from difflib import get_close_matches
import random


load_dotenv()

# Initialize Cohere client
cohere_api_key = os.getenv('1kSZ1GLeZYKomOqyTaKmSAnSYiMAhJk3TSKBUVxw')  # Replace with your real API key environment variable
co = cohere.Client(cohere_api_key)

print("Starting application...")

# Set environment variables
os.environ['SPOTIFY_CLIENT_ID'] = 'c4d974cf20524d5e99a7cdbb426c08f2'
os.environ['SPOTIFY_CLIENT_SECRET'] = 'fc8553edafaa48ffa2504a646554d7cd'

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
import random

# Function to classify mood using Cohere's generation API with 3 best words
def classify_mood_with_generation(user_input):
    prompt = f"""Given this input: '{user_input}', what are the three best words to describe this mood?
    Choose three from the following, separated by commas: happy, sad, relaxed, energetic, mysterious, romantic, angry, joyful, melancholic, hopeful, 
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
        classified_moods = response.generations[0].text.strip().lower().split(", ")

        valid_moods = list(MOOD_TO_ATTRIBUTES.keys())  # Only keep moods we handle
        filtered_moods = [mood for mood in classified_moods if mood in valid_moods]
        if len(filtered_moods) == 3:
            return filtered_moods
        else:
            return random.sample(valid_moods, 3)  # Fallback to random moods if anything fails

    except Exception as e:
        print(f"Error in mood classification: {str(e)}")
        return random.sample(valid_moods, 3)  # Fallback to 3 random moods if something goes wrong

# Function to randomize energy and valence and fetch Spotify recommendations
def get_spotify_recommendations_for_moods(moods):
    all_recommendations = []

    for mood in moods:
        mood_attributes = MOOD_TO_ATTRIBUTES.get(mood, {'energy': 0.5, 'valence': 0.5, 'genre': 'indie'})

        # Randomize energy and valence values
        randomized_energy = max(0.0, min(1.0, mood_attributes['energy'] + random.uniform(-0.5, 0.5)))
        randomized_valence = max(0.0, min(1.0, mood_attributes['valence'] + random.uniform(-0.5, 0.5)))

        try:
            results = sp.recommendations(seed_genres=[mood_attributes['genre']],
                                         limit=10,
                                         target_energy=randomized_energy,
                                         target_valence=randomized_valence)

            recommendations = [{'name': track['name'],
                                'artist': track['artists'][0]['name'],
                                'url': track['external_urls']['spotify'],
                                'image': track['album']['images'][0]['url'] if track['album']['images'] else "https://via.placeholder.com/50"
                                } for track in results['tracks']]
            all_recommendations.extend(recommendations)

        except Exception as e:
            print(f"Error getting Spotify recommendations: {str(e)}")

    return all_recommendations

# Main route to recommend songs based on user mood with three best words and random energy/valence
@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form['mood']
    print(f"Received mood input: {user_input}")

    if 'history' not in session:
        session['history'] = []

    # Use Cohere to classify the mood from user input (get 3 words)
    classified_moods = classify_mood_with_generation(user_input)
    print(f"Classified moods: {classified_moods}")

    # Get Spotify recommendations based on the classified moods with random energy/valence
    songs = get_spotify_recommendations_for_moods(classified_moods)

    # Store the classified moods and recommendations in session history
    session['history'].insert(0, {
        'mood': user_input,
        'classified_moods': classified_moods,
        'songs': songs
    })
    session['history'] = session['history'][:10]  # Keep only the latest 10 entries
    session.modified = True

    # Return the classified moods and recommendations to the client
    return jsonify({
        'mood': user_input,
        'classified_moods': classified_moods,
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

