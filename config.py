import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
ALLOWED_GROUP_IDS = list(map(int, os.getenv('ALLOWED_GROUP_IDS', '').split(',')))
OWNER_IDS = list(map(int, os.getenv('OWNER_IDS', '').split(',')))

# Listes de recommandations de manga et de faits
manga_recommendations = [
    "One Piece", "Naruto", "Attack on Titan", "Death Note", "My Hero Academia",
    "Fullmetal Alchemist", "Dragon Ball", "Tokyo Ghoul", "Demon Slayer", "Hunter x Hunter"
]

manga_facts = [
    "Le manga le plus vendu de tous les temps est One Piece.",
    "Osamu Tezuka, créateur d'Astro Boy, est souvent appelé le 'Dieu du manga'.",
    "Le terme 'manga' a été inventé par le célèbre artiste Hokusai au 19ème siècle.",
    "Les mangas se lisent généralement de droite à gauche.",
    "Le plus long manga jamais publié est JoJo's Bizarre Adventure, avec plus de 130 volumes."
]
