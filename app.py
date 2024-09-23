import os
import sys
from flask import Flask, render_template, request
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from textblob import TextBlob

# Set environment variables
os.environ['SPOTIFY_CLIENT_ID'] = 'c4d974cf20524d5e99a7cdbb426c08f2'
os.environ['SPOTIFY_CLIENT_SECRET'] = 'fc8553edafaa48ffa2504a646554d7cd'

# Debug information
print("Python version:", sys.version)
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Contents of current directory:", os.listdir())

app = Flask(__name__)

# Spotify setup
client_credentials_manager = SpotifyClientCredentials(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def analyze_mood(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity
    if sentiment > 0.5:
        return "very positive"
    elif 0 < sentiment <= 0.5:
        return "positive"
    elif -0.5 <= sentiment < 0:
        return "negative"
    else:
        return "very negative"

def get_spotify_recommendations(mood):
    # Map moods to Spotify genres
    mood_to_genre = {
        "very positive": "happy",
        "positive": "pop",
        "negative": "sad",
        "very negative": "blues"
    }
    genre = mood_to_genre.get(mood, "pop")

    results = sp.recommendations(seed_genres=[genre], limit=10)
    return [{'name': track['name'], 'artist': track['artists'][0]['name'], 'url': track['external_urls']['spotify']} for track in results['tracks']]

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_input = request.form['mood']
        mood = analyze_mood(user_input)
        songs = get_spotify_recommendations(mood)
        return render_template('index.html', songs=songs)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)