import tkinter as tk
import random
import math
import time
import uuid
window = tk.Tk()
window.title("Airplane Game")
window.geometry("800x600")
window.attributes("-fullscreen", True)
canvas = tk.Canvas(window, width=800, height=600, bg="paleturquoise")
canvas.pack()
list_airplanelevelcolor = ["ivory", "skyblue2", "lightgreen", "lightcoral", "pink", "tan", "lightgray", "gray", "black"]
list_airplanexyidlevel = []
list_bulletidxy = []
game_level = 0
timer = 0
last_spawn_time = 0
score = 0
game_starting = False
restarting = False
game_running = True
game_over = False
restart_button = None
labels = tk.Label(window, text=f"Time: {timer} seconds, Score: {score}, Level: 1", font=("Arial", 16), bg="white")
labels.pack(side="top", padx=10, pady=5, anchor="ne")
to_removea = []
to_removeb = []
our_airplane_y = 300
def update_timer():
    global timer, labels, game_level, game_running
    if not game_running:
        return
    timer += 1
    if 0 < timer < 1000:
        game_level = 1
    elif 1000 < timer < 2000:
        game_level = 2
    elif 2000 < timer < 4000:
        game_level = 3
    elif 4000 < timer < 6000:
        game_level = 4
    elif 6000 < timer < 10000:
        game_level = 5
    elif 10000 < timer < 14000:
        game_level = 6
    elif 14000 < timer < 18000:
        game_level = 7
    elif 18000 < timer < 24000:
        game_level = 8
    elif 24000 < timer:
        game_level = 9
    if round(timer/40) == 1:
        labels.config(text=f"Time:{timer/40 : .0f} second, Score: {score}, Level: {game_level}")
    else:
        labels.config(text=f"Time:{timer/40 : .0f} seconds, Score: {score}, Level: {game_level}")
    window.after(25, update_timer)
def move_our_airplane_up(event):
    global our_airplane_y
    canvas.move("our_airplane", 0, -10)
    our_airplane_y -= 10
window.bind("<Up>", move_our_airplane_up)
def move_our_airplane_down(event):
    global our_airplane_y
    canvas.move("our_airplane", 0, 10)
    our_airplane_y += 10
window.bind("<Down>", move_our_airplane_down)
def start_game():
    global game_starting
    game_starting = True
canvas.create_text(400, 270, text="Click the start button to start the game", font=("Arial", 24), fill="black")
canvas.create_text(400, 320, text="Shoot down as many enemy airplanes as you can!", font=("Arial", 24), fill="black")
start_button = tk.Button(window, text="Start Game", command=start_game)
start_button.pack(side="top", padx=10, pady=5, anchor="nw")
def create_bullet():
    global our_airplane_y, game_running
    if not game_running:
        return
    bullet_id = uuid.uuid4()
    canvas.create_oval(690, our_airplane_y - 5, 700, our_airplane_y + 5, fill="brown", outline="brown", tags=bullet_id)
    list_bulletidxy.append([bullet_id, 695, our_airplane_y])
    window.after(200, create_bullet)
def move_bullet():
    for i in range(len(list_bulletidxy)):
        bullet_id, x, y = list_bulletidxy[i]
        canvas.move(bullet_id, -1, 0)
        list_bulletidxy[i][1] = x - 1
def create_airplane(x, y, level):
    airplane_id = uuid.uuid4()
    color = list_airplanelevelcolor[level]
    canvas.create_polygon(x + 30, y, x, y + 20, x, y - 20, fill=color, outline=color, tag=airplane_id)
    canvas.create_polygon(x + 45, y, x + 15, y + 10, x + 15, y - 10, fill=color, outline=color, tag=airplane_id)
    canvas.create_polygon(x + 70, y, x + 30, y + 5, x + 30, y - 5, fill=color, outline=color, tag=airplane_id)
    if level == 7 or level == 8:
        canvas.create_text(x + 20, y, text=f"Level {level + 1}", font=("Arial", 10), tag=airplane_id, fill="white")
    else:
        canvas.create_text(x + 20, y, text=f"Level {level + 1}", font=("Arial", 10), tag=airplane_id)
    list_airplanexyidlevel.append([x + 70, y, airplane_id, level])
def move_airplane():
    for i in range(len(list_airplanexyidlevel)):
        x, y, airplane_id, level = list_airplanexyidlevel[i]
        canvas.move(airplane_id, 1, 0)
        list_airplanexyidlevel[i][0] = x + 1 
def game_lost():
    global restarting, game_running, game_over, restart_button
    if game_over:
        return
    game_running = False
    game_over = True
    canvas.delete("all")
    canvas.create_text(400, 270, text="Game Over", font=("Arial", 24))
    canvas.create_text(400, 320, text=f"You scored {score} points", font=("Arial", 16))
    canvas.create_text(400, 340, text=f"You survived for{timer/40 : .0f} seconds, and you were on level {game_level}", font=("Arial", 16))
    canvas.create_text(400, 360, text="Want to play again? Press the restart button", font=("Arial", 16))
    restarting = True
    restart_button = tk.Button(window, text="Restart Game", command=restart_game)
    restart_button.pack(side="top", padx=10, pady=5, anchor="nw")
def restart_game():
    global score, timer, game_level, game_running, game_over, restarting, list_airplanexyidlevel, list_bulletidxy, restart_button, our_airplane_y
    score = 0
    timer = 0
    game_level = 0
    game_running = True
    game_over = False
    restarting = False
    list_airplanexyidlevel.clear()
    list_bulletidxy.clear()
    canvas.delete("all")
    if restart_button:
        restart_button.destroy()
        restart_button = None
    labels.config(text=f"Time: {timer/40 : .0f} seconds, Score: {score}, Level: {game_level}")
    our_airplane_y = 300
    canvas.create_rectangle(750, 275, 800, 325, fill="black", outline="black", tags="our_airplane")
    canvas.create_polygon(750, 275, 750, 325, 700, 300, fill="black", outline="black", tags="our_airplane")
    canvas.create_text(750, 300, text="Our Airplane", font=("Arial", 10), tags="our_airplane", fill="white")
    update_timer()
    window.after(1, main_loop)
    window.after(1, create_bullet)
def del_outofbounds_airplane_plus_cleanup():
    global to_removea, game_over
    to_removea.clear() 
    for x, y, airplane_id, level in list_airplanexyidlevel:
        if x > 800:
            canvas.delete(airplane_id)
            to_removea.append([x, y, airplane_id, level])
            if not game_over:
                window.after(100, game_lost)
    for item in to_removea:
        if item in list_airplanexyidlevel: 
            list_airplanexyidlevel.remove(item)
def del_outofbounds_bullet_plus_cleanup():
    global to_removeb
    to_removeb.clear() 
    for bullet_id, x, y in list_bulletidxy:
        if x < 0:
            canvas.delete(bullet_id)
            to_removeb.append([bullet_id, x, y])
    for item in to_removeb:
        if item in list_bulletidxy: 
            list_bulletidxy.remove(item)
def collision_bullet_airplane():
    global list_airplanexyidlevel, list_bulletidxy, to_removea, to_removeb, score
    to_removea.clear()
    to_removeb.clear()
    for bullet_id, xb, yb in list_bulletidxy:
        for xa, ya, airplane_id, level in list_airplanexyidlevel:
            airplane_left = xa - 70
            airplane_right = xa
            airplane_top = ya - 20
            airplane_bottom = ya + 20
            if (airplane_left <= xb <= airplane_right and 
                airplane_top <= yb <= airplane_bottom):
                if level > 0:
                    level -= 1
                    score += 5
                    color = list_airplanelevelcolor[level]
                    canvas.delete(airplane_id)
                    canvas.create_polygon(xa - 40, ya, xa - 70, ya + 20, xa - 70, ya - 20, fill=color, outline=color, tag=airplane_id)
                    canvas.create_polygon(xa - 25, ya, xa - 55, ya + 10, xa - 55, ya - 10, fill=color, outline=color, tag=airplane_id)
                    canvas.create_polygon(xa, ya, xa - 40, ya + 5, xa - 40, ya - 5, fill=color, outline=color, tag=airplane_id)
                    if level == 7 or level == 8:
                        canvas.create_text(xa - 50, ya, text=f"Level {level + 1}", font=("Arial", 10), tag=airplane_id, fill="white")
                    else:
                        canvas.create_text(xa - 50, ya, text=f"Level {level + 1}", font=("Arial", 10), tag=airplane_id)
                    for i in range(len(list_airplanexyidlevel)):
                        if list_airplanexyidlevel[i][2] == airplane_id:
                            list_airplanexyidlevel[i][3] = level
                            break
                    canvas.delete(bullet_id)
                    to_removeb.append([bullet_id, xb, yb])
                    break  
                else:
                    canvas.delete(airplane_id)
                    score += 10
                    to_removea.append([xa, ya, airplane_id, level])
                    canvas.delete(bullet_id)
                    to_removeb.append([bullet_id, xb, yb])
                    break
    for item in to_removea:
        if item in list_airplanexyidlevel:
            list_airplanexyidlevel.remove(item)
    for item in to_removeb:
        if item in list_bulletidxy:
            list_bulletidxy.remove(item)
def create_airplane_part2():
    global last_spawn_time
    if timer - last_spawn_time < 10:
        return
    if timer % 100 == 0 and random.random() > 0.5 and 0 < timer < 1000:
        create_airplane(0, random.randint(100, 500), random.randint(0, 1))
        last_spawn_time = timer
    elif timer % 100 == 0 and random.random() > 0.25 and 1000 < timer < 2000:
        create_airplane(0, random.randint(100, 500), random.randint(0, 1))
        last_spawn_time = timer
    elif timer % 60 == 0 and random.random() > 0.25 and 2000 < timer < 4000:
        create_airplane(0, random.randint(100, 500), random.randint(0, 2))
        last_spawn_time = timer
    elif timer % 40 == 0 and random.random() > 0.25 and 4000 < timer < 6000:
        create_airplane(0, random.randint(100, 500), random.randint(0, 4))
        last_spawn_time = timer
    elif timer % 30 == 0 and random.random() > 0.25 and 6000 < timer < 10000:
        create_airplane(0, random.randint(100, 500), random.randint(1, 5))
        last_spawn_time = timer
    elif timer % 30 == 0 and random.random() > 0.15 and 10000 < timer < 14000:
        create_airplane(0, random.randint(100, 500), random.randint(2, 7))
        last_spawn_time = timer
    elif timer % 30 == 0 and random.random() > 0.05 and 14000 < timer < 18000:
        create_airplane(0, random.randint(100, 500), random.randint(3, 8))
        last_spawn_time = timer
    elif timer % 20 == 0 and random.random() > 0.05 and 18000 < timer < 24000:
        create_airplane(0, random.randint(100, 500), random.randint(4, 8))
        last_spawn_time = timer
    elif timer % 20 == 0 and timer > 24000:
        create_airplane(0, random.randint(100, 500), random.randint(5, 8))
        last_spawn_time = timer
def main_loop():
    global game_running
    if not game_running:
        return
    move_airplane()
    move_bullet()
    del_outofbounds_airplane_plus_cleanup()
    del_outofbounds_bullet_plus_cleanup()
    collision_bullet_airplane()
    create_airplane_part2()
    window.after(10, main_loop)
def wait_for_start():
    if not game_starting:
        window.after(100, wait_for_start)
    else:
        canvas.delete("all")
        if restarting == False:
            start_button.destroy()
        update_timer()
        window.after(1, main_loop)
        window.after(1, create_bullet)
        canvas.create_rectangle(750, 275, 800, 325, fill="black", outline="black", tags="our_airplane")
        canvas.create_polygon(750, 275, 750, 325, 700, 300, fill="black", outline="black", tags="our_airplane")
        canvas.create_text(750, 300, text="Our Airplane", font=("Arial", 10), tags="our_airplane", fill="white")
wait_for_start()
window.mainloop()