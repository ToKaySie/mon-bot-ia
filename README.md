# 🤖 Bot IA Telegram - Ollama Cloud

Un bot Telegram intelligent propulsé par **Ollama Cloud**, avec support de conversation contextuelle, rate limiting, et déploiement serverless gratuit sur **Vercel**.

## ✨ Fonctionnalités

- 🧠 **IA conversationnelle** via Ollama Cloud (modèles LLM)
- 💬 **Mémoire contextuelle** : le bot se souvient du fil de conversation
- 🔄 **Commandes intuitives** : `/start`, `/reset`, `/model`, `/stats`, `/help`
- 🔒 **Rate limiting** pour éviter les abus
- 👤 **Restriction d'accès** par user ID Telegram
- 🚀 **Double mode** : local (polling) + serverless (webhook Vercel)
- 📝 **Messages longs** découpés automatiquement

## 📁 Structure du projet

```
bot-ia/
├── bot.py                  # Point d'entrée local (mode polling)
├── set_webhook.py          # Script de configuration webhook
├── requirements.txt        # Dépendances Python
├── vercel.json             # Config déploiement Vercel
├── .env.example            # Template de configuration
├── .gitignore
├── api/
│   └── webhook.py          # Fonction serverless Vercel
└── core/
    ├── __init__.py
    ├── config.py            # Configuration (variables d'env)
    ├── ollama_client.py     # Client API Ollama Cloud
    ├── conversation.py      # Gestion de l'historique
    ├── handlers.py          # Handlers Telegram
    └── rate_limiter.py      # Rate limiter
```

---

## 🛠️ Prérequis

1. **Python 3.10+**
2. **Un bot Telegram** créé via [@BotFather](https://t.me/BotFather)
3. **Un compte Ollama Cloud** avec une clé API ([ollama.com](https://ollama.com))

---

## ⚡ Démarrage rapide (Mode Local)

### 1. Cloner et installer

```bash
cd bot-ia
pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditez `.env` et remplissez :
```env
TELEGRAM_BOT_TOKEN=votre_token_botfather
OLLAMA_API_KEY=votre_cle_api_ollama
OLLAMA_MODEL=llama3.1:8b
```

### 3. Lancer le bot

```bash
python bot.py
```

Le bot est maintenant en ligne sur Telegram ! 🎉

---

## 🌐 Déploiement Gratuit sur Vercel (Serverless)

### Pourquoi Vercel ?
- ✅ **Gratuit** (tier hobby)
- ✅ **Toujours en ligne** (pas besoin de PC allumé)
- ✅ **Serverless** (se scale automatiquement)
- ✅ **Supporte Python**

### Étape 1 : Créer un compte Vercel

1. Allez sur [vercel.com](https://vercel.com) et créez un compte gratuit
2. Installez la CLI Vercel :
```bash
npm install -g vercel
```

### Étape 2 : Initialiser le projet

```bash
cd bot-ia
vercel login
```

### Étape 3 : Configurer les variables d'environnement sur Vercel

```bash
# Ajoutez vos secrets (une commande par variable)
vercel env add TELEGRAM_BOT_TOKEN
vercel env add OLLAMA_API_KEY
vercel env add OLLAMA_API_URL
vercel env add OLLAMA_MODEL
```

Ou bien via le dashboard Vercel :
1. Allez dans **Settings > Environment Variables**
2. Ajoutez chaque variable depuis votre `.env`

### Étape 4 : Déployer

```bash
vercel --prod
```

Notez l'URL de déploiement (ex: `https://bot-ia-xxx.vercel.app`).

### Étape 5 : Configurer le Webhook Telegram

```bash
python set_webhook.py https://bot-ia-xxx.vercel.app
```

C'est tout ! Le bot est maintenant en ligne 24/7 sans aucun serveur à gérer. 🚀

### Revenir au mode local

Si vous voulez revenir au mode local (polling) :
```bash
python set_webhook.py --delete
python bot.py
```

---

## 🔧 Configuration avancée

| Variable | Description | Défaut |
|----------|------------|--------|
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram | **requis** |
| `OLLAMA_API_KEY` | Clé API Ollama Cloud | **requis** |
| `OLLAMA_API_URL` | URL de l'API Ollama | `https://api.ollama.com/v1` |
| `OLLAMA_MODEL` | Modèle IA à utiliser | `llama3.1:8b` |
| `MAX_HISTORY` | Messages max en mémoire | `20` |
| `MAX_RESPONSE_LENGTH` | Longueur max des réponses | `4000` |
| `SYSTEM_PROMPT` | Personnalité du bot | *(prompt par défaut)* |
| `RATE_LIMIT_MESSAGES` | Messages max par période | `30` |
| `RATE_LIMIT_PERIOD` | Durée de la période (sec) | `60` |
| `ALLOWED_USERS` | IDs autorisés (ex: `123,456`) | *(tous)* |

---

## 💡 Commandes du bot

| Commande | Description |
|----------|-------------|
| `/start` | Message de bienvenue |
| `/help` | Guide d'utilisation |
| `/reset` | Effacer l'historique |
| `/model` | Voir le modèle actuel |
| `/model <nom>` | Changer de modèle |
| `/stats` | Statistiques |

---

## 🔐 Sécurité

- Les clés API sont stockées en variables d'environnement (jamais dans le code)
- Le `.env` est exclu du Git via `.gitignore`
- Rate limiting intégré pour prévenir les abus
- Restriction d'accès possible par user ID Telegram
