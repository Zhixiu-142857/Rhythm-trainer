# To be used with Game_of_guessing_a_number.py

# Constructing all possible numbers (valid secrets/guesses: 3 distinct digits)

possible_numbers = []

for i in range(1000):
    j = str(i)
    for i in range(3 - len(j)):
        j = "0" + j
    if j[0] != j[1] and j[0] != j[2] and j[1] != j[2]:
        possible_numbers.append(j)

# All valid guesses we're allowed to make (same set; never pruned)
all_guesses = possible_numbers

# Track digits we've already tried (to prefer exploring new digits)
digits_tried = set()

# Getting the most informative number (choose among all_guesses, score by splitting possible_numbers)

# Bonus for guessing a number that could still be the secret (avoids wasting a guess on 019 when 039 is similar)
STILL_POSSIBLE_BONUS = 3000  # smaller than one "new digit" (10000) so 345 still beats 034

def most_informative_number():
    global possible_numbers, digits_tried
    possible_set = set(possible_numbers)  # for O(1) lookup
    # Digits that appear in at least one remaining possible secret (e.g. after 012,345,678 → no 9)
    possible_digits = set()
    for n in possible_numbers:
        possible_digits.update(n)
    def guess_uses_only_possible_digits(num):
        return len(possible_digits) >= 3 and all(d in possible_digits for d in num)
    best_score = -1
    best_number = ""
    for number in all_guesses:
        if not guess_uses_only_possible_digits(number):
            continue  # don't guess numbers that use ruled-out digits (e.g. 769 when 9 is impossible)
        correct_numbers_correct_place = 0
        correct_numbers_incorrect_place = 0
        for number2 in possible_numbers:
            for i in range(3):
                if number[i] == number2[i]:
                    correct_numbers_correct_place += 1
                elif number[i] in number2:
                    correct_numbers_incorrect_place += 1
        info_score = correct_numbers_correct_place * 2 + correct_numbers_incorrect_place
        new_digits = sum(1 for d in number if d not in digits_tried)
        still_possible = number in possible_set
        # One new digit dominates; still_possible bonus pushes 039 ahead of 019 when close
        score = new_digits * 10000 + info_score + (STILL_POSSIBLE_BONUS if still_possible else 0)
        if score > best_score:
            best_score = score
            best_number = number
    return best_number

# Getting feedback

def is_valid_feedback(feedback_cc, feedback_ci):
    """Feedback is impossible if counts are out of range or sum > 3 (each digit counts at most once)."""
    if not (0 <= feedback_cc <= 3 and 0 <= feedback_ci <= 3):
        return False
    if feedback_cc + feedback_ci > 3:
        return False
    return True

def getting_feedback(number):
    while True:
        try:
            feedback_cc = int(input(f"My guess is {number}. How many correct numbers correct place? "))
            feedback_ci = int(input(f"My guess is {number}. How many correct numbers incorrect place? "))
        except ValueError:
            print("Please enter numbers only. Try again.")
            continue
        if not is_valid_feedback(feedback_cc, feedback_ci):
            print("That feedback is impossible (e.g. correct+incorrect can't exceed 3; if all 3 are correct place, incorrect must be 0). Please re-enter.")
            continue
        return feedback_cc, feedback_ci

# Updating possible numbers

def update_possible_numbers(number, feedback_cc, feedback_ci):
    global possible_numbers
    to_keep = []
    for number2 in possible_numbers:
        correct_numbers_correct_place = 0
        correct_numbers_incorrect_place = 0
        for i in range(3):
            if number[i] == number2[i]:
                correct_numbers_correct_place += 1
            elif number[i] in number2:
                correct_numbers_incorrect_place += 1
        if correct_numbers_correct_place == feedback_cc and correct_numbers_incorrect_place == feedback_ci:
            to_keep.append(number2)
    possible_numbers = to_keep

# Main loop

def main_loop():
    guesses = 0
    global possible_numbers, digits_tried
    while len(possible_numbers) > 1:
        best_number = most_informative_number()
        guesses += 1
        feedback_cc, feedback_ci = getting_feedback(best_number)
        digits_tried.update(best_number)  # remember we've tried these digits
        update_possible_numbers(best_number, feedback_cc, feedback_ci)
    if possible_numbers:
        print(f"The number must be {possible_numbers[0]}.")
        if guesses == 1:
            print(f"It took me {guesses} guess to guess the number.")
        else:
            print(f"It took me {guesses} guesses to guess the number.")
    else:
        print("No solution found.")

main_loop()