"""Frank, a tiny moving Windows desktop dog. Install Pillow before running."""
import base64,io,json,queue,random,sys,threading,tkinter as tk,webbrowser
from pathlib import Path
from urllib.request import Request,urlopen
from tkinter import ttk
from PIL import Image,ImageOps,ImageTk
from sound import generate_bark
from pet_motion import MotionController, FRAME_MS

BASE=Path(__file__).resolve().parent
HOME=Path.home()/".frank"
HOME.mkdir(exist_ok=True)
STATE=HOME/"desktop_stash.json"
FEED="https://raw.githubusercontent.com/joestella99/Frank/main/data/jobs.json"
COLOR="#fe00fe"
GOLD="#ffcb78"

def load_state():
    try:return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError,ValueError):return {"seen":[],"statuses":{},"saved_jobs":{}}

def save_state(state):
    STATE.write_text(json.dumps(state,indent=2),encoding="utf-8")

def read_feed():
    req=Request(FEED+"?v="+str(random.randint(0,999999)),headers={"User-Agent":"FrankJobDog/1.0","Cache-Control":"no-cache"})
    with urlopen(req,timeout=15) as r:return json.load(r).get("jobs",[])

class Pet:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("Frank")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost",True)
        self.root.configure(bg=COLOR)
        try:self.root.wm_attributes("-transparentcolor",COLOR)
        except tk.TclError:pass
        self.state=load_state()
        self.state.setdefault("seen",[])
        self.state.setdefault("statuses",{})
        self.state.setdefault("saved_jobs",{})
        self.jobs=[]
        self.messages=queue.Queue()
        self.dashboard=None
        self.bubble=None
        self.drag=None
        self.sound=True
        try:self.bark_file=generate_bark(HOME/"bark.wav")
        except Exception:self.bark_file=None
        self.running=True
        self.direction=-1
        self.tick=0
        self.sprite=self.make_sprite()
        self.motion=MotionController(self.sprite)
        self.current_image=ImageTk.PhotoImage(self.motion.frame())
        self.label=tk.Label(self.root,image=self.current_image,bg=COLOR,borderwidth=0,cursor="hand2")
        self.label.pack()
        self.width,self.height=self.motion.width,self.motion.height
        screen_w,screen_h=self.root.winfo_screenwidth(),self.root.winfo_screenheight()
        self.x=max(0,screen_w-self.width-38)
        self.floor=screen_h-self.height-75
        self.y=self.floor
        self.place()
        self.label.bind("<ButtonPress-1>",self.mouse_down)
        self.label.bind("<B1-Motion>",self.mouse_move)
        self.label.bind("<ButtonRelease-1>",self.mouse_up)
        self.label.bind("<Double-Button-1>",lambda e:self.open_stash())
        self.label.bind("<Button-3>",self.menu)
        self.menu_ui=tk.Menu(self.root,tearoff=0)
        self.menu_ui.add_command(label="Open job stash",command=self.open_stash)
        self.menu_ui.add_command(label="Check cloud feed",command=self.sync)
        self.menu_ui.add_command(label="Open GitHub jobs",command=lambda:webbrowser.open("https://github.com/joestella99/Frank/blob/main/data/jobs.json"))
        self.menu_ui.add_command(label="Pause / resume walking",command=self.toggle_walk)
        self.menu_ui.add_command(label="Mute / unmute bark",command=self.toggle_sound)
        self.menu_ui.add_separator()
        self.menu_ui.add_command(label="Quit Frank",command=self.root.destroy)
        self.root.after(400,self.animate)
        self.root.after(1000,self.poll)
        self.root.after(1200,self.sync)
        self.root.after(700,self.sync_again)

    def make_sprite(self):
        file=BASE/"assets"/"frank.png"
        encoded=BASE/"assets"/"frank.png.b64"
        if file.exists():im=Image.open(file).convert("RGBA")
        elif encoded.exists():im=Image.open(io.BytesIO(base64.b64decode(encoded.read_text().strip()))).convert("RGBA")
        else:
            im=Image.new("RGBA",(120,150),(0,0,0,0))
            from PIL import ImageDraw
            d=ImageDraw.Draw(im)
            d.ellipse((17,42,100,143),fill="#282222")
            d.polygon([(24,54),(14,7),(54,38)],fill="#302827")
            d.polygon([(70,37),(101,5),(102,66)],fill="#302827")
            d.ellipse((38,48,91,105),fill="#423634")
            d.ellipse((50,68,57,75),fill=GOLD);d.ellipse((76,68,83,75),fill=GOLD)
            d.ellipse((59,85,74,97),fill="black")
        bounds=im.getbbox()
        if bounds:im=im.crop(bounds)
        im.thumbnail((61,79),Image.Resampling.LANCZOS)
        return im

    def place(self):
        self.root.geometry("+%d+%d"%(int(self.x),int(self.y)))

    def mouse_down(self,e):
        self.drag=(e.x_root,e.y_root,self.x,self.y)
    def mouse_move(self,e):
        if self.drag:
            a,b,c,d=self.drag
            self.x=c+e.x_root-a;self.y=d+e.y_root-b
            self.place()
    def mouse_up(self,e):
        if self.drag:
            a,b,_,_=self.drag
            if abs(a-e.x_root)+abs(b-e.y_root)<5:self.say("Woof! Double-click for my job stash.")
            self.drag=None
            self.floor=min(self.root.winfo_screenheight()-self.height,max(0,self.y))

    def menu(self,e):
        try:self.menu_ui.tk_popup(e.x_root,e.y_root)
        finally:self.menu_ui.grab_release()

    def toggle_walk(self):
        self.running=not self.running
        self.motion.walking_enabled=self.running
    def toggle_sound(self):
        self.sound=not self.sound

    def animate(self):
        # Frame-by-frame motion, never a pre-baked left/right slide.
        if self.drag is None:
            self.x=self.motion.step(self.x,self.root.winfo_screenwidth()-self.width)
            self.direction=self.motion.direction
            self.y=self.floor
        self.current_image=ImageTk.PhotoImage(self.motion.frame())
        self.label.configure(image=self.current_image)
        self.place()
        self.root.after(FRAME_MS,self.animate)

    def say(self,msg):
        if self.bubble:
            try:self.bubble.destroy()
            except tk.TclError:pass
        bubble=tk.Toplevel(self.root)
        self.bubble=bubble
        bubble.overrideredirect(True);bubble.attributes("-topmost",True)
        tk.Label(bubble,text=msg,bg="#242323",fg=GOLD,padx=12,pady=8,
                 wraplength=245,font=("Segoe UI",10,"bold")).pack()
        bubble.update_idletasks()
        x=max(5,min(self.root.winfo_screenwidth()-bubble.winfo_width()-5,int(self.x)-45))
        y=max(5,int(self.y)-bubble.winfo_height()+7)
        bubble.geometry("+%d+%d"%(x,y))
        def close():
            if self.bubble is bubble:
                try:bubble.destroy()
                except tk.TclError:pass
                self.bubble=None
        self.root.after(5200,close)

    def bark(self):
        if self.sound:
            if sys.platform=="win32":
                try:
                    import winsound
                    winsound.PlaySound(str(self.bark_file),winsound.SND_FILENAME|winsound.SND_ASYNC) if self.bark_file else winsound.MessageBeep()
                except Exception:pass
            else:self.root.bell()

    def sync(self):
        def worker():
            try:self.messages.put(("jobs",read_feed()))
            except Exception as e:self.messages.put(("error",str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def sync_again(self):
        self.root.after(5*60*1000,self.sync)
        self.root.after(5*60*1000,self.sync_again)

    def poll(self):
        try:
            while True:
                tag,value=self.messages.get_nowait()
                if tag=="jobs":
                    live=[j for j in value if j.get("active",True)]
                    # Your starred applications remain in the local stash even if removed from the public feed.
                    archived=[j for jid,j in self.state["saved_jobs"].items() if jid not in {x["id"] for x in live}]
                    self.jobs=live+archived
                    new=[j for j in live if j["id"] not in self.state["seen"]]
                    self.state["seen"]=list(set(self.state["seen"]) | {j["id"] for j in self.jobs})
                    save_state(self.state)
                    if new:
                        top=max(new,key=lambda j:j.get("score",0))
                        self.motion.found_job()
                        self.bark()
                        self.say("I fetched %d new match%s! %s at %s"%(len(new),"es" if len(new)!=1 else "",top["title"],top["company"]))
                    if self.dashboard and self.dashboard.winfo_exists():self.refresh()
                else:print("Frank sync failed:",value,file=sys.stderr)
        except queue.Empty:pass
        self.root.after(500,self.poll)

    def open_stash(self):
        if self.dashboard and self.dashboard.winfo_exists():
            self.dashboard.lift();return
        win=tk.Toplevel(self.root)
        self.dashboard=win
        win.title("Frank's job stash")
        win.geometry("940x510")
        win.configure(bg="#171b1b")
        top=tk.Frame(win,bg="#171b1b");top.pack(fill="x",padx=15,pady=10)
        tk.Label(top,text="🐾 FRANK'S FINDS",bg="#171b1b",fg=GOLD,font=("Segoe UI",17,"bold")).pack(side="left")
        tk.Button(top,text="Check for jobs",command=self.sync).pack(side="right")
        cols=("score","company","title","location","status")
        self.table=ttk.Treeview(win,columns=cols,show="headings")
        for col,width in [("score",65),("company",150),("title",320),("location",235),("status",110)]:
            self.table.heading(col,text=col.title())
            self.table.column(col,width=width,stretch=col=="title")
        self.table.pack(fill="both",expand=True,padx=15)
        controls=tk.Frame(win,bg="#171b1b");controls.pack(fill="x",padx=15,pady=12)
        for title,action in (("Open application",self.open_job),("Save for later",lambda:self.set_status("saved")),
                             ("Applied",lambda:self.set_status("applied")),("Ignore",lambda:self.set_status("ignored"))):
            tk.Button(controls,text=title,command=action,padx=8,pady=6).pack(side="left",padx=5)
        self.refresh()

    def selected(self):
        if not self.dashboard or not self.dashboard.winfo_exists():return None
        rows=self.table.selection()
        if not rows:return None
        return next((j for j in self.jobs if j["id"]==rows[0]),None)

    def open_job(self):
        j=self.selected()
        if j:webbrowser.open(j["url"])

    def set_status(self,status):
        j=self.selected()
        if j:
            self.state["statuses"][j["id"]]=status
            if status in ("saved","applied"):
                self.state["saved_jobs"][j["id"]]=j
            else:
                self.state["saved_jobs"].pop(j["id"],None)
            save_state(self.state)
            self.refresh()

    def refresh(self):
        if not self.dashboard or not self.dashboard.winfo_exists():return
        selected=self.table.selection()
        self.table.delete(*self.table.get_children())
        for j in sorted(self.jobs,key=lambda x:(x.get("score",0),x.get("first_seen","")),reverse=True):
            self.table.insert("", "end",iid=j["id"],values=(
                j.get("score",0),j["company"],j["title"],j.get("location",""),
                self.state["statuses"].get(j["id"],"new")))
        for key in selected:
            if self.table.exists(key):self.table.selection_set(key)

    def run(self):self.root.mainloop()

if __name__=="__main__":Pet().run()
