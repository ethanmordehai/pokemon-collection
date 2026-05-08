# PokéCollect

Application locale Flask pour gérer une collection d'items Pokémon scellés, mettre à jour les prix via eBay.fr et suivre les actualités TCG.

## Lancement

```powershell
cd "C:\Users\MORDEHAI Ethan\Documents\Codex\2026-05-08\je-veux-que-tu-me-cr\pokemon-collection"
pip install -r requirements.txt
python app.py
```

Ouvre ensuite http://localhost:5000.

## Notes

- Les données sont stockées dans `collection.json`.
- Le bouton de mise à jour globale interroge eBay avec un délai aléatoire entre les items.
- Si eBay ou une source d'actualité bloque la requête, l'app conserve les dernières valeurs connues et affiche un état d'avertissement.
- L'export CSV est disponible depuis le bouton `Export CSV`.
