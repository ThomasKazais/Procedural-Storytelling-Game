import threading
import queue
import tkinter as tk
from tkinter import ttk
from typing import Optional

from game_logic import (
    player_state, get_storylet_passage, apply_choice_and_advance,
    order_choices_by_weight, tick_turn, cooldown_remaining, enter_state
)
from llm import paraphrase_via_llm

class StoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Procedural Story (Tkinter)")
        self.geometry("900x750")
        self.configure(bg="#0f1115")

        default_font = ("Segoe UI", 11)
        self.option_add("*Font", default_font)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", padding=10)
        style.configure("TFrame", background="#0f1115")
        style.configure("Title.TLabel", foreground="#e6e6e6", background="#0f1115", font=("Segoe UI Semibold", 13))
        style.configure("Body.TLabel", foreground="#d7dae0", background="#0f1115")
        style.configure("Meta.TLabel", foreground="#9aa3af", background="#0f1115")
        style.configure("Notice.TLabel", foreground="#b5f4a5", background="#0f1115")

        self.container = ttk.Frame(self, padding=16, style="TFrame")
        self.container.pack(fill="both", expand=True)

        self.meta = ttk.Label(self.container, text="", style="Meta.TLabel", anchor="w")
        self.meta.pack(fill="x", pady=(0, 8))

        self.story_frame = ttk.Frame(self.container, style="TFrame")
        self.story_frame.pack(fill="both", expand=True)
        self.story_text = tk.Text(self.story_frame, wrap="word", height=16, bg="#111318", fg="#e8ebf1",
                                  insertbackground="#e8ebf1", bd=0, padx=10, pady=10, relief="flat")
        self.story_text.pack(fill="both", expand=True)

        self.status = ttk.Label(self.container, text="", style="Meta.TLabel", anchor="w")
        self.status.pack(fill="x", pady=(6, 6))

        self.choice_frame = ttk.Frame(self.container, style="TFrame")
        self.choice_frame.pack(fill="x", pady=(6, 0))

        self.feedback = ttk.Label(self.container, text="", style="Notice.TLabel", anchor="w")
        self.feedback.pack(fill="x", pady=(6, 0))

        self.current_state = "village_square"
        # Ρυθμίσεις εμφάνισης επιλογών
        self.show_all = False          
        self.compact_choices = True    
        self.max_choices_compact = 4   # μέγιστο 4 επιλογές σε compact προβολή
        self.post_end_ack = False  # εμφάνιση "THE END" μόνο μια φορα οταν είναι να εμφανιστεί
        self._llm_queue = queue.Queue()
        self._render_lock = threading.Lock()
        enter_state(self.current_state, player_state)
        self.render_state()

    def clear_choices(self):
        for w in self.choice_frame.winfo_children():
            w.destroy()

    def set_story_text(self, text):
        self.story_text.configure(state="normal")
        self.story_text.delete("1.0", "end")
        self.story_text.insert("1.0", text)
        self.story_text.configure(state="disabled")

    def set_status(self, text):
        self.status.configure(text=text)

    def set_meta(self, state, tone):
        tone_text = tone if tone else "default"
        self.meta.configure(text=f"State: {state}   •   Tone: {tone_text}")

    def set_feedback(self, lines):
        self.feedback.configure(text="\n".join(lines))

    def set_buttons_state(self, enabled: bool):
        for w in self.choice_frame.winfo_children():
            if isinstance(w, ttk.Button):
                w.configure(state=("normal" if enabled else "disabled"))
    
    def _is_end_reached(self, state: str) -> bool:
        """
        We consider 'THE END' reached when the Red Stone quest is completed
        and we're at the treasure scene. We only show it once per run.
        """
        if self.post_end_ack:
            return False
        q = player_state.get("quests", {}).get("red_stone", {})
        return bool(q.get("completed")) and state == "treasure_found"

    def on_show_more(self):
        """Expand the current state's choices."""
        self.show_all = True
        self.render_state()

    def _continue_after_end(self):
        """User chose to keep exploring after the 'THE END' banner."""
        self.post_end_ack = True
        # Re-render του ίδιο state με κανονικά κουμπιά επιλογών
        self.render_state()    

    def _render_end_screen(self, base_text: str):
        """
        Show the narrative + a bold THE END banner and two buttons:
        - Continue exploring (resume)
        - Close story (exit app)
        """
        # Εμφάνιση αφήγησης (χωρίς νέα κλήση στο LLM)
        self.set_story_text(base_text + "\n\n— THE END —")
        self.set_status("")
        self.clear_choices()

        end_label = ttk.Label(self.choice_frame, text="THE END", style="Title.TLabel", anchor="center")
        end_label.pack(fill="x", pady=(6, 6))

        btn_continue = ttk.Button(
            self.choice_frame,
            text="Continue exploring",
            command=self._continue_after_end
        )
        btn_continue.pack(fill="x", pady=6)

        btn_close = ttk.Button(
            self.choice_frame,
            text="Close story",
            command=self.destroy 
        )
        btn_close.pack(fill="x", pady=6)

    def render_state(self, feedback_msgs=None):
        with self._render_lock:
            state_id = self.current_state
            passage = get_storylet_passage(state_id, player_state)
            tone = passage.get("tone")
            base_text = passage.get("text", "")

            # Προετοιμασία UI 
            self.set_meta(self.current_state, tone)
            self.set_story_text("")
            self.set_feedback(feedback_msgs or [])
            self.clear_choices()

            # Έλεγχος για τέλος της ιστορίας (εμφανίζεται μόνο μια φορά)
            if self._is_end_reached(self.current_state):
                self._render_end_screen(base_text)
                return

            # Ταξινόμηση επιλογών μόνο αν δεν έχει έχει τελειώσει η ιστορία
            choices = order_choices_by_weight(
                self.current_state,
                passage.get("choices", []),
                st=player_state
            )

            # Εναλλακτική επιλογή αν ο παίκτης έχει κολλήσει
            if len(choices) <= 1:
                choices = choices + [{
                    "text": "Ask around for new leads",
                    "next": "village_square",
                    "effects": []
                }]

            # Compact προβολή επιλογών με δυνατότητα εμφάνισης περισσοτέρων
            MAX_CHOICES_COMPACT = getattr(self, "max_choices_compact", 4)
            MIN_ENABLED = 2  # για εμφάνιση τουλάχιστον 2 επιλογών

            # Διαχωρισμός επιλογών βάση cooldown (πρώτα οι "διαθέσιμες")
            enabled, disabled = [], []
            for ch in choices:
                cd = cooldown_remaining(state_id, ch["next"])
                (enabled if cd == 0 else disabled).append((ch, cd))

            # Απόφαση για το τι θα εμφανιστεί
            if (not getattr(self, "compact_choices", True)) or getattr(self, "show_all", False):
                # εμφάνιση όλων (πρώτα οι διαθέσιμες)
                display_list = enabled + disabled
            else:
                # Compact προβολή (ξεκινάμε με τις καλύτερες διαθέσιμες)
                display_list = enabled[:MAX_CHOICES_COMPACT]

                # Διασφάλιση ελάχιστου αριθμού διαθέσιμων επιλογών
                visible_enabled = sum(1 for _, cd in display_list if cd == 0)
                if visible_enabled < MIN_ENABLED:
                    need = MIN_ENABLED - visible_enabled
                    display_list += disabled[:need]

                # Συμπλήρωση υπόλοιπων θέσεων μέχρι το όριο
                taken = set(id(p) for p in display_list)
                for pool in (enabled, disabled):
                    for pair in pool:
                        if len(display_list) >= MAX_CHOICES_COMPACT:
                            break
                        if id(pair) not in taken:
                            display_list.append(pair)
                            taken.add(id(pair))

            # Δημιουργία κουμιών επιλογών
            more_btn = None
            for ch, cd in display_list:
                label = ch["text"] + (f"  (cooldown {cd})" if cd > 0 else "")
                btn = ttk.Button(self.choice_frame, text=label, command=lambda c=ch: self.on_choose(c))
                btn.pack(fill="x", pady=6)

            # Κουμπι "Εμφάνιση περισσότερων" αν υπάρχουν κρυφές επιλογές
            if getattr(self, "compact_choices", True) and (not getattr(self, "show_all", False)) and (len(display_list) < len(choices)):
                more_btn = ttk.Button(self.choice_frame, text="Show more options…", command=self.on_show_more)
                more_btn.pack(fill="x", pady=6)

            # Εκκίνηση παραγωγής αφήγησης σε background thread
            self.set_status("Generating narration…")
            self.set_buttons_state(False)

            # Το κουμπί "περισσότερα" παραμένει ενεργό κατά τη φόρτωση
            try:
                if more_btn is not None:
                    more_btn.state(["!disabled"])
            except Exception:
                pass

            threading.Thread(
                target=self._llm_worker,
                args=(base_text, self.current_state, tone),
                daemon=True
            ).start()

        self.after(50, self._poll_llm_queue)

    def _llm_worker(self, text, state, tone):
        try:
            out = paraphrase_via_llm(text, state, tone=tone)
        except Exception:
            out = text
        self._llm_queue.put(out)

    def _poll_llm_queue(self):
        try:
            out = self._llm_queue.get_nowait()
        except queue.Empty:
            self.after(50, self._poll_llm_queue)
            return
        self.set_story_text(out)
        self.set_status("")
        self.set_buttons_state(True)

    def on_choose(self, choice):
        self.set_buttons_state(False)
        tick_turn(player_state, self.current_state)
        next_state, msgs = apply_choice_and_advance(player_state, self.current_state, choice)
        self.current_state = next_state
        self.show_all = False
        self.render_state(feedback_msgs=msgs or [])
        

if __name__ == "__main__":
    app = StoryApp()
    app.mainloop()
