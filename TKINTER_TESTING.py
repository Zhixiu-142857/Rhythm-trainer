import tkinter as tk
import time

window = tk.Tk()
window.title("Animated Canvas")

canvas = tk.Canvas(window, width=400, height=300, bg="white")
canvas.pack()

# Create a moving circle
circle = canvas.create_oval(50, 150, 100, 200, fill="blue")

def animate():
    canvas.move(circle, 2, 0)  # Move right
    if canvas.coords(circle)[0] > 400:  # If off screen
        canvas.coords(circle, 50, 150, 100, 200)  # Reset position
    window.after(50, animate)  # Call again in 50ms

animate()
window.mainloop()
