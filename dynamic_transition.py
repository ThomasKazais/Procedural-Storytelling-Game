import random
from collections import defaultdict

class DynamicTransitionMatrix:
    """
    A class that manages dynamic transitions between story states using
    simple reinforcement learning mechanics.
    """
    def __init__(self, base_matrix):
        # Χρησιμοποιούμε την defaultdict για να μπορούμε να επεκτείνουμε δυναμικά (και να μην κρασάρει το πρόγραμμα)
        self.matrix = defaultdict(dict, base_matrix)

    def update_probability(self, state, choice, reward):
        """
        Ενημερώνουμε την πιθανότητα για (state->choice) βάσει του reward.
        
        Εφαρμογή:
          - Αυξάνουμε την πιθανότητα της επιλεγμένης δράσης κατά 'reward'.
          - Μειώνουμε λίγο για μη επιλεγμένες (ή μπορείς να το επεκτείνεις).
          - Περιορίζουμε [0.0, 1.0].
          - Στο τέλος κάνουμε normalize ώστε οι πιθανότητες να αθροίζουν 1.
        """
        if state in self.matrix and choice in self.matrix[state]:
            current_prob = self.matrix[state][choice]
            new_prob = current_prob + reward - 0.1 * (1 - reward)
            # clamp μεταξύ 0 και 1
            new_prob = max(0.0, min(1.0, new_prob))
            self.matrix[state][choice] = new_prob
            # κάνουμε normalize (κανονικοποίηση)
            self._normalize(state)

    def get_choices(self, state):
        """
        Επιστρέφει dict {choice: probability} για το συγκεκριμένο state.
        Αν δεν υπάρχει, γυρνάει ένα κενό dict.
        """
        return self.matrix.get(state, {})

    def _normalize(self, state):
        """
        Κανονικοποιεί τις πιθανότητες για ένα state ώστε να αθροίζουν 1.0.
        """
        total = sum(self.matrix[state].values())
        if total > 0:
            for choice in self.matrix[state]:
                self.matrix[state][choice] /= total
