"""Cloud scheduler: persist newly discovered employer jobs and optional Discord alerts."""
import json,os,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.request import Request,urlopen
from job_engine import gather,rank

ROOT=Path(__file__).resolve().parent
FEED=ROOT/"data"/"jobs.json"
THRESHOLD=int(os.environ.get("FRANK_MIN_SCORE","62"))

def merge(old,found,working,now):
    known={j["id"]:j.copy() for j in old if j.get("id")}
    fresh=[]
    found_ids={j["id"] for j in found}
    for j in found:
        points,why=rank(j)
        if points<THRESHOLD: continue
        if j["id"] not in known:
            record={k:j.get(k) for k in ("id","company","title","location","url","posted_at","sports","source","board")}
            record.update(score=points,why=why,first_seen=now,active=True)
            known[j["id"]]=record
            fresh.append(record)
        else:
            known[j["id"]].update(score=points,why=why,active=True,title=j["title"],url=j["url"])
    for job in known.values():
        if job.get("board") in working and job["id"] not in found_ids:
            job["active"]=False
    cutoff=datetime.fromisoformat(now)-timedelta(days=30)
    results=[]
    for job in known.values():
        try: first=datetime.fromisoformat(job["first_seen"].replace("Z","+00:00"))
        except (KeyError,ValueError):first=datetime.now(timezone.utc)
        if job.get("active",True) or first>=cutoff: results.append(job)
    results.sort(key=lambda j:(j.get("active",True),j.get("first_seen","")),reverse=True)
    return results[:400],fresh

def alert(fresh):
    hook=os.environ.get("FRANK_DISCORD_WEBHOOK","")
    if not hook:return
    for j in sorted(fresh,key=lambda x:x["score"],reverse=True)[:4]:
        if j["score"]<78:continue
        message="🐾 **Frank fetched a promising role!**\n**"+j["title"][:110]+"** at "+j["company"][:75]+"\n"+j["location"][:125]+"\nFit "+str(j["score"])+"/100 — "+j["why"][:140]+"\n"+j["url"]
        try:
            req=Request(hook,method="POST",headers={"Content-Type":"application/json","User-Agent":"Frank/1.0"},
                        data=json.dumps({"content":message}).encode("utf-8"))
            with urlopen(req,timeout=12):pass
        except Exception as e: print("Discord alert unavailable:",str(e)[:120],file=sys.stderr)

def main():
    boards=json.loads((ROOT/"boards.json").read_text(encoding="utf-8"))
    found,errors,working=gather(boards)
    print("Frank scanned",len(found),"openings across",len(working),"boards")
    for e in errors:print("Unavailable board:",e,file=sys.stderr)
    if not working:
        print("All job boards failed; preserving previous findings",file=sys.stderr)
        return 1
    try:old=json.loads(FEED.read_text(encoding="utf-8")).get("jobs",[])
    except (OSError,ValueError):old=[]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs,new=merge(old,found,working,now)
    if jobs!=old:
        FEED.parent.mkdir(parents=True,exist_ok=True)
        FEED.write_text(json.dumps({"version":1,"jobs":jobs},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Saved",len(jobs),"matching roles;",len(new),"new to Frank")
    alert(new)
    return 0

if __name__=="__main__":raise SystemExit(main())
