"""
============================================================================
 ablation.py - Μελετη Απομονωσης Μηχανισμων (Ablation Study)
============================================================================
Τρεχει τον ΠΡΑΓΜΑΤΙΚΟ αλγοριθμο επιλογης του game_logic.py, απενεργοποιωντας
εναν μηχανισμο καθε φορα, και μετραει την επιδραση σε:
  - ποσοστο ολοκληρωσης της αποστολης Red Stone
  - μεσο αριθμο βροχων ταλαντωσης (A->B->A) ανα εκτελεση
  - πληθος διακριτων αφηγηματικων διαδρομων
  - μεσο αριθμο διακριτων καταστασεων ανα εκτελεση

Δεν τροποποιει ποτε τα αρχεια πηγης - κανει μονο in-memory monkeypatching.

ΧΡΗΣΗ:
    python ablation.py                 # 5000 εκτελεσεις/παραλλαγη (default)
    python ablation.py --runs 1000     # περισσοτερες εκτελεσεις
    python ablation.py --topk 1        # καθοδηγουμενος παικτης (παντα top-1)
    python ablation.py --seed 123      # διαφορετικο seed
    python ablation.py --csv out.csv   # αποθηκευση και σε CSV

ΣΗΜΕΙΩΣΗ: Με σταθερο seed (default 0) τα αποτελεσματα ειναι ΑΝΑΠΑΡΑΓΩΓΙΜΑ.
============================================================================
"""
import os, sys, random, json, argparse, contextlib, io
from collections import Counter


# Διασφάλιση offline εκτέλεσης (καθαρίζουμε τυχόν keys ώστε να μην ενεργοποιηθεί το LLM).
os.environ.pop("OPENROUTER_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ["OPENAI_API_KEY"] = ""


def fresh():
    """Επαναφορτωση των modules ωστε να μηδενιζεται το global state
    (βαρη, cooldowns, visit_counts, recent_states) σε καθε εκτελεση."""
    for m in ["game_logic", "enhanced_passages", "llm"]:
        sys.modules.pop(m, None)
    import game_logic
    return game_logic


def detect_pingpong(path):
    # Μετραει πραγματικα διαδοχικα μοτιβα A->B->A πανω στην ακολουθια καταστασεων
    return sum(
        1
        for i in range(len(path) - 2)
        if path[i] == path[i + 2] and path[i] != path[i + 1]
    )


def apply_ablation(gl, mode):
    """Απενεργοποιει εναν μηχανισμο μεσω monkeypatching."""
    if mode == "no_novelty":
        gl._novelty_term = lambda depth, vc, nxt: 0.0
    elif mode == "no_loop":
        gl.is_loopy_transition = lambda src, dst: False
    elif mode == "no_cooldown":
        gl.cooldown_remaining = lambda src, dst: 0
        class _Zero(dict):
            def get(self, k, d=0): return 0
        gl.state_cooldowns = _Zero()
    elif mode == "no_cluster":
        gl._cluster_switch_mult = lambda src, dst: 1.0
    elif mode == "no_arc":
        gl._arc_multiplier = lambda src, dst, st: 1.0
    elif mode == "no_reinforcement":
        gl.bump_transition_weight = lambda *a, **k: None
    # "full" => καμια αλλαγη


def run_one(gl, seed, top_k=3, max_turns=80):
    """Μια αυτοματη διελευση του παιχνιδιου."""
    random.seed(seed)
    st = gl.player_state
    state = "village_square"
    gl.enter_state(state, st)
    visited = Counter()
    trans = Counter()
    completed_turn = None
    path = [state]

    # Σιγαζουμε το stdout (π.χ. μηνυματα micro-choice) κατα την εκτελεση.
    with contextlib.redirect_stdout(io.StringIO()):
        for t in range(max_turns):
            visited[state] += 1
            passage = gl.get_storylet_passage(state, st)
            choices = gl.order_choices_by_weight(state, passage.get("choices", []), st=st)
            if not choices:
                break
            k = min(top_k, len(choices))
            choice = choices[0] if top_k == 1 else random.choice(choices[:k])
            gl.tick_turn(st, state)
            nxt, _ = gl.apply_choice_and_advance(st, state, choice)
            trans[f"{state}->{nxt}"] += 1
            state = nxt
            path.append(nxt)
            if st.get("quests", {}).get("red_stone", {}).get("completed"):
                completed_turn = t + 1
                break

    return {
        "completed": completed_turn is not None,
        "ct": completed_turn,
        "distinct": len(visited),
        "trans": dict(trans),
        "pp": detect_pingpong(path),
        "path": path,
    }


def study(mode, n_runs, top_k, base_seed):
    results = []
    for s in range(n_runs):
        gl = fresh()
        apply_ablation(gl, mode)
        results.append(run_one(gl, seed=base_seed * 100000 + s, top_k=top_k))

    n = len(results)
    nc = sum(r["completed"] for r in results)
    cts = [r["ct"] for r in results if r["completed"]]
    paths = set(tuple(r["path"]) for r in results if r["completed"])
    return {
        "mode": mode,
        "completion_rate": round(100 * nc / n, 1),
        "avg_completion_turn": round(sum(cts) / len(cts), 1) if cts else 0,
        "distinct_paths": len(paths),
        "avg_pingpong": round(sum(r["pp"] for r in results) / n, 2),
        "avg_distinct_states": round(sum(r["distinct"] for r in results) / n, 1),
    }


def main():
    ap = argparse.ArgumentParser(description="Ablation study for the narrative selection algorithm.")
    ap.add_argument("--runs", type=int, default=5000, help="Εκτελεσεις ανα παραλλαγη (default 5000)")
    ap.add_argument("--topk", type=int, default=3, help="Επιλογη αναμεσα στις top-k (1=καθοδηγουμενος, default 3)")
    ap.add_argument("--seed", type=int, default=0, help="Base seed για αναπαραγωγιμοτητα (default 0)")
    ap.add_argument("--csv", type=str, default=None, help="Προαιρετικη αποθηκευση σε CSV")
    ap.add_argument("--json", type=str, default="ablation_results.json", help="Αρχειο εξοδου JSON")
    args = ap.parse_args()

    modes = ["full", "no_loop", "no_arc", "no_novelty",
             "no_cluster", "no_cooldown", "no_reinforcement"]

    print(f"Ablation study | runs/variant={args.runs} | top_k={args.topk} | seed={args.seed}")
    print("-" * 92)
    header = f"{'Variant':<22}{'Compl.%':>10}{'AvgTurn':>10}{'Paths':>12}{'PingPong':>10}{'DistStates':>12}"
    print(header)
    print("-" * 92)

    out = {}
    for m in modes:
        res = study(m, args.runs, args.topk, args.seed)
        out[m] = res
        print(f"{m:<22}{res['completion_rate']:>10}{res['avg_completion_turn']:>10}"
              f"{res['distinct_paths']:>12}{res['avg_pingpong']:>10}{res['avg_distinct_states']:>12}")

    print("-" * 92)
    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"JSON saved -> {args.json}")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["mode", "completion_rate", "avg_completion_turn",
                        "distinct_paths", "avg_pingpong", "avg_distinct_states"])
            for m in modes:
                r = out[m]
                w.writerow([m, r["completion_rate"], r["avg_completion_turn"],
                            r["distinct_paths"], r["avg_pingpong"], r["avg_distinct_states"]])
        print(f"CSV saved  -> {args.csv}")


if __name__ == "__main__":
    main()
