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

@app.route("/", methods=['POST'])
def incoming_sms():
    """Send a dynamic reply to an incoming text message"""
    # Get the message the user sent our Twilio number
    body = request.values.get('Body', None)
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
        resp = MessagingResponse()
        resp.message(message)
        return str(resp)
    else:
        return '', 200


if __name__ == "__main__":
    app.run()
