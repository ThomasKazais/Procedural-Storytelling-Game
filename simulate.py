"""
Αυτοματοποιημένος προσομοιωτής διελεύσεων για την μηχανή παιχνιδιού-αφήγησης.
Αξιοποιεί τον πραγματικό αλγόριθμο order_choices_by_weight / apply_choice_and_advance logic,
επιλέγοντας απο τις top-k επιλογές για να προσομοιώσει παίκτη που ακολουθεί κυρίως
την "καθοδήγηση" του συστήματος αλλά διατηρεί έναν βαθμό ελευθερίας. 
"""
import os, sys, random, json
from collections import Counter

# Απενεργοποίηση LLM για γρηγορότερη απόδοση της προσομοίωσης
os.environ.pop("OPENROUTER_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ["OPENAI_API_KEY"] = ""  # διασφάλιση ότι δεν καλώ Client

def fresh_modules():
    """Re-import game_logic fresh so global state (weights, cooldowns,
    visit_counts, recent_states) resets between playthroughs."""
    for m in ["game_logic", "enhanced_passages", "llm"]:
        if m in sys.modules:
            del sys.modules[m]
    import game_logic
    return game_logic

def run_one(seed, max_turns=60, top_k=2):
    random.seed(seed)
    gl = fresh_modules()

    st = gl.player_state
    state = "village_square"
    gl.enter_state(state, st)

    visited = Counter()
    transitions = Counter()
    completed_turn = None
    path = [state]

    for t in range(max_turns):
        visited[state] += 1
        passage = gl.get_storylet_passage(state, st)
        choices = gl.order_choices_by_weight(state, passage.get("choices", []), st=st)
        if not choices:
            break
        # Επιλογή απο τις top-k επιλογές (κυρίως καθοδηγούμενες)
        k = min(top_k, len(choices))
        choice = random.choice(choices[:k])

        gl.tick_turn(st, state)
        nxt, _msgs = gl.apply_choice_and_advance(st, state, choice)
        transitions[(state, nxt)] += 1
        state = nxt
        path.append(nxt)

        q = st.get("quests", {}).get("red_stone", {})
        if q.get("completed"):
            completed_turn = t + 1
            break

    # Ανίχνευση αμφίδρομων μεταβάσεων A->B->A (ping-pong loops)
    return {
        "seed": seed,
        "completed": completed_turn is not None,
        "completed_turn": completed_turn,
        "turns": min(t + 1, max_turns),
        "distinct_states": len(visited),
        "visited": dict(visited),
        "transitions": {f"{a}->{b}": c for (a, b), c in transitions.items()},
        "path": path,
    }

def detect_pingpong(path):
    # Μετράει πραγματικά διαδοχικά μοτίβα A->B->A πάνω στην ακολουθία καταστάσεων
    return sum(
        1
        for i in range(len(path) - 2)
        if path[i] == path[i + 2] and path[i] != path[i + 1]
    )

def main():
    N = 500
    results = [run_one(seed=s) for s in range(N)]

    n_completed = sum(r["completed"] for r in results)
    completion_rate = 100.0 * n_completed / N

    comp_turns = [r["completed_turn"] for r in results if r["completed"]]
    avg_comp_turn = sum(comp_turns) / len(comp_turns) if comp_turns else 0
    min_comp = min(comp_turns) if comp_turns else 0
    max_comp = max(comp_turns) if comp_turns else 0

    avg_distinct = sum(r["distinct_states"] for r in results) / N

    # Ποικιλία διαδρομών (πόσες διακριτές διατεταγμένες ακολουθίες καταστάσεων)
    distinct_paths = set()
    for r in results:
        if r["completed"]:
            distinct_paths.add(tuple(r["path"]))
    n_distinct_paths = len(distinct_paths)

    # Ποσοστό αμφίδρομων μεταβάσεων
    total_pp = sum(detect_pingpong(r["path"]) for r in results)
    avg_pp = total_pp / N

    # Κατανομή επισκέψεων ανά κόμβο
    agg_visits = Counter()
    for r in results:
        for s, c in r["visited"].items():
            agg_visits[s] += c
    total_visits = sum(agg_visits.values())

    summary = {
        "runs": N,
        "completion_rate_pct": round(completion_rate, 1),
        "avg_completion_turn": round(avg_comp_turn, 1),
        "min_completion_turn": min_comp,
        "max_completion_turn": max_comp,
        "avg_distinct_states_per_run": round(avg_distinct, 1),
        "distinct_completing_paths": n_distinct_paths,
        "avg_pingpong_per_run": round(avg_pp, 2),
        "total_states_in_world": len(agg_visits),
    }

    # Πιο συχνά επισκεπτόμενα states
    top_states = [(s, round(100.0 * c / total_visits, 1)) for s, c in agg_visits.most_common(8)]

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("TOP_STATES:" + json.dumps(top_states, ensure_ascii=False))

    # Αποθήκευση αποτελεσμάτων σε JSON
    with open("sim_results.json", "w") as f:
        json.dump({"summary": summary, "top_states": top_states,
                   "completion_turns": comp_turns}, f, ensure_ascii=False)

if __name__ == "__main__":
    main()
