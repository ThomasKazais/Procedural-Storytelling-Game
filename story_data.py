# --------------------------
# Δυναμικός πίνακας μεταβάσεων:
# Κάθε state έχει ένα dict {επιλογή: πιθανότητα}, που οδηγεί στο επόμενο state ίσο με το όνομα της επιλογής.
# --------------------------
base_matrix = {

    # -- Κεντρικό Χωριό --
    "village square": {
        "greet the elder": 0.4,
        "explore the bazaar": 0.3,
        "leave the village": 0.3,
    },
    "greet the elder": {
        "ask about the village's history": 0.5,
        "ask for a place to visit": 0.5,
    },
    "ask about the village's history": {"elder reveals treasure hint": 1.0},
    "ask for a place to visit": {"elder suggests bazaar": 1.0},
    "elder reveals treasure hint": {"seek the mysterious stranger": 1.0},
    "elder suggests bazaar": {"explore the bazaar": 1.0},

    # -- Bazaar / Εμπορική περιοχή --
    "explore the bazaar": {
        "talk to the merchant": 0.6,
        "help a lost traveler": 0.4,
    },
    "talk to the merchant": {
        "ask for the map price": 0.5,
        "offer to trade for the map": 0.5,
    },
    "ask for the map price": {"merchant states price": 1.0},
    "offer to trade for the map": {"merchant accepts trade": 1.0},
    "merchant states price": {
        "decide to buy map": 0.7,
        "decide to leave": 0.3
    },
    "merchant accepts trade": {"receive the map": 1.0},
    "receive the map": {"seek the treasure": 1.0},
    "seek the treasure": {"treasure found!": 1.0},

    "help a lost traveler": {
        "give directions": 0.5,
        "offer escort": 0.5,
    },
    "give directions": {"traveler grateful": 1.0},
    "offer escort": {"traveler joins you": 1.0},
    "traveler grateful": {"explore the bazaar": 1.0},
    "traveler joins you": {"village outskirts": 1.0},

    # -- Εκτός χωριού --
    "leave the village": {"village outskirts": 1.0},
    "village outskirts": {
        "enter the dark forest": 0.3,
        "follow the road to another town": 0.4,
        "return to the village square": 0.3,
    },

    # -- Dark Forest Branch --
    "enter the dark forest": {
        "fight wolves": 0.3,
        "sneak around wolves": 0.4,
        "turn back": 0.3,
    },
    "fight wolves": {"wolves defeated": 1.0},
    "sneak around wolves": {"wolves bypassed": 1.0},
    "turn back": {"village outskirts": 1.0},
    "wolves defeated": {"forest clearing": 1.0},
    "wolves bypassed": {"forest clearing": 1.0},
    "forest clearing": {
        "search for hidden path": 0.5,
        "set up camp": 0.5
    },
    "search for hidden path": {"mysterious cave": 1.0},
    "set up camp": {"rest until morning": 1.0},
    "rest until morning": {"village outskirts": 1.0},

    "mysterious cave": {
        "enter cave": 0.5,
        "leave cave": 0.5
    },
    "enter cave": {"strange ruins": 1.0},
    "leave cave": {"forest clearing": 1.0},
    "strange ruins": {"solve puzzle door": 1.0},
    "solve puzzle door": {"hidden treasure room": 1.0},
    "hidden treasure room": {"treasure found!": 1.0},

    # -- Road to Another Town Branch --
    "follow the road to another town": {
        "bandit ambush": 0.5,
        "find a resting spot": 0.5,
    },
    "bandit ambush": {
        "fight the bandits": 0.5,
        "surrender valuables": 0.5
    },
    "fight the bandits": {"bandits defeated": 1.0},
    "surrender valuables": {"bandits leave": 1.0},
    "bandits defeated": {"continue on road": 1.0},
    "bandits leave": {"continue on road": 1.0},
    "continue on road": {"arrive at new town": 1.0},
    "find a resting spot": {"rest until morning": 1.0},
    "arrive at new town": {"explore new town": 1.0},
    "explore new town": {
        "some side quest?": 0.4,
        "return to road": 0.3,
        "visit blacksmith's forge": 0.3
    },
    "some side quest?": {"complete side quest": 1.0},
    "complete side quest": {"arrive at new town": 1.0},
    "return to road": {"village outskirts": 1.0},

    # -- Blacksmith / Σιδεράς --
    "visit blacksmith's forge": {
        "ask about forging a new blade": 0.4,
        "sell found loot": 0.3,
        "offer help to blacksmith": 0.3,
    },
    "ask about forging a new blade": {"blacksmith demands rare gem": 1.0},
    "sell found loot": {"gain some gold": 1.0},
    "offer help to blacksmith": {"collect ore from mine": 1.0},
    "blacksmith demands rare gem": {"need rare gem for blade": 1.0},
    "gain some gold": {"blacksmith trade ends": 1.0},
    "blacksmith trade ends": {"explore new town": 1.0},
    "collect ore from mine": {"dark mine entrance": 1.0},
    "need rare gem for blade": {"explore new town": 1.0},

    # -- Σκοτεινό Ορυχείο --
    "dark mine entrance": {
        "enter the mine": 0.5,
        "turn back to blacksmith": 0.5,
    },
    "turn back to blacksmith": {"visit blacksmith's forge": 1.0},
    "enter the mine": {"mine interior": 1.0},
    "mine interior": {
        "search for ore": 0.5,
        "search deeper for gem": 0.5
    },
    "search for ore": {"found some ore": 1.0},
    "found some ore": {"return to blacksmith's forge": 1.0},
    "return to blacksmith's forge": {"offer ore to blacksmith": 1.0},
    "offer ore to blacksmith": {"blacksmith trade ends": 1.0},

    "search deeper for gem": {
        "fight cave spider": 0.4,
        "sneak past spider": 0.4,
        "retreat": 0.2
    },
    "fight cave spider": {"spider defeated": 1.0},
    "sneak past spider": {"found rare gem": 1.0},
    "retreat": {"mine interior": 1.0},
    "spider defeated": {"found rare gem": 1.0},
    "found rare gem": {"return to blacksmith's forge": 1.0},

    # -- Mysterious Stranger (Ενδεικτικό quest) --
    "seek the mysterious stranger": {"solve a riddle": 1.0},
    "solve a riddle": {"receive treasure location": 1.0},
    "receive treasure location": {"seek the treasure": 1.0},

    # -- Όταν βρεις θησαυρό --
    "treasure found!": {
        "royal invitation": 0.5,
        "end your journey": 0.5
    },
    "end your journey": {},
    "royal invitation": {"capital city gates": 1.0},

    # -- Πρωτεύουσα --
    "capital city gates": {
        "enter the capital": 0.7,
        "turn away": 0.3
    },
    "turn away": {"village outskirts": 1.0},
    "enter the capital": {
        "visit royal palace": 0.4,
        "explore capital streets": 0.3,
        "search for wizard's tower": 0.3
    },
    "visit royal palace": {"audience with king": 1.0},
    "audience with king": {
        "accept royal quest": 0.5,
        "decline politely": 0.5
    },
    "accept royal quest": {"cursed temple": 1.0},
    "decline politely": {"capital city gates": 1.0},

    "explore capital streets": {
        "enter fancy tavern": 0.4,
        "visit market district": 0.3,
        "talk with street minstrel": 0.3
    },
    # ...προσθετω και άλλα όταν είμαι έτοιμος να ενισχύσω την ιστορία

    "search for wizard's tower": {"wizard tower entrance": 1.0},
    "wizard tower entrance": {
        "knock on door": 0.5,
        "try to sneak in": 0.5
    },
    # ...προσθετω και άλλα όταν είμαι έτοιμος να ενισχύσω την ιστορία

    "cursed temple": {
        "explore temple halls": 0.5,
        "attempt purification ritual": 0.5
    },
    # ...προσθετω και άλλα όταν είμαι έτοιμος να ενισχύσω την ιστορία
}

# --------------------------
# Rewards για κάθε state->choice
# --------------------------
player_rewards = {
    "village square": {
        "greet the elder": 0.3,
        "explore the bazaar": 0.2,
        "leave the village": 0.2,
    },
    "greet the elder": {
        "ask about the village's history": 0.4,
        "ask for a place to visit": 0.2,
    },
    "explore the bazaar": {
        "talk to the merchant": 0.3,
        "help a lost traveler": 0.4,
    },
    "talk to the merchant": {
        "ask for the map price": 0.2,
        "offer to trade for the map": 0.3,
    },
    "merchant states price": {
        "decide to buy map": 0.3,
        "decide to leave": 0.1,
    },
    "village outskirts": {
        "enter the dark forest": 0.3,
        "follow the road to another town": 0.3,
        "return to the village square": 0.1,
    },
    "enter the dark forest": {
        "fight wolves": 0.2,
        "sneak around wolves": 0.3,
        "turn back": 0.1,
    },
    "follow the road to another town": {
        "bandit ambush": 0.3,
        "find a resting spot": 0.2,
    },
    "help a lost traveler": {
        "give directions": 0.3,
        "offer escort": 0.4,
    },

    "visit blacksmith's forge": {
        "ask about forging a new blade": 0.3,
        "sell found loot": 0.2,
        "offer help to blacksmith": 0.3,
    },
    "dark mine entrance": {
        "enter the mine": 0.3,
        "turn back to blacksmith": 0.1,
    },
    "mine interior": {
        "search for ore": 0.2,
        "search deeper for gem": 0.4,
    },
    "search deeper for gem": {
        "fight cave spider": 0.3,
        "sneak past spider": 0.3,
        "retreat": 0.1
    },

    "treasure found!": {
        "royal invitation": 0.5,
        "end your journey": 0.1
    },
    "royal invitation": {
        "capital city gates": 0.3
    },
    "capital city gates": {
        "enter the capital": 0.4,
        "turn away": 0.1
    },
    "enter the capital": {
        "visit royal palace": 0.3,
        "explore capital streets": 0.2,
        "search for wizard's tower": 0.3
    },
    # ...προσθετω και άλλα όταν είμαι έτοιμος να ενισχύσω την ιστορία
}

# --------------------------
# Απόθεμα παίκτη
# --------------------------
player_inventory = {
    "gold": 10,
    "map": False,
    "medicine": 0,
    "rare_gem": False,      # για τον σιδερά ή άλλες αποστολές
    "magic_scroll": False,  # πιθανό να βρεθεί στον wizard tower
    "elven_blade": False,   # αν ο σιδεράς το σφυρηλατήσει κλπ.
}

# --------------------------
# Requirements επιλογών
# (state, choice) -> {αντικείμενο: ποσότητα ή bool}
# --------------------------
choice_requirements = {
    ("merchant states price", "decide to buy map"): {"gold": 5},
    ("fight the bandits", "bandits defeated"): {"gold": 0},

    # Παράδειγμα: χρειάζεται να έχεις το rare_gem = True
    # για να "προχωρήσεις" σε κάποια μετάβαση
    ("blacksmith demands rare gem", "need rare gem for blade"): {"rare_gem": 1},

    # ...προσθετω και άλλα όταν είμαι έτοιμος να ενισχύσω την ιστορία
}
