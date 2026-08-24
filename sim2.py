import os, sys, random, json
from collections import Counter
os.environ.pop("OPENROUTER_API_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ["OPENAI_API_KEY"] = ""

def fresh():
    for m in ["game_logic","enhanced_passages","llm"]:
        sys.modules.pop(m, None)
    import game_logic
    return game_logic

def detect_pp(path):
    # Μετράει πραγματικά διαδοχικά μοτίβα A->B->A πάνω στην ακολουθία καταστάσεων
    return sum(
        1
        for i in range(len(path) - 2)
        if path[i] == path[i + 2] and path[i] != path[i + 1]
    )

def run_one(seed, top_k, max_turns=80):
    random.seed(seed)
    gl=fresh()
    st=gl.player_state
    state="village_square"; gl.enter_state(state,st)
    visited=Counter(); trans=Counter(); comp=None
    path=[state]
    for t in range(max_turns):
        visited[state]+=1
        p=gl.get_storylet_passage(state,st)
        ch=gl.order_choices_by_weight(state,p.get("choices",[]),st=st)
        if not ch: break
        k=min(top_k,len(ch))
        c=ch[0] if top_k==1 else random.choice(ch[:k])
        gl.tick_turn(st,state)
        nxt,_=gl.apply_choice_and_advance(st,state,c)
        trans[f"{state}->{nxt}"]+=1
        state=nxt
        path.append(nxt)
        if st.get("quests",{}).get("red_stone",{}).get("completed"):
            comp=t+1; break
    return {"completed":comp is not None,"ct":comp,"turns":min(t+1,max_turns),
            "distinct":len(visited),"trans":dict(trans),
            "pp":detect_pp(path),"path":path,"visited":dict(visited)}

def summarize(results,label):
    N=len(results)
    nc=sum(r["completed"] for r in results)
    cts=[r["ct"] for r in results if r["completed"]]
    paths=set(tuple(r["path"]) for r in results if r["completed"])
    agg=Counter()
    for r in results:
        for s,c in r["visited"].items(): agg[s]+=c
    tv=sum(agg.values())
    return {
        "label":label,"runs":N,
        "completion_rate":round(100*nc/N,1),
        "avg_ct":round(sum(cts)/len(cts),1) if cts else 0,
        "min_ct":min(cts) if cts else 0,"max_ct":max(cts) if cts else 0,
        "avg_distinct":round(sum(r["distinct"] for r in results)/N,1),
        "distinct_paths":len(paths),
        "avg_pp":round(sum(r["pp"] for r in results)/N,2),
        "coverage":len(agg),
        "top":[(s,round(100*c/tv,1)) for s,c in agg.most_common(6)],
    }



def main():
    N=5000
    guided=[run_one(s,1) for s in range(N)]
    explorer=[run_one(s,3) for s in range(N)]
    out={"guided":summarize(guided,"Καθοδηγούμενος (top-1)"),
         "explorer":summarize(explorer,"Εξερευνητής (top-3)")}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    json.dump(out,open("sim2_results.json","w"),ensure_ascii=False)


if __name__ == "__main__":
    main()
