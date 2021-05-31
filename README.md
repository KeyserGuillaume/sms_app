sms_app permet de connaitre la météo à venir et faire des itinéraires à pied rien qu'en échangeant des sms avec un numéro loué par twilio.

Un sms est envoyé au numéro twilio, twilio envoie une requête à un serveur flask (hébergé sur heroku), qui peut envoyer à twilio un ou des messages à renvoyer vers le numéro de téléphone.

Mettre les identifiants twilio et les numéros de téléphone dans l'environnement shell (export TWILIO_ACCOUNT_SID=yyyyyyyyyyyyyyyyyy && export TWILIO_AUTH_TOKEN=yyyyyyyyyyyyyyyyyy && export PHONE_NUMBER=+XXXXXXXXXX && export TWILIO_NUMBER=+XXXXXXXXXX && export WEATHER_TOKEN=WWWWWWWWWWWWWWWW)

Faire python3 -m pipenv shell

Puis python app.py

Ensuite utiliser des commandes telles que:
curl -X POST -F 'Body=Hello' localhost:5000
curl -X POST -F 'Body=Will it rain in Dunkerque ?' localhost:5000
curl -X POST -F 'Body=Will it rain in Paris 18 ?' localhost:5000
curl -X POST -F 'Body=Walk from 156 avenue loubet, dunkerque to 168 avenue de la libération' localhost:5000
curl -X POST -F 'Body=Walk from 41 rue joseph jacquard, dunkerque to 52 rue pierre et marie curie' localhost:5000
curl -X POST -F 'Body=Walk from 22 rue doudeauville, paris to 5 avenue république, paris' localhost:5000

Et observer les réponses renvoyées

Pour déployer: git push heroku master

heroku logs --tail pour voir les erreurs

# TODO:
- Walk from: ajouter la possibilité "Walk from X to atm"
- Walk from: ajouter la possibilité "Walk from X to sncf"
- Créer "Velib from A to B", "Drop Velib near X", "Find Velib near X"
- Créer requête 'Ask WolframAlpha X'
- Mettre un nombre max de sms envoyables par requêtes (10?)
