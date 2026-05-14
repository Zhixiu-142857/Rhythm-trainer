#This is a game of guessing a number 
import random
correct_digit_correct_place = 0
correct_digit_incorrect_place = 0
Guesses = 0
#Telling the person how to play
print("This is a game where the computer selects a number from 000 ~ 999 and you try to guess it.")
print("In every number the computer selects, the digits will all be distinct.")
print("You will have as many attempts as you need to guess the number, but try to do it in as less as you can.")
print("Every number you guess, you will be told:")
print("1. How many digits are correct and in the correct place;")
print("2. How many digits are correct but in an incorrect place.")
print("Remember, zero can be the first digit in this game.")
print("Have fun!")
#Selecting the number
numbers_zero_to_nine = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
first_digit = random.choice(numbers_zero_to_nine)
numbers_zero_to_nine.remove(first_digit)
second_digit = random.choice(numbers_zero_to_nine)
numbers_zero_to_nine.remove(second_digit)
third_digit = random.choice(numbers_zero_to_nine)
The_number = str(first_digit) + str(second_digit) + str(third_digit)
#Guessing the number
print("When guessing, remember to enter a three digit number where no digits repeat and where zero can be the first digit.")
print("If you want to quit, enter '000' (Without the quotes).")
Player_guess_string = "000" 
Player_won = False  
while Player_guess_string != The_number:
    Player_guess_string = input("Please enter your guess: ")
    if Player_guess_string == "000":
        print("You have quit the game.")
        print(f"The number was {The_number}.")
        break 
    if not (Player_guess_string.isdigit() and len(Player_guess_string) == 3 and len(set(Player_guess_string)) == 3):
        #Error message
        print(f"Your guess, {Player_guess_string}, is not a valid number because:")
        if not Player_guess_string.isdigit():
            if len(Player_guess_string) != 3:
                print("it is not a number, and")
            if len(Player_guess_string) == 3:
                print("it is not a number.")
        if len(Player_guess_string) <= 2:
            print("it has less than 3 digits.")
        if len(Player_guess_string) >= 4:
            print("it has more than 3 digits.")
        continue
    Guesses += 1
    for i in range(3):
        if Player_guess_string[i] == str(The_number)[i]:
            correct_digit_correct_place += 1
        elif Player_guess_string[i] in str(The_number):
            correct_digit_incorrect_place += 1
    #informing the player
    if correct_digit_correct_place == 1:
        print("In your guess, 1 digit is correct and in the correct place.")
    else:
        print(f"In your guess, {correct_digit_correct_place} digits are correct and in the correct place.")
    if correct_digit_incorrect_place == 1:
        print("In your guess, 1 digit is correct and but in the incorrect place.")
    else:
        print(f"In your guess, {correct_digit_incorrect_place} digits are correct but in the incorrect place.")
    correct_digit_correct_place = 0
    correct_digit_incorrect_place = 0
    if Player_guess_string == The_number:
        Player_won = True
if Player_won:
    print(f"You have guessed the number correctly in {Guesses} guesses!")
