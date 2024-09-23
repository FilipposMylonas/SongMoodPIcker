import os
import sys
from flask import Flask, render_template, request, jsonify, session
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import cohere

print("Starting application...")

# Set environment variables
os.environ['SPOTIFY_CLIENT_ID'] = 'c4d974cf20524d5e99a7cdbb426c08f2'
os.environ['SPOTIFY_CLIENT_SECRET'] = 'fc8553edafaa48ffa2504a646554d7cd'
os.environ['COHERE_API_KEY'] = '1kSZ1GLeZYKomOqyTaKmSAnSYiMAhJk3TSKBUVxw'

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

# Cohere setup
cohere_api_key = os.getenv('COHERE_API_KEY')
if not cohere_api_key:
    raise ValueError("Cohere API key not found. Please set COHERE_API_KEY environment variable.")

co = cohere.Client(cohere_api_key)

print("Cohere client initialized.")

def analyze_mood(text):
    try:
        response = co.classify(
            model='large',
            inputs=[text],
            examples=[
                {"text": "I'm feeling great today!", "label": "very positive"},
                {"text": "Everything is going well.", "label": "positive"},
                {"text": "I'm not sure how I feel.", "label": "neutral"},
                {"text": "I'm having a bad day.", "label": "negative"},
                {"text": "Everything is terrible.", "label": "very negative"}
            ]
        )
        return response.classifications[0].prediction
    except Exception as e:
        print(f"Error in sentiment analysis: {str(e)}")
        return "neutral"

def get_spotify_recommendations(mood):
    print(f"Getting recommendations for mood: {mood}")
    mood_to_genre = {
        "very positive": "happy",
        "positive": "pop",
        "neutral": "indie",
        "negative": "sad",
        "very negative": "blues"
    }
    genre = mood_to_genre.get(mood, "pop")

    try:
        results = sp.recommendations(seed_genres=[genre], limit=10)
        return [{'name': track['name'],
                 'artist': track['artists'][0]['name'],
                 'url': track['external_urls']['spotify'],
                 'image': track['album']['images'][0]['url'] if track['album']['images'] else "https://via.placeholder.com/50"
                 } for track in results['tracks']]
    except Exception as e:
        print(f"Error getting Spotify recommendations: {str(e)}")
        return []

@app.route('/')
def index():
    print("Serving index page.")
    if 'history' not in session:
        session['history'] = []
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form['mood']
    print(f"Received mood: {user_input}")
    mood = analyze_mood(user_input)
    songs = get_spotify_recommendations(mood)

    if 'history' not in session:
        session['history'] = []
    session['history'].insert(0, user_input)
    session['history'] = session['history'][:10]
    session.modified = True

    print(f"Returning recommendations for mood: {mood}")
    return jsonify({
        'mood': user_input,
        'analyzed_mood': mood,
        'songs': songs
    })

@app.route('/history', methods=['GET'])
def get_history():
    history = session.get('history', [])
    print(f"Returning history: {history}")
    return jsonify(history)

@app.route('/clear_history', methods=['POST'])
def clear_history():
    session['history'] = []
    session.modified = True
    print("History cleared.")
    return jsonify({"message": "History cleared successfully"})

@app.route('/model_status')
def model_status():
    return jsonify({"ready": True})  # Cohere API is always ready

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True)

print("Application setup complete.")