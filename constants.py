# with trial account, twilio puts in an annoying message which takes up characters
TWILIO_MESSAGE_CHARACTER_COUNT = 38

# careful, most characters which aren't ascii will count for many characters
MAX_SMS_CHARACTER_COUNT = 160

# abort routing computation if A and B are too far from each other (in km)
MAX_FLYING_DISTANCE = 30

# when writing itinerary, we truncate street name when it's too long
MAX_CHARS_PER_WAY = 20

# in routing we first write the total itinerary distance
ITINERARY_DISTANCE_CHARACTER_COUNT = 17

# how many characters we take to write direction and distance to cover before next
ITINERARY_BASE_DIRECTION_CHARACTER_COUNT= 13

# how many kilometers I am ready to walk to save one sms
SMS_TO_METER_PREFERENCE = 0.3

# in degrees
PARALLELISM_TOLERANCE = 20

# in km
MIN_DISTANCE_FOR_WAY_BEARING = 0.02

DIFFICULT_WAYS = ['path', 'cycleway', 'chemin']