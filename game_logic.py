from story_data import player_rewards, player_inventory, choice_requirements
from dynamic_transition import DynamicTransitionMatrix

def can_make_choice(state, choice):
    """
    Checks if the player meets the inventory/requirement conditions for a choice.
    Returns True if they can, False otherwise.
    """
    if (state, choice) not in choice_requirements:
        return True
    
    needed = choice_requirements[(state, choice)]
    for item, needed_amount in needed.items():
        # Αν το requirement είναι gold:
        if item == "gold":
            # Χρειαζόμαστε τουλάχιστον 'needed_amount' gold
            if player_inventory["gold"] < needed_amount:
                return False

        # Αν είναι κάτι boolean, π.χ. 'rare_gem':
        elif item == "rare_gem":
            if needed_amount > 0 and not player_inventory["rare_gem"]:
                return False
        
        # Έξτρα αν χρειαστεί
        elif item == "magic_scroll":
            if needed_amount > 0 and not player_inventory["magic_scroll"]:
                return False
        
        # ...προσθετω και άλλα όταν είμαι έτοιμος να ενισχύσω την ιστορία

    return True

def apply_choice_effects(state, choice):
    """
    Applies any effects from making a particular choice.
    Π.χ. αν πληρώνεις gold, αν κερδίζεις items, κλπ.
    """
    # Παράδειγμα με map:
    if (state, choice) == ("merchant states price", "decide to buy map"):
        cost = 5
        player_inventory["gold"] -= cost
        player_inventory["map"] = True
    
    if (state, choice) == ("offer to trade for the map", "merchant accepts trade"):
        player_inventory["map"] = True
    
    if (state, choice) == ("help a lost traveler", "offer escort"):
        player_inventory["medicine"] += 1
    
    if (state, choice) == ("fight the bandits", "bandits defeated"):
        player_inventory["gold"] += 3

    # Αν ψάξεις βαθύτερα για gem και κερδίσεις ή προσπεράσεις την αράχνη...
    if (state, choice) in [
        ("search deeper for gem", "spider defeated"),
        ("search deeper for gem", "sneak past spider")
    ]:
        player_inventory["rare_gem"] = True

    # Αν πούλησες loot στο σιδερά...
    if (state, choice) == ("sell found loot", "gain some gold"):
        player_inventory["gold"] += 5

    
def handle_choice(choice, current_state, transition_matrix, dialogue_label, update_dialogue_callback):
    """
    Κύρια συνάρτηση για επιλογή παίκτη:
    - Ελέγχει αν η επιλογή είναι έγκυρη για το state
    - Ελέγχει αν έχεις τα requirements
    - Υπολογίζει reward, ενημερώνει πιθανότητες
    - Εφαρμόζει επιπτώσεις inventory
    - Επιστρέφει το επόμενο state
    """
    choices = transition_matrix.get_choices(current_state)
    if choice not in choices:
        dialogue_label.config(text="Invalid choice for this state.")
        return current_state

    # Ελέγχουμε requirements
    if not can_make_choice(current_state, choice):
        dialogue_label.config(text="You don't meet the requirements for that action.")
        return current_state

    # Βρίσκουμε reward (ή 0.1 default)
    reward = player_rewards.get(current_state, {}).get(choice, 0.1)
    # Ενημερώνουμε τις πιθανότητες
    transition_matrix.update_probability(current_state, choice, reward)

    # Εφαρμόζουμε τυχόν αλλαγές στο inventory
    apply_choice_effects(current_state, choice)

    # Πάμε στο επόμενο state (το key = choice)
    new_state = choice
    update_dialogue_callback(new_state)
    return new_state
