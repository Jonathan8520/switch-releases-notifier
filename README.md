# 🎮 Clash of Clans Code Scraper

Scraper automatique qui surveille les nouveaux codes Clash of Clans et envoie des notifications Discord.

## 🚀 Installation

### 1. Créer un Webhook Discord

1. Va dans ton serveur Discord
2. **Paramètres du serveur** → **Intégrations** → **Webhooks**
3. **Nouveau Webhook**
4. Nomme-le (ex: "CoC Codes")
5. Choisis le salon où poster
6. **Copie l'URL du webhook**

### 2. Configurer le repo GitHub

1. Va dans **Settings** → **Secrets and variables** → **Actions**
2. Clique sur **New repository secret**
3. Nom : `DISCORD_WEBHOOK`
4. Valeur : colle l'URL de ton webhook Discord
5. **Add secret**

### 3. Activer GitHub Actions

1. Va dans l'onglet **Actions**
2. Si c'est désactivé, clique sur "I understand my workflows, go ahead and enable them"

### 4. Lancer le premier test

1. Va dans **Actions** → **Scrape Clash of Clans Codes**
2. Clique sur **Run workflow** → **Run workflow**
3. Attends 30 secondes
4. Tu devrais recevoir une notification Discord !

## 📋 Structure du projet

```
coc-scraper-discord/
├── .github/
│   └── workflows/
│       └── scraper.yml      # Configuration GitHub Actions
├── scraper.py               # Script principal
├── requirements.txt         # Dépendances Python
├── seen.json               # Codes déjà détectés (auto-généré)
├── run_count.txt           # Compteur d'exécutions (auto-généré)
└── README.md               # Ce fichier
```

## 🔧 Fonctionnalités

- ✅ Scraping automatique toutes les 5 minutes
- ✅ Détection des nouveaux codes uniquement
- ✅ Retry automatique en cas d'erreur réseau
- ✅ Logs détaillés avec timestamps
- ✅ Heartbeat toutes les 10 exécutions
- ✅ Persistence des codes déjà vus
- ✅ Compatible GitHub Actions

## 🐛 Dépannage

### Le scraper ne s'exécute pas toutes les 5 minutes

C'est normal ! GitHub Actions peut retarder les crons de 5-15 minutes sur les repos gratuits. Pour du monitoring en temps réel, utilise plutôt :
- Un VPS avec crontab
- cron-job.org (gratuit)
- UptimeRobot

### Pas de notifications Discord

1. Vérifie que le secret `DISCORD_WEBHOOK` est bien configuré
2. Va dans **Actions** et regarde les logs d'exécution
3. Lance manuellement le workflow pour tester

### Le workflow échoue

1. Va dans **Actions** → clique sur l'exécution échouée
2. Regarde les logs pour voir l'erreur
3. Vérifie que `requirements.txt` est à la racine du repo

### Recevoir des notifications de test

Décommente temporairement ces lignes dans `scraper.py` :

```python
# Dans main(), après la vérification de WEBHOOK_URL
test_item = {"text": "Test - 20 Gems", "link": "https://example.com"}
notify_discord(test_item, is_test=True)
```

## 📊 Monitoring

Le scraper envoie un heartbeat toutes les 10 exécutions pour confirmer qu'il fonctionne. Si tu ne reçois rien pendant 1h, vérifie :

1. L'onglet **Actions** pour voir si les workflows s'exécutent
2. Les logs de la dernière exécution

## 🔐 Sécurité

- ⚠️ Ne commit **JAMAIS** ton URL de webhook Discord dans le code
- ✅ Utilise toujours les **GitHub Secrets**
- ✅ Le fichier `seen.json` peut être commité (pas de données sensibles)

## 📝 Personnalisation

### Changer la fréquence

Dans `.github/workflows/scraper.yml` :

```yaml
schedule:
  - cron: '*/10 * * * *'  # Toutes les 10 minutes
  - cron: '0 * * * *'     # Toutes les heures
  - cron: '0 */6 * * *'   # Toutes les 6 heures
```

### Changer le message Discord

Dans `scraper.py`, modifie la fonction `notify_discord()` :

```python
data = {
    "content": f"🚨 NOUVEAU CODE ! {item['text']}\n{item['link']}",
    "username": "CoC Bot",
    "avatar_url": "https://example.com/avatar.png"
}
```

## 📞 Support

En cas de problème :
1. Vérifie les logs dans **Actions**
2. Lance le workflow manuellement pour tester
3. Vérifie que le secret Discord est bien configuré

## 📜 License

Ce projet est libre d'utilisation. Enjoy ! 🎮