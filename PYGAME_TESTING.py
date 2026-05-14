import pygame
import sys

print("Starting Pygame test...")

# Initialize Pygame
pygame.init()

# Set up the display
width = 600
height = 400
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Pygame Graphics Test")

# Colors
WHITE = (255, 255, 255)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

print("Drawing shapes...")

# Fill the screen with white
screen.fill(WHITE)

# Draw a red rectangle
pygame.draw.rect(screen, RED, (50, 50, 100, 80))
print("Red rectangle drawn")

# Draw a blue circle
pygame.draw.circle(screen, BLUE, (300, 100), 50)
print("Blue circle drawn")

# Draw a green triangle
pygame.draw.polygon(screen, GREEN, [(200, 200), (250, 150), (300, 200)])
print("Green triangle drawn")

# Update the display
pygame.display.flip()
print("Display updated")

print("Press any key to close...")

# Game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            running = False

pygame.quit()
print("Pygame test finished") 