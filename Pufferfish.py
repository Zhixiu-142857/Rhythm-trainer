import tkinter as tk 
import random
import math
import time
import uuid
window = tk.Tk()
window.title("Pufferfish")
window.geometry("600x600")
canvas = tk.Canvas(window, width=600, height=600, bg="aliceblue")
canvas.pack()
mousex = 0
mousey = 0
list_idxysize = []
game_running = True
MAX_FISH = 51
money = 0
tax_timer = 30
game_timer = 120
timer_running = True
game_starting = False
restart_button = None
def start_game():
    global game_starting
    game_starting = True
start_button = tk.Button(window, text="Start Game", command=start_game)
start_button.pack(side="top", padx=10, pady=5, anchor="nw")
canvas.create_text(300, 270, text="Click the start button to start the game", font=("Arial", 24), fill="black")
canvas.create_text(300, 320, text="You have 2 minutes to catch (click on) as many pufferfish as you can", font=("Arial", 14), fill="black")
canvas.create_text(300, 340, text="Each pufferfish is worth a random amount of money", font=("Arial", 14), fill="black")
canvas.create_text(300, 360, text="The game will end when the time runs out", font=("Arial", 14), fill="black")
canvas.create_text(300, 380, text="You will be taxed 10 percent of your money every 30 seconds", font=("Arial", 14), fill="black")
canvas.create_text(300, 400, text="If you have at least $1000,", font=("Arial", 14), fill="black")
canvas.create_text(300, 420, text="press the space button to use your money to buy an extra 30 seconds", font=("Arial", 14), fill="black")
canvas.create_text(300, 470, text="Good luck!", font=("Arial", 24), fill="black")
def wait_for_start():
    if not game_starting:
        window.after(100, wait_for_start)
    else:
        canvas.delete("all")
        start_button.destroy()
        global labels
        labels = tk.Label(window, text=f"Time: {game_timer}, Money: ${money:.2f}", font=("Arial", 16), bg="white")
        labels.pack(side="top", padx=10, pady=5, anchor="ne")
        def update_labels():
            labels.config(text=f"Time: {game_timer}, Money: ${money:.2f}")
        def get_fish_info(fish_tag):
            for a in list_idxysize:
                if a[0] == fish_tag:
                    return a
            return None
        def fish_overlapping_fish(fish_tag):
            fish_info = get_fish_info(fish_tag)
            if fish_info is None:
                return False
            x1, y1, size1 = fish_info[1], fish_info[2], fish_info[3]
            radius1 = size1 * 0.5
            for a in list_idxysize:
                if a[0] == fish_tag:
                    continue
                x2, y2, size2 = a[1], a[2], a[3]
                radius2 = size2 * 0.5
                distance = math.hypot(x1 - x2, y1 - y2)
                if distance < (radius1 + radius2):
                    return True
            return False
        def delete_pufferfish(fish_tag):
            canvas.delete(fish_tag)
            for a in list_idxysize:
                if a[0] == fish_tag:
                    list_idxysize.remove(a)
                    break
        def tax():
            global money
            money = math.ceil(money * 0.9)
            labels.config(text=f"Time: {game_timer}, Money: ${money:.2f}")
        def update_game_timer():
            global game_timer, timer_running, game_running
            if timer_running and game_timer > 0:
                game_timer -= 1
                labels.config(text=f"Time: {game_timer}, Money: ${money:.2f}")
                window.after(1000, update_game_timer)
            elif game_timer <= 0:
                labels.config(text="Time's up!")
                game_running = False
                timer_running = False
                window.after(1000, lambda: canvas.delete("all"))
                window.after(1000, lambda: canvas.create_text(300, 300, text=f"Time's up! You have ${money:.2f}.", font=("Arial", 24), fill="red"))
                def restart_game2():
                    global game_starting, game_timer, money, labels, start_button, restart_button, game_running, timer_running
                    game_starting = False
                    game_timer = 120
                    money = 0
                    game_running = True
                    timer_running = True
                    labels.destroy()
                    canvas.delete("all")
                    restart_button.destroy()
                    start_button = tk.Button(window, text="Start Game", command=start_game)
                    start_button.pack(side="top", padx=10, pady=5, anchor="nw")
                    canvas.create_text(300, 270, text="Click the start button to start the game", font=("Arial", 24), fill="black")
                    canvas.create_text(300, 320, text="You have 2 minutes to catch (click on) as many pufferfish as you can", font=("Arial", 14), fill="black")
                    canvas.create_text(300, 340, text="Each pufferfish is worth a random amount of money", font=("Arial", 14), fill="black")
                    canvas.create_text(300, 360, text="The game will end when the time runs out", font=("Arial", 14), fill="black")
                    canvas.create_text(300, 380, text="You will be taxed 10 percent of your money every 30 seconds", font=("Arial", 14), fill="black")
                    canvas.create_text(300, 400, text="If you have at least $1000,", font=("Arial", 14), fill="black")
                    canvas.create_text(300, 420, text="press the space button to use your money to buy an extra 30 seconds", font=("Arial", 14), fill="black")
                    canvas.create_text(300, 470, text="Good luck!", font=("Arial", 24), fill="black")
                    window.after(1, wait_for_start)
                global restart_button
                restart_button = tk.Button(window, text="Restart Game", command=restart_game2)
                restart_button.pack(side="top", padx=10, pady=5, anchor="nw")
        def update_tax_timer():
            global tax_timer
            if tax_timer > 0:
                tax_timer -= 1
                window.after(1000, update_tax_timer)
            elif tax_timer <= 0:
                tax()
                tax_timer = 30  
                window.after(1000, update_tax_timer)
        def clicked_fish(event):
            global mousex, mousey, money
            mousex = event.x
            mousey = event.y
            for a in list_idxysize[:]:
                x1, y1, size1 = a[1], a[2], a[3]
                radius1 = size1 * 0.5
                distance = math.hypot(mousex - x1, mousey - y1)
                if distance < radius1:
                    delete_pufferfish(a[0])
                    money += a[3]/math.ceil(random.randint(1, 3)*random.randint(1, 3)*random.randint(1, 3)) 
                    labels.config(text=f"Time: {game_timer}, Money: ${money:.2f}")
                    break
        canvas.bind("<Button-1>", clicked_fish)
        def buy_time(event=None):
            global money, game_timer
            if money >= 1000:
                money -= 1000
                game_timer += 30
                update_labels()
        window.bind("<space>", buy_time)
        def create_pufferfish():
            global list_idxysize
            if len(list_idxysize) >= MAX_FISH:
                return
            attempts = 0
            while attempts < 25:
                size = random.randint(30, 60)
                color1 = random.choice(["salmon", "darkorange", "orangered", "coral", "tan", "indianred", "goldenrod", "orange", "salmon", "salmon", "salmon", "orange", "salmon", "orange"])
                color2 = random.choice(["white", "snow", "seashell", "ivory", "honeydew", "mintcream", "aliceblue", "ghostwhite", "linen", "whitesmoke", "gray", "lightgray", "gray", "snow", "white", "white", "white"])
                x = random.randint(size, 600 - size)
                y = random.randint(size, 600 - size)
                fish_tag = str(uuid.uuid4())
                canvas.create_oval(x - round(3*size/4), y - round(size/2), x + round(size/4), y + round(size/2), fill=color1, outline=color1, tags=(fish_tag,))
                canvas.create_polygon(x + round(size/4), y, x + round(size/2), y + round(size/2), x + round(size/2), y - round(size/2), fill=color1, outline=color1, tags=(fish_tag,))
                canvas.create_text(x - round(size/8), y, text="Pufferfish!", font=("Arial", round(size/4)), fill=color2, tags=(fish_tag,))
                list_idxysize.append([fish_tag, x, y, size])
                if not fish_overlapping_fish(fish_tag):
                    break
                else:
                    delete_pufferfish(fish_tag)
                    attempts += 1
        def main_loop(): 
            if game_running:
                create_pufferfish()
                update_labels()
                window.after(random.randint(200, 1000), main_loop)
        window.after(1, update_game_timer)
        window.after(1, update_tax_timer)
        window.after(1, main_loop)
wait_for_start()
window.mainloop()