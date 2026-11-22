from flask import Flask, render_template, request, jsonify
import requests
import pandas as pd
import numpy as np
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

API_KEY = '97229981'

executor = ThreadPoolExecutor(max_workers=10)

@lru_cache(maxsize=100)
def get_movie_details(movie_id):
    url = f"http://www.omdbapi.com/?apikey={API_KEY}&i={movie_id}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.Timeout:
        return None
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    genre = request.form.get('genre')
    if not genre:
        return render_template('index.html', error="Please enter a genre.")

    movies = []
    page = 1

    def fetch_movie_page(page_num):
        url = f"http://www.omdbapi.com/?apikey={API_KEY}&s=movie&type=movie&page={page_num}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except requests.exceptions.Timeout:
            return None
        return None

    while len(movies) < 10:  # Fetch 10 movies
        future = executor.submit(fetch_movie_page, page)
        data = future.result()

        if not data or data.get("Response") == "False":
            break

        for movie in data.get('Search', []):
            movie_id = movie.get("imdbID")
            details = get_movie_details(movie_id)
            if not details or details.get("Response") == "False":
                continue

            movie_genre = details.get("Genre", "").lower()
            if genre.lower() in [g.strip().lower() for g in movie_genre.split(',')]:
                movies.append({
                    "Title": details.get("Title"),
                    "Year": details.get("Year"),
                    "Poster": details.get("Poster"),
                    "imdbRating": details.get("imdbRating", "N/A"),
                    "Genre": details.get("Genre"),
                    "Overview": details.get("Plot", "No description available.")
                })

            if len(movies) >= 10:
                break

        page += 1

    if not movies:
        return render_template('index.html', error="No movies found for this genre. Please try again.")

    df = pd.DataFrame(movies)

    df['imdbRating'] = pd.to_numeric(df['imdbRating'], errors='coerce')
    df = df.dropna(subset=['imdbRating'])
    df = df.sort_values(by='imdbRating', ascending=False)

    sorted_movies = df.to_dict(orient='records')

    return jsonify(sorted_movies) 

if __name__ == '__main__':
    app.run(debug=True)
