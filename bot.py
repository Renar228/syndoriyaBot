import os
import random
import base64
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pymongo import MongoClient
from config import MONGODB_URI, ALLOWED_GROUP_IDS, OWNER_IDS, manga_recommendations, manga_facts

# Connexion à MongoDB
client = MongoClient(MONGODB_URI)
db = client['manga_tactical_game_db']
characters_collection = db['characters']
games_collection = db['games']
quests_collection = db['quests']
character_images = db['character_images']

# Fonction pour vérifier si le message provient d'un groupe autorisé
def is_allowed_group(update: Update) -> bool:
    return update.effective_chat.id in ALLOWED_GROUP_IDS

# Décorateur pour restreindre l'accès aux groupes autorisés
def restricted_access(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_allowed_group(update):
            await update.message.reply_text("Ce bot n'est pas autorisé dans ce groupe.")
            return
        return await func(update, context)
    return wrapper

# Fonction pour obtenir une salutation en fonction de l'heure
def get_greeting(hour):
    if 5 <= hour < 12:
        return "Bonjour"
    elif 12 <= hour < 18:
        return "Bon après-midi"
    else:
        return "Bonsoir"

# Fonction pour obtenir ou créer un personnage
def get_or_create_character(user_id):
    character = characters_collection.find_one({'user_id': user_id})
    if not character:
        character = {
            'user_id': user_id,
            'name': 'Héros Manga',
            'health': 100,
            'attack': 10,
            'defense': 5,
            'experience': 0,
            'level': 1,
            'money': 100,
            'artifacts': [],
            'techniques': [],
            'photo': None
        }
        characters_collection.insert_one(character)
    return character

# Fonction pour créer ou obtenir un jeu
def get_or_create_game(user_id):
    game = games_collection.find_one({'user_id': user_id})
    if not game:
        game = {
            'user_id': user_id,
            'current_enemy': None,
            'game_state': 'idle',
            'current_quest': None
        }
        games_collection.insert_one(game)
    return game

@restricted_access
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    character = get_or_create_character(user.id)
    current_hour = datetime.now().hour
    greeting = get_greeting(current_hour)
    await update.message.reply_text(
        f"{greeting} et bienvenue dans le monde manga tactique, {user.mention_html()}! "
        f"Votre héros '{character['name']}' est prêt pour l'aventure.\n\n"
        "Utilisez /status pour voir vos statistiques, /quest pour obtenir une quête, "
        "/recommend pour obtenir une recommandation de manga ou /fact pour un fait amusant sur les mangas."
    )

@restricted_access
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    character = get_or_create_character(user.id)
    status_text = (
        f"Statut de {character['name']}:\n"
        f"Santé: {character['health']}\n"
        f"Attaque: {character['attack']}\n"
        f"Défense: {character['defense']}\n"
        f"Expérience: {character['experience']}\n"
        f"Niveau: {character['level']}\n"
        f"Argent: {character['money']} pièces\n"
        f"Artefacts: {', '.join(character['artifacts']) if character['artifacts'] else 'Aucun'}\n"
        f"Techniques: {', '.join(character['techniques']) if character['techniques'] else 'Aucune'}"
    )
    
    if character['photo']:
        photo_bytes = base64.b64decode(character['photo'])
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_bytes, caption=status_text)
    else:
        await update.message.reply_text(status_text)

