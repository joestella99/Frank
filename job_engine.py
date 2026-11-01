"""Employer job board readers and conservative scoring. Python standard library only."""
import json,re,html
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor,as_completed

def get_json(url):
    with urlopen(Request(url,headers={"User-Agent":"FrankJobDog/1.0","Accept":"application/json"}),timeout=18) as r:
        return json.load(r)

def plain(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>"," ",str(s or "")))).strip()

def collect_board(b,fetch=get_json):
    typ,slug=b["provider"],quote(b["slug"],safe="")
    found=[]
    if typ=="greenhouse":
        items=fetch("https://boards-api.greenhouse.io/v1/boards/"+slug+"/jobs?content=true").get("jobs",[])
        for j in items:
            if j.get("internal_job_id") is None: continue
            found.append(dict(id="gh:"+slug+":"+str(j.get("id")),title=j.get("title",""),
                              location=(j.get("location") or {}).get("name",""),
                              url=j.get("absolute_url",""),description=plain(j.get("content",""))[:5000],
                              posted_at=j.get("first_published") or ""))
    elif typ=="ashby":
        items=fetch("https://api.ashbyhq.com/posting-api/job-board/"+slug+"?includeCompensation=true").get("jobs",[])
        for j in items:
            if j.get("isListed") is False: continue
            locs=[j.get("location","")]+[x.get("location","") for x in j.get("secondaryLocations",[])]
            if j.get("workplaceType")=="Remote": locs.append("Remote")
            found.append(dict(id="ashby:"+slug+":"+str(j.get("id") or j.get("jobUrl")),
                              title=j.get("title",""),location="; ".join(dict.fromkeys(filter(None,locs))),
                              url=j.get("applyUrl") or j.get("jobUrl") or "",
                              description=plain(j.get("descriptionPlain") or j.get("descriptionHtml"))[:5000],
                              posted_at=j.get("publishedAt") or ""))
    elif typ=="lever":
        for j in fetch("https://api.lever.co/v0/postings/"+slug+"?mode=json"):
            loc=(j.get("categories") or {}).get("location","")
            if j.get("workplaceType")=="remote": loc=loc+"; Remote"
            found.append(dict(id="lever:"+slug+":"+str(j.get("id")),title=j.get("text",""),
                              location=loc,url=j.get("hostedUrl") or j.get("applyUrl") or "",
                              description=plain(j.get("descriptionPlain") or j.get("description"))[:5000],posted_at=""))
    elif typ=="smartrecruiters":
        items=fetch("https://api.smartrecruiters.com/v1/companies/"+slug+"/postings?limit=100&destination=PUBLIC").get("content",[])
        for j in items:
            loc=j.get("location") or {}
            place=", ".join(filter(None,[loc.get("city"),loc.get("region"),loc.get("country")]))
            if loc.get("remote"): place+="; Remote"
            found.append(dict(id="smart:"+slug+":"+str(j.get("id")),title=j.get("name",""),
                              location=place,url="https://jobs.smartrecruiters.com/"+slug+"/"+str(j.get("id")),
                              description="",posted_at=j.get("releasedDate") or ""))
    else: raise ValueError("Unknown job board provider: "+typ)
    for j in found:
        j.update(company=b["name"],sports=bool(b.get("sports")),source=b["provider"],board=b["provider"]+":"+b["slug"])
    return [j for j in found if j["title"] and str(j["url"]).startswith("https://")]

ROLES=[
    (r"(software|full.stack|front.end|back.end|backend|frontend|web|application|platform) (engineer|developer)",40,"Software engineering"),
    (r"(product manager|product owner|technical product|associate product)",42,"Product"),
    (r"(technical project manager|technical program manager|implementation engineer|solutions engineer)",37,"Technical delivery"),
    (r"(sdet|qa engineer|test automation|automation engineer|quality assurance)",35,"Automation / QA"),
    (r"(customer success engineer|support engineer|integration engineer|forward.deployed engineer)",34,"Technical client work"),
    (r"(data engineer|product analyst)",28,"Data / product analysis")
]
EXCLUDE=r"\b(chief|director|vice president|vp|head of|staff|principal|intern|internship|contractor|sales|account executive)\b"
NON_US=r"\b(london|uk|england|canada|toronto|india|europe|emea|latam|apac|singapore|germany|france|australia|ireland)\b"

def rank(j):
    title=j.get("title","").lower()
    if re.search(EXCLUDE,title): return (0,"Out of scope")
    hits=[(value,why) for pattern,value,why in ROLES if re.search(pattern,title)]
    if not hits: return (0,"Not a target role")
    pts,why=max(hits)
    loc=j.get("location","").lower()
    if re.search(r"new york|\bnyc\b|manhattan|brooklyn|queens|bronx|jersey city|hoboken",loc):
        pts+=26; place="NYC"
    elif re.search(r"\bremote\b|work from anywhere",loc) and not re.search(NON_US,loc):
        pts+=21; place="Possibly US-remote (verify)"
    else: return (0,"Outside preferred locations / unverified remote")
    if re.search(r"\b(senior|lead)\b",title): pts-=13
    reasons=[why,place]
    if j.get("sports"): pts+=18; reasons.append("Sports technology")
    skills=[x for x in ("python","typescript","playwright","automation","c#","sql","javascript","react","api") if x in j.get("description","").lower()]
    pts+=min(15,3*len(skills))+8
    if skills: reasons.append("Skills: "+", ".join(skills[:3]))
    return (max(0,min(100,pts))," · ".join(reasons))

def gather(boards,fetch=get_json):
    output=[];errors=[];working=set()
    active=[b for b in boards if b.get("enabled",True)]
    if not active:return output,errors,working
    with ThreadPoolExecutor(max_workers=min(5,len(active))) as pool:
        tasks={pool.submit(collect_board,b,fetch):b for b in active}
        for f in as_completed(tasks):
            b=tasks[f]
            try:
                output.extend(f.result())
                working.add(b["provider"]+":"+b["slug"])
            except Exception as e: errors.append(b["name"]+": "+str(e)[:150])
    return output,errors,working
