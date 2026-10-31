import tkinter as tk
from tkinter import ttk, messagebox
import math, random, time, json
from pathlib import Path

BASE = Path(__file__).resolve().parent
CFG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))

class PortBotTest:
    """Полностью автономный бот в изолированном симуляторе; не взаимодействует с GTA/RAGE MP."""
    def __init__(self, root):
        self.root = root
        root.title("PORT BOT PRO — автономный тестовый симулятор")
        root.geometry("1120x790")
        root.configure(bg="#0d1420")
        self.running = False
        self.paused = False
        self.boxes = 0
        self.earned = 0.0
        self.errors = 0
        self.started = None
        self.phase = "idle"
        self.player = [90.0, 330.0]
        self.box = [random.randint(180, 840), random.randint(100, 590)]
        self.delivery = [random.randint(180, 840), random.randint(100, 590)]
        self.marker_x = 0.0
        self.marker_dir = 1
        self.minigame_ticks = 0
        self.log_lines = []
        self.build_ui()
        self.draw_world()
        self.log("Готово. Это автономный симулятор: управление выполняется внутри тестовой сцены.")

    def build_ui(self):
        top = tk.Frame(self.root, bg="#172437", padx=18, pady=14)
        top.pack(fill="x")
        tk.Label(top, text="PORT BOT PRO", bg="#172437", fg="#f2f6ff",
                 font=("Segoe UI", 21, "bold")).pack(side="left")
        tk.Label(top, text="AUTONOMOUS TEST ENVIRONMENT", bg="#172437", fg="#91a8c5",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=18, pady=(8,0))
        self.status = tk.Label(top, text="● ОСТАНОВЛЕН", bg="#172437", fg="#ffbf69",
                               font=("Segoe UI", 10, "bold"))
        self.status.pack(side="right")

        stats = tk.Frame(self.root, bg="#0d1420", padx=12, pady=12)
        stats.pack(fill="x")
        self.stats = {}
        for title, key, initial in [
            ("ДОСТАВЛЕНО", "boxes", "0"), ("ЗАРАБОТАНО", "money", "$0.00"),
            ("ОШИБКИ", "errors", "0"), ("ТЕМП", "rate", "$0.00/ч")
        ]:
            card = tk.Frame(stats, bg="#1a293c", padx=16, pady=10)
            card.pack(side="left", expand=True, fill="x", padx=5)
            tk.Label(card, text=title, bg="#1a293c", fg="#8fa6c2",
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            val = tk.Label(card, text=initial, bg="#1a293c", fg="#62e6b2",
                           font=("Segoe UI", 20, "bold"))
            val.pack(anchor="w")
            self.stats[key] = val

        middle = tk.Frame(self.root, bg="#0d1420", padx=16)
        middle.pack(fill="both", expand=True)
        left = tk.Frame(middle, bg="#0d1420")
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="ТЕСТОВАЯ СЦЕНА", bg="#0d1420", fg="#d9e5f4",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0,7))
        self.canvas = tk.Canvas(left, width=900, height=610, bg="#101c2b",
                                highlightthickness=1, highlightbackground="#2c4058")
        self.canvas.pack(fill="both", expand=True)

        side = tk.Frame(middle, bg="#172437", width=240, padx=14, pady=14)
        side.pack(side="right", fill="y", padx=(14,0))
        side.pack_propagate(False)
        tk.Label(side, text="СОСТОЯНИЕ БОТА", bg="#172437", fg="#91a8c5",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.phase_label = tk.Label(side, text="Ожидание запуска", bg="#172437",
                                    fg="#ffffff", font=("Segoe UI", 13, "bold"),
                                    wraplength=205, justify="left")
        self.phase_label.pack(anchor="w", pady=(8,18))
        tk.Label(side, text="МИНИ-ИГРА", bg="#172437", fg="#91a8c5",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.gamebar = tk.Canvas(side, width=205, height=42, bg="#0c1420",
                                 highlightthickness=0)
        self.gamebar.pack(pady=8)
        self.game_label = tk.Label(side, text="Не активна", bg="#172437",
                                   fg="#b8c9dd", wraplength=205, justify="left")
        self.game_label.pack(anchor="w")
        tk.Label(side, text="РЕЖИМ", bg="#172437", fg="#91a8c5",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(20,4))
        tk.Label(side, text="Автономный тест\nБез подключения к игре",
                 bg="#172437", fg="#b8c9dd", justify="left").pack(anchor="w")

        controls = tk.Frame(self.root, bg="#0d1420", padx=16, pady=12)
        controls.pack(fill="x")
        ttk.Button(controls, text="▶ Запустить автономный тест", command=self.start).pack(side="left", padx=4)
        ttk.Button(controls, text="Ⅱ Пауза", command=self.pause).pack(side="left", padx=4)
        ttk.Button(controls, text="■ Стоп", command=self.stop).pack(side="left", padx=4)
        ttk.Button(controls, text="Сбросить", command=self.reset).pack(side="left", padx=4)
        tk.Label(controls, text="Цикл: поиск → подход → подбор → доставка → мини-игра → повтор",
                 bg="#0d1420", fg="#8196b1", font=("Segoe UI", 9)).pack(side="right")

        logframe = tk.Frame(self.root, bg="#0d1420", padx=16, pady=(0,12))
        logframe.pack(fill="x")
        tk.Label(logframe, text="ЖУРНАЛ СОБЫТИЙ", bg="#0d1420", fg="#d9e5f4",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.logbox = tk.Text(logframe, height=6, bg="#080e17", fg="#b8c9dd",
                              insertbackground="white", relief="flat",
                              font=("Consolas", 9), state="disabled")
        self.logbox.pack(fill="x", pady=5)

    def log(self, message):
        stamp = time.strftime("%H:%M:%S")
        self.logbox.configure(state="normal")
        self.logbox.insert("end", f"[{stamp}] {message}\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def start(self):
        if self.running:
            self.paused = False
            return
        self.running, self.paused = True, False
        self.started = time.time()
        self.phase = "to_box"
        self.status.config(text="● РАБОТАЕТ", fg="#62e6b2")
        self.log("Автономный агент запущен.")
        self.tick()

    def pause(self):
        if self.running:
            self.paused = not self.paused
            self.status.config(text="Ⅱ ПАУЗА" if self.paused else "● РАБОТАЕТ",
                               fg="#ffbf69" if self.paused else "#62e6b2")
            self.log("Пауза." if self.paused else "Продолжение работы.")

    def stop(self):
        self.running = False
        self.paused = False
        self.status.config(text="● ОСТАНОВЛЕН", fg="#ffbf69")
        self.phase = "idle"
        self.phase_label.config(text="Остановлен")
        self.log("Работа остановлена.")
        self.draw_world()

    def reset(self):
        self.stop()
        self.boxes, self.earned, self.errors = 0, 0.0, 0
        self.player = [90.0, 330.0]
        self.new_targets()
        self.update_stats()
        self.log("Статистика и сцена сброшены.")

    def new_targets(self):
        self.box = [random.randint(180, 840), random.randint(90, 590)]
        self.delivery = [random.randint(180, 840), random.randint(90, 590)]

    def move_toward(self, target, speed=4.2):
        dx, dy = target[0]-self.player[0], target[1]-self.player[1]
        d = math.hypot(dx, dy)
        if d <= speed:
            self.player = [float(target[0]), float(target[1])]
            return True
        self.player[0] += dx/d*speed
        self.player[1] += dy/d*speed
        return False

    def tick(self):
        if not self.running:
            return
        if not self.paused:
            if self.phase == "to_box":
                self.phase_label.config(text="Ищу и подхожу к коробке")
                if self.move_toward(self.box):
                    self.phase = "pickup"
                    self.log("Коробка найдена. Подбор выполнен.")
            elif self.phase == "pickup":
                self.phase = "to_delivery"
                self.log("Коробка подобрана. Направляюсь к точке сдачи.")
            elif self.phase == "to_delivery":
                self.phase_label.config(text="Доставляю коробку")
                if self.move_toward(self.delivery):
                    self.phase = "minigame"
                    self.marker_x = random.random()
                    self.marker_dir = random.choice([-1,1])
                    self.minigame_ticks = 0
                    self.log("Достигнута точка сдачи. Запущена мини-игра.")
            elif self.phase == "minigame":
                self.phase_label.config(text="Прохожу мини-игру")
                self.marker_x += self.marker_dir * 0.018
                if self.marker_x >= 1 or self.marker_x <= 0:
                    self.marker_dir *= -1
                    self.marker_x = min(1,max(0,self.marker_x))
                self.minigame_ticks += 1
                self.draw_minigame()
                target = float(CFG["minigame"]["target_x"])
                if abs(self.marker_x-target) <= CFG["minigame"]["tolerance"]:
                    self.boxes += 1
                    self.earned += CFG["simulation"]["delivery_reward"]
                    self.log(f"Успешная сдача! Начислено ${CFG['simulation']['delivery_reward']:.2f}.")
                    self.update_stats()
                    self.new_targets()
                    self.phase = "to_box"
                elif self.minigame_ticks > 240:
                    self.errors += 1
                    self.log("Тестовая мини-игра не пройдена. Повторяю доставку.")
                    self.update_stats()
                    self.phase = "to_delivery"
            self.draw_world()
            self.update_stats()
        self.root.after(CFG["simulation"]["move_interval_ms"], self.tick)

    def update_stats(self):
        self.stats["boxes"].config(text=str(self.boxes))
        self.stats["money"].config(text=f"${self.earned:.2f}")
        self.stats["errors"].config(text=str(self.errors))
        elapsed = max(1, time.time()-(self.started or time.time()))
        self.stats["rate"].config(text=f"${self.earned*3600/elapsed:.2f}/ч")

    def draw_minigame(self):
        c=self.gamebar; c.delete("all")
        c.create_rectangle(8,15,197,27,fill="#31445d",outline="")
        tx=8+189*CFG["minigame"]["target_x"]
        c.create_rectangle(tx-5,10,tx+5,32,fill="#f4f7ff",outline="")
        mx=8+189*self.marker_x
        c.create_oval(mx-6,12,mx+6,30,fill="#55e39c",outline="")
        self.game_label.config(text="Маркер движется. Агент ожидает попадания в целевую зону.",fg="#62e6b2")

    def draw_world(self):
        c=self.canvas; c.delete("all")
        w=max(900,c.winfo_width()); h=max(610,c.winfo_height())
        for x in range(0,w,40): c.create_line(x,0,x,h,fill="#1b2a3d")
        for y in range(0,h,40): c.create_line(0,y,w,y,fill="#1b2a3d")
        c.create_text(18,16,anchor="nw",text="СИМУЛЯЦИЯ МАРШРУТА",fill="#8097b3",font=("Segoe UI",9,"bold"))
        bx,by=self.box; dx,dy=self.delivery; px,py=self.player
        c.create_rectangle(bx-13,by-13,bx+13,by+13,fill="#f0b64f",outline="#ffe0a0",width=2)
        c.create_text(bx,by+24,text="КОРОБКА",fill="#f0c875",font=("Segoe UI",8,"bold"))
        c.create_oval(dx-15,dy-15,dx+15,dy+15,fill="#2a9d83",outline="#76f0c6",width=2)
        c.create_text(dx,dy+25,text="СДАЧА",fill="#76f0c6",font=("Segoe UI",8,"bold"))
        c.create_line(px,py,bx,by,fill="#52677f",dash=(3,5))
        c.create_oval(px-12,py-12,px+12,py+12,fill="#5ba6ff",outline="#d6eaff",width=2)
        c.create_text(px,py-24,text="BOT",fill="#a8d0ff",font=("Segoe UI",8,"bold"))
        if self.phase=="to_delivery":
            c.create_line(px,py,dx,dy,fill="#62e6b2",width=2,dash=(6,4))

if __name__ == "__main__":
    root = tk.Tk()
    app = PortBotTest(root)
    root.mainloop()