@restricted_access
async def quest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    game = get_or_create_game(user.id)
    
    if game['current_quest']:
        await update.message.reply_text("Vous avez déjà une quête en cours. Terminez-la d'abord!")
        return
    
    quests = [
        {
            'name': 'Chasse aux trésors',
            'description': 'Trouvez le trésor caché dans la forêt mystique.',
            'reward': {'money': 100, 'artifact': 'Amulette de force'},
            'difficulty': 'Facile'
        },
        {
            'name': 'Défense du village',
            'description': 'Protégez le village contre une horde de bandits.',
            'reward': {'money': 200, 'technique': 'Coup de poing dévastateur'},
            'difficulty': 'Moyen'
        },
        {
            'name': 'Le dragon ancestral',
            'description': 'Affrontez le dragon ancestral dans son antre.',
            'reward': {'money': 500, 'artifact': 'Épée légendaire', 'technique': 'Souffle du dragon'},
            'difficulty': 'Difficile'
        }
    ]
    
    quest = random.choice(quests)
    game['current_quest'] = quest
    games_collection.update_one({'user_id': user.id}, {'$set': game})
    
    keyboard = [
        [InlineKeyboardButton("Accepter", callback_data='accept_quest')],
        [InlineKeyboardButton("Refuser", callback_data='refuse_quest')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Nouvelle quête disponible: {quest['name']}\n"
        f"Description: {quest['description']}\n"
        f"Difficulté: {quest['difficulty']}\n"
        f"Récompense: {', '.join(str(v) + ' ' + k for k, v in quest['reward'].items())}\n"
        "Voulez-vous accepter cette quête?",
        reply_markup=reply_markup
    )

async def quest_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    character = get_or_create_character(user.id)
    game = get_or_create_game(user.id)
    
    if query.data == 'accept_quest':
        quest = game['current_quest']
        success = random.random() < 0.7  # 70% de chance de réussite
        
        if success:
            reward_text = []
            if 'money' in quest['reward']:
                character['money'] += quest['reward']['money']
                reward_text.append(f"{quest['reward']['money']} pièces")
            if 'artifact' in quest['reward']:
                character['artifacts'].append(quest['reward']['artifact'])
                reward_text.append(quest['reward']['artifact'])
            if 'technique' in quest['reward']:
                character['techniques'].append(quest['reward']['technique'])
                reward_text.append(quest['reward']['technique'])
            
            characters_collection.update_one({'user_id': user.id}, {'$set': character})
            await query.edit_message_text(
                f"Félicitations! Vous avez réussi la quête '{quest['name']}'.\n"
                f"Vous avez gagné: {', '.join(reward_text)}."
            )
        else:
            await query.edit_message_text(
                f"Malheureusement, vous avez échoué à la quête '{quest['name']}'.\n"
                "Reposez-vous et réessayez plus tard!"
            )
        
        game['current_quest'] = None
        games_collection.update_one({'user_id': user.id}, {'$set': game})
    
    elif query.data == 'refuse_quest':
        game['current_quest'] = None
        games_collection.update_one({'user_id': user.id}, {'$set': game})
        await query.edit_message_text("Vous avez refusé la quête. Une autre sera disponible plus tard.")

@restricted_access
async def add_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    character = get_or_create_character(user.id)
    
    if update.message.photo:
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
        photo_bytes = await photo_file.download_as_bytearray()
        photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
        
        character['photo'] = photo_base64
        characters_collection.update_one({'user_id': user.id}, {'$set': character})
        
        await update.message.reply_text("La photo de votre personnage a été mise à jour avec succès!")
    else:
        await update.message.reply_text("Veuillez envoyer une photo pour mettre à jour l'image de votre personnage.")

@restricted_access
async def recommend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    recommendation = random.choice(manga_recommendations)
    await update.message.reply_text(f"Je vous recommande de lire : {recommendation}")

@restricted_access
async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    manga_fact = random.choice(manga_facts)
    await update.message.reply_text(f"Saviez-vous que : {manga_fact}")

@restricted_access
async def upload_character_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in OWNER_IDS:
        await update.message.reply_text("Seuls les propriétaires du bot peuvent uploader des images de personnages.")
        return

    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        image_bytes = await file.download_as_bytearray()
        
        context.user_data['temp_image'] = image_bytes
        await update.message.reply_text("Pour quel personnage est cette image ? (Envoyez le nom)")
    else:
        await update.message.reply_text("Veuillez envoyer une image en pièce jointe.")

async def save_character_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in OWNER_IDS:
        return

    character_name = update.message.text.lower()
    image_bytes = context.user_data.get('temp_image')
    
    if not image_bytes:
        await update.message.reply_text("Aucune image en attente. Veuillez d'abord envoyer une image.")
        return

    image_id = character_images.insert_one({'image': image_bytes}).inserted_id
    characters_collection.update_one({'name': character_name}, {'$set': {'image_id': str(image_id)}}, upsert=True)

    await update.message.reply_text(f"Image uploadée avec succès pour {character_name.capitalize()}!")
    del context.user_data['temp_image']

@restricted_access
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = update.message.text.lower()
    current_hour = datetime.now().hour
    greeting = get_greeting(current_hour)
    
    if any(word in message_text for word in ['bonjour', 'salut', 'coucou', 'hello']):
        await update.message.reply_text(f"{greeting}! Comment puis-je vous aider aujourd'hui dans votre aventure ?")
    elif 'bonsoir' in message_text:
        await update.message.reply_text(f"Bonsoir! Prêt pour une aventure nocturne ?")
    elif 'merci' in message_text:
        await update.message.reply_text("De rien! C'est toujours un plaisir d'aider un héros comme vous.")
    elif 'au revoir' in message_text or 'adieu' in message_text:
        await update.message.reply_text("Au revoir! J'espère vous revoir bientôt pour de nouvelles aventures!")
    elif 'recommande' in message_text or 'manga' in message_text:
        await recommend(update, context)
    elif 'fait' in message_text or 'info' in message_text:
        await fact(update, context)
    else:
        await update.message.reply_text(
            "Je n'ai pas compris votre message. Voici ce que je peux faire :\n"
            "/start - Commencer une nouvelle partie\n"
            "/status - Voir le statut de votre personnage\n"
            "/quest - Obtenir une nouvelle quête\n"
            "/recommend - Obtenir une recommandation de manga\n"
            "/fact - Apprendre un fait intéressant sur les mangas\n"
            "/add_photo - Ajouter une photo à votre personnage"
        )
def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Le token du bot Telegram n'est pas défini dans les variables d'environnement.")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("status", status, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("quest", quest, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("add_photo", add_photo, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("recommend", recommend, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("fact", fact, filters=filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("upload_character_image", upload_character_image, filters=filters.ChatType.GROUPS))

    application.add_handler(CallbackQueryHandler(quest_action))

    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, add_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_message))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=OWNER_IDS) & filters.ChatType.GROUPS,
        save_character_image
    ))

    print("Le bot démarre...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    print("Le bot s'est arrêté.")

if __name__ == "__main__":
    main()
