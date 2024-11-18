import os
import time
import threading
import random
from pynput import keyboard

# Game configuration
ROWS = 10
COLUMNS = 100  # Increased for better visibility
INITIAL_ALIEN_SPEED = 0.5
MISSILE_SPEED = 0.1
MISSILE_COOLDOWN = 0.3
ALIEN_SPAWN_RATE = 1.5
LEVEL_UP_SCORE = 10
# TEMP = 0

# Game state variables
player_row = ROWS // 2  # Start at the middle row
alien_positions = [[] for _ in range(ROWS)]  # Positions of aliens in each row
missile_positions = [[] for _ in range(ROWS)]  # Allow multiple missiles per row
missile_ready = True
score = 0
missed = 0
level = 1
game_over = False
paused = False


# Locks for thread-safe operations
alien_lock = threading.Lock()
missile_lock = threading.Lock()


level_up = False  # To track if a level-up message should be displayed
level_up_lock = threading.Lock()


def display_game():
    """Display the current state of the game."""
    global level_up  # Access the level-up state variable
    clear_screen()

    # Check if we should display the level-up message
    with level_up_lock:
        if level_up:
            show_level_up_message(level)
            level_up = False  # Reset the level-up state after showing the message

    # Display regular game screen
    print(f"Score: {score}  |  Missed: {missed}/3  |  Level: {level}  |  Missile Ready: {'Yes' if missile_ready else 'No'}")
    print("=" * (COLUMNS + 10))
    for row in range(ROWS):
        line = [' '] * COLUMNS
        if row == player_row:
            line[0] = 'P'
        with missile_lock:
            for missile_pos in missile_positions[row]:
                if 0 <= missile_pos < COLUMNS:
                    line[missile_pos] = '|'
        with alien_lock:
            for pos in alien_positions[row]:
                if 0 <= pos < COLUMNS:
                    line[pos] = 'A'
        print(''.join(line))
    print("=" * (COLUMNS + 10))
    print("Controls: 'w' Up | 's' Down | 'k' Shoot | 'p' Pause | 'q' Quit")


def move_aliens():
    global missed, game_over
    last_spawn_time = time.time()
    while not game_over:
        if paused:
            time.sleep(0.1)
            continue
        time.sleep(INITIAL_ALIEN_SPEED / level)
        with alien_lock:
            for row in range(ROWS):
                new_positions = []
                for pos in alien_positions[row]:
                    new_pos = pos - 1
                    if new_pos == 0:
                        if row == player_row:
                            # Alien collides with the player
                            game_over = True
                            return
                        else:
                            missed += 1
                            if missed >= 3:
                                game_over = True
                                return
                    if new_pos > 0:
                        new_positions.append(new_pos)
                alien_positions[row] = new_positions
        # Spawn alien only at the defined rate
        if time.time() - last_spawn_time > ALIEN_SPAWN_RATE:
            spawn_alien()
            last_spawn_time = time.time()

def spawn_alien():
    """Spawn a new alien at the right edge."""
    with alien_lock:
        if not paused:
            row = random.randint(0, ROWS - 1)
            alien_positions[row].append(COLUMNS - 1)


def move_missiles():
    """Move missiles from left to right."""
    global score, level, level_up
    while not game_over:
        if paused:
            time.sleep(0.1)
            continue
        time.sleep(MISSILE_SPEED)
        with missile_lock:
            for row in range(ROWS):
                updated_missiles = []
                for missile_pos in missile_positions[row]:
                    missile_pos += 1
                    collision = False
                    with alien_lock:
                        if missile_pos in alien_positions[row]:
                            alien_positions[row].remove(missile_pos)
                            collision = True
                            score += 1
                            if score % LEVEL_UP_SCORE == 0:
                                level += 1
                                with level_up_lock:
                                    level_up = True  # Set the level-up flag
                    if not collision and missile_pos < COLUMNS:
                        updated_missiles.append(missile_pos)
                missile_positions[row] = updated_missiles

def show_level_up_message(current_level):
    """Display a message when the player levels up."""
    global paused
    paused = True
    clear_screen()
    print("=" * (COLUMNS + 10))
    print(f"🎉 LEVEL UP! 🎉")
    print(f"🌟 You've reached Level {current_level}! Keep going! 🌟")
    print("=" * (COLUMNS + 10))
    show_headquarter_message()
    paused = False

def show_headquarter_message():
    """Display a message from the headquarters."""
    messages = [
        "Head Quarter: Commander, watch out for faster aliens in next Level!",
        "Head Quarter: Excellent shooting! Keep up the good work!",
        "Head Quarter: Your mission is critical. Earth is counting on you!",
        "Head Quarter: Be careful! Aliens are targeting your position.",
        "Head Quarter: Don't forget, you can use 'k' to shoot missiles!",
        "Head Quarter: Stay sharp, Commander. The mothership isn't far!",
        "Head Quarter: A new wave of aliens is approaching. Brace yourself!",
        "Head Quarter: Remember, you can pause with 'p' if you need a breather.",
        "Head Quarter: Each level makes the aliens faster. Good luck!",
        "Head Quarter: Protect Earth at all costs. Failure is not an option.",
        "Head Quarter: Outstanding moves, Commander! You're a natural hero!",
        "Head Quarter: You've outsmarted the aliens again. Keep it up!",
        "Head Quarter: Commander, you're making Earth proud! Onward!",
        "Head Quarter: That's what we call precision shooting. Bravo!",
        "Head Quarter: Your bravery inspires us all. Humanity salutes you!"
    ]
    # print("=" * (COLUMNS + 10))
    slow_print(random.choice(messages))
    print("=" * (COLUMNS + 10))
    time.sleep(2)

def missile_cooldown():
    """Reset missile readiness after cooldown."""
    global missile_ready
    time.sleep(MISSILE_COOLDOWN)
    missile_ready = True

def on_press(key):
    """Handle key press events."""
    global player_row, missile_ready, paused, game_over
    if paused and key != keyboard.KeyCode.from_char('p'):
        return
    try:
        if key.char == 'w':  # Move up
            if player_row > 0:
                player_row -= 1
        elif key.char == 's':  # Move down
            if player_row < ROWS - 1:
                player_row += 1
        elif key.char == 'k':  # Shoot missile with 'k'
            if missile_ready:
                with missile_lock:
                    missile_positions[player_row].append(1)  # Add a new missile at column 1
                missile_ready = False
                threading.Thread(target=missile_cooldown, daemon=True).start()
        elif key.char == 'p':  # Pause or unpause
            paused = not paused
        elif key.char == 'q':  # Quit game
            game_over = True
            return False  # Stop listener
    except AttributeError:
        # Handle special keys
        if key == keyboard.Key.space:  # Shoot missile with space bar
            if missile_ready:
                with missile_lock:
                    missile_positions[player_row].append(1)
                missile_ready = False
                threading.Thread(target=missile_cooldown, daemon=True).start()
        elif key == keyboard.Key.esc:
            game_over = True
            return False  # Stop listener

def game_loop():
    """Main game loop."""
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    alien_thread = threading.Thread(target=move_aliens, daemon=True)
    missile_thread = threading.Thread(target=move_missiles, daemon=True)
    alien_thread.start()
    missile_thread.start()
    while not game_over:
        if paused:
            clear_screen()
            print("Game Paused. Press 'p' to resume.")
            time.sleep(0.1)
            continue
        display_game()
        time.sleep(0.1)
    listener.stop()
    # No need to join daemon threads
    clear_screen()
    print("GAME OVER!")
    print(f"Final Score: {score}")
    print(f"Level Reached: {level}")
    print("Thanks for playing!")
    header = r"""
         _    ______  ________     ____  ___  ______________    ______
        | |  / / __ \/  _/ __ \   / __ )/   |/_  __/_  __/ /   / ____/
        | | / / / / // // / / /  / __  / /| | / /   / / / /   / __/   
        | |/ / /_/ // // /_/ /  / /_/ / ___ |/ /   / / / /___/ /___   
        |___/\____/___/_____/  /_____/_/  |_/_/   /_/ /_____/_____/   
                                                              
    """
    
    # Cool Borders and Alignment
    border = "=" * 70
    scoreboard = f"""
    {header}
    {border}
    
                        FINAL SCOREBOARD
                
    {border}

                        Level Reached: {level}
                        Final Score:   {score}
    
    {border}
                        Thank you for playing!
    """
    
    clear_screen()
    print(scoreboard)


def main():
    """Start the game."""
    clear_screen()
    print("Press 's' to skip the story or any other key to continue.")
    user_input = input()
    if user_input.lower() != 's':
        play_intro()
    
    game_loop()
    
def play_intro():
    """Displays the intro sequence with decorations, animations, and interactivity."""
    header = r"""
        ╔══════════════════════════════════════════════════════════════════╗
        ║     _    ______  ________     ____  ___  ______________    ______║
        ║    | |  / / __ \/  _/ __ \   / __ )/   |/_  __/_  __/ /   / ____/║
        ║    | | / / / / // // / / /  / __  / /| | / /   / / / /   / __/   ║
        ║    | |/ / /_/ // // /_/ /  / /_/ / ___ |/ /   / / / /___/ /___   ║
        ║    |___/\____/___/_____/  /_____/_/  |_/_/   /_/ /_____/_____/   ║
        ║                                                                  ║
        ╚══════════════════════════════════════════════════════════════════╝
                                                              
    """
    clear_screen()

    print(header)
    slow_print("                         GALACTIC HERO: THE EARTH DEFENDERS")
    time.sleep(5)

    clear_screen()
    slow_print("In the year 2075, Earth faced its greatest threat...\n", 0.07)
    slow_print("""
    👾 A massive alien fleet entered Earth's orbit. They had one goal:
    CONQUEST.
    """, 0.05)
    time.sleep(2)

    slow_print("""
    🛡️  The nations of Earth were in chaos. But amidst the despair,
    a beacon of hope emerged: ISRO, India's space research agency.
    """, 0.06)
    time.sleep(4)

    clear_screen()
    slow_print("""
    Dr. Aryan, ISRO's lead scientist, addressed the global leaders:
    'We intercepted the alien's signals. Their mothership is the key.'
    'We have built humanity's first interstellar combat ship: the X-77 Defender.'
    'Commander, you have been chosen to lead this mission.'
    """, 0.05)
    time.sleep(2)

    # Adding player action
    input(">>> PRESS ENTER TO ACCEPT THE MISSION <<<")

    clear_screen()
    slow_print("""
    You climb into the cockpit of the X-77 Defender...
    Lights flicker. The hum of the engine surrounds you.
    The control panel comes alive as the countdown begins.
    """, 0.07)
    time.sleep(2)

    # Launch sequence animation
    launch_sequence()
    time.sleep(1)

    # Display mission start
    clear_screen()
    print(header)
    slow_print("            MiSSION:  Stop the alien fleet. Save humanity. 🌍        ")
    time.sleep(2)
    input(">>> PRESS ENTER TO BEGIN THE GAME <<<")

def launch_sequence():
    """Displays the launch sequence animation."""
    frames = [
        """
             ▄█████████▄
           ▄██▀       ▀██▄
          ███           ███
         ███     ██     ███
          ███▄         ▄███
           ▀██▄       ▄██▀
             ▀█████████▀

         🚀 Preparing for liftoff...
        """,
        """
             ▄█████████▄
           ▄██▀       ▀██▄
          ███           ███
         ███     ██     ███
          ███▄         ▄███
           ▀██▄       ▄██▀
             ▀█████████▀

         🚀 Engines igniting...
        """,
        """
              ▄███████▄
            ▄██▀     ▀██▄
           ██     █     ██
            ▀██▄     ▄██▀
              ▀███████▀

         🚀 Lifting off!
        """,
        """
                ▄████▄
               ██▀ ▀██
                ▀▄ ▄▀

         🌌 Entering space...
        """
    ]

    for frame in frames:
        clear_screen()
        print(frame)
        time.sleep(1.5)

def slow_print(text, speed=0.05):
    """Prints text character by character with a delay."""
    import sys
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(speed)
    print()

def clear_screen():
    """Clears the console screen."""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    main()