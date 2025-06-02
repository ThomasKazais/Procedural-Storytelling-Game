import tkinter as tk
from dynamic_transition import DynamicTransitionMatrix
from story_data import base_matrix, player_inventory
from game_logic import handle_choice

# Αρχικό state
current_state = "village square"

# Φορτώνουμε τον πίνακα μεταβάσεων
transition_matrix = DynamicTransitionMatrix(base_matrix)

def update_dialogue(new_state=None):
    """
    Ενημερώνει το παράθυρο διαλόγου:
      - αλλάζει το τρέχον state αν δοθεί new_state
      - δείχνει το κείμενο με τα στοιχεία inventory
      - φτιάχνει κουμπιά για κάθε διαθέσιμη επιλογή από το transition_matrix
    """
    global current_state
    if new_state:
        current_state = new_state

    # Εμφάνιση κειμένου κατάστασης & inventory
    dialogue_label.config(
        text=(
            f"Current state: {current_state}\n"
            f"Gold: {player_inventory['gold']}, "
            f"Map: {player_inventory['map']}, "
            f"Medicine: {player_inventory['medicine']}, "
            f"Rare Gem: {player_inventory['rare_gem']}, "
            f"Magic Scroll: {player_inventory['magic_scroll']}, "
            f"Elven Blade: {player_inventory['elven_blade']}"
        )
    )

    # Καθαρισμός παλιών κουμπιών/στοιχείων
    for widget in choices_frame.winfo_children():
        widget.destroy()

    # Παίρνουμε τις πιθανές επιλογές για το τρέχον state
    choices = transition_matrix.get_choices(current_state)

    # Αν δεν υπάρχουν επιλογές, λήγουμε την ιστορία
    if len(choices) == 0:
        end_label = tk.Label(
            choices_frame,
            text="The story has ended!",
            font=("Helvetica", 12, "bold")
        )
        end_label.pack(pady=10)
        return

    # Για κάθε επιλογή, δημιουργούμε ένα κουμπί
    for option, prob in choices.items():
        button_text = f"{option}"
        button = tk.Button(
            choices_frame,
            text=button_text,
            command=lambda o=option: on_choice_selected(o)
        )
        button.pack(pady=5, padx=10, fill=tk.X)

def on_choice_selected(choice):
    """
    Όταν γίνεται κλικ σε μια επιλογή, καλούμε handle_choice από game_logic.py.
    Αν το state αλλάξει, ενημερώνουμε το διάλογο.
    """
    global current_state
    new_state = handle_choice(choice, current_state, transition_matrix, dialogue_label, update_dialogue)
    if new_state != current_state:
        update_dialogue(new_state)

# Δημιουργία του κύριου παραθύρου
root = tk.Tk()
root.title("A Village Adventure")

dialogue_label = tk.Label(
    root,
    text="",
    font=("Arial", 14),
    wraplength=600,
    justify="center"
)
dialogue_label.pack(pady=10)

choices_frame = tk.Frame(root)
choices_frame.pack(fill=tk.BOTH, expand=True)

# Εκκίνηση της ιστορίας
update_dialogue()

root.mainloop()
