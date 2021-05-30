import os
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from weather import get_rain_response
from routing import get_walking_itinerary_response

app = Flask(__name__)

# Find these values at https://twilio.com/user/account
twilio_sid = os.environ['TWILIO_ACCOUNT_SID']
twilio_token = os.environ['TWILIO_AUTH_TOKEN']
client = Client(twilio_sid, twilio_token)

def send_message(msg, destination):
    if msg and msg != '':
        client.messages.create(from_=os.environ.get('TWILIO_NUMBER'),
                      to=destination,
                      body=msg)

@app.route("/", methods=['POST'])
def incoming_sms():
    """Send a dynamic reply to an incoming text message"""
    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)
    phone_number = request.values.get('from', None)
    message = ''

    # Determine the right reply for this message
    if body == 'Hello':
        # Start our TwiML response
        message = 'Hi'
    elif body[:12] == 'Will it rain':
        message = get_rain_response(body)
    elif body[:9] == 'Walk from':
        message = get_walking_itinerary_response(body)
    if message and message != '':
        send_message(message, phone_number)
    # for long requests like routing, twilio may have stopped listening
    # TODO set up a task queue or make hacks
    # https://stackoverflow.com/questions/48994440/execute-a-function-after-flask-returns-response
    return '', 200


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
