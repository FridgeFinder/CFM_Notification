"""
Constants for fridge notification processing.
"""

# Condition mapping, KEY = Status Report Database key, VALUE = User Notification Preference database key
CONDITION_MAP = {
    'good': 'good',
    'dirty': 'dirty',
    'out of order': 'outOfOrder',
    'not at location': 'notAtLocation',
    'ghost': 'ghost'
}

CONDITION_MESSAGE_MAP = {
    'good': 'Fridge is in good condition',
    'dirty': 'Fridge needs cleaning',
    'outOfOrder': 'Fridge needs repairs',
    'notAtLocation': 'Fridge has been moved',
    'ghost': 'Fridge has been permanently removed'
}

FOOD_LEVEL_MESSAGE_MAP = {
    0: 'Fridge is out of food',
    1: 'Fridge has a little food',
    2: 'Fridge has plenty of food',
    3: 'Fridge is full'
}

FOOD_LEVEL_NOTIFICATION_MAP = {
    0: 'noFood',
    1: 'hasFood',
    2: 'hasFood',
    3: 'hasFood'
}
