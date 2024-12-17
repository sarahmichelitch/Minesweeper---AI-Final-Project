import tkinter as tk
from random import shuffle
from tkinter.messagebox import showinfo, showerror
from PIL import ImageTk, Image
from typing import List, Set, Tuple, Dict
from itertools import combinations
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
from typing import List
import pandas as pd
import time
import argparse
from tqdm import tqdm

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt



# Original color definitions for display
COLORS = {
    1: '#0000FF',  # Blue
    2: '#008200',  # Green
    3: '#FF0000',  # Red
    4: '#000084',  # Dark Blue
    5: '#840000',  # Dark Red
    6: '#008284',  # Cyan
    7: '#840084',  # Purple
    8: '#800020'   # Maroon
}

BUTTON_COLORS = {
    'default': '#f0f0f0',      # Light gray for unopened cells
    'revealed': '#ffffff',      # White for revealed cells
    'mine': '#ff0000',         # Red for mines
    'flagged': '#e0e0e0'       # Slightly darker gray for flagged cells
}


# Button class to represent each cell in the grid
class MyButton(tk.Button):
    def __init__(self, master, x, y, number=0, *args, **kwargs):
        super(MyButton, self).__init__(
            master, *args, **kwargs, width=3, font='Calibri 15 bold',
            background=BUTTON_COLORS['default'])  # Set default background
        self.x = x  # row index
        self.y = y  # column index
        self.number = number  # cell number
        self.is_mine = False
        self.count_bomb = 0  # number of neighboring mines
        self.is_open = False

    def __repr__(self):
        return f'MyButton{self.x} {self.y} {self.number} {self.is_mine}'


# AI solver agent class
class MinesweeperSolver:
    def __init__(self, game: 'MineSweeper'):
        self.game = game
        self.known_mines: Set[Tuple[int, int]] = set()
        self.known_safe: Set[Tuple[int, int]] = set()
        self.frontier: Set[Tuple[int, int]] = set()
        self.constraints: Dict[Tuple[int, int],
                               List[Tuple[Set[Tuple[int, int]], int]]] = defaultdict(list)
        self.total_mines = game.MINES
        self.mines_found = 0

    def get_unopened_neighbors(self, x: int, y: int) -> Set[Tuple[int, int]]:
        neighbors = set()
        for dx in [-1, 0, 1]:  # iterate over neighboring rows
            for dy in [-1, 0, 1]:  # iterate over neighboring columns

                # Skip the cell itself
                if dx == 0 and dy == 0:
                    continue

                new_x, new_y = x + dx, y + dy  # calculate coordinates of the neighboring cell

                # Add the cell to neighbors after checking for bounds and unopened state
                if (1 <= new_x <= self.game.ROW and
                    1 <= new_y <= self.game.COLUMNS and
                        not self.game.buttons[new_x][new_y].is_open):
                    neighbors.add((new_x, new_y))

        return neighbors  # return the set of unopened neighbors

    def update_constraints(self):
        self.constraints.clear()
        self.frontier.clear()

        for i in range(1, self.game.ROW + 1):  # iterate through rows
            for j in range(1, self.game.COLUMNS + 1):  # iterate through columns
                btn = self.game.buttons[i][j]
                if btn.is_open and btn.count_bomb > 0:  # only for cells with neighboring mines
                    unopened = self.get_unopened_neighbors(i, j)
                    if unopened:  # only if there are unopened neighbor cells
                        # number of neighboring KNOWN mines
                        known_mines = len(
                            unopened.intersection(self.known_mines))
                        # number of undiscovered neighboring mines
                        remaining_mines = btn.count_bomb - known_mines
                        unopened = unopened.difference(self.known_mines)
                        # Update constraints and frontier if there are unopened neighbors
                        if unopened:
                            self.constraints[(i, j)].append(
                                (unopened, remaining_mines))
                            self.frontier.update(unopened)

    # Basic solver for if the number of neighboring mines equal the number of unopened neighbors or the number of known mines
    def basic_solve(self) -> bool:
        made_progress = False

        self.update_constraints()

        for cell, constraint_list in self.constraints.items():
            for unopened_cells, remaining_mines in constraint_list:

                # If the number of neighboring mines equals the number of unopened neighbors, mark them all as mines
                if len(unopened_cells) == remaining_mines and remaining_mines > 0:
                    for mine in unopened_cells:
                        if mine not in self.known_mines:
                            self.known_mines.add(mine)
                            self.mines_found += 1
                            made_progress = True

                # If there are no undiscovered neighboring mines, mark the rest of the neighbors as safe
                elif remaining_mines == 0:
                    for safe in unopened_cells:
                        if safe not in self.known_safe:
                            self.known_safe.add(safe)
                            made_progress = True

        return made_progress

    # Advanced solver comparing overlapping constaints to further deduce guaranteeed safe moves
    def advanced_solve(self) -> bool:
        made_progress = False

        for (cell1, constraints1), (cell2, constraints2) in combinations(self.constraints.items(), 2):
            for (cells1, mines1), (cells2, mines2) in [(c1, c2)
                                                       for c1 in constraints1
                                                       for c2 in constraints2]:
                if cells1.issubset(cells2):
                    diff_cells = cells2.difference(cells1)
                    diff_mines = mines2 - mines1

                    # If remaining cells are mines, mark them as such
                    if len(diff_cells) == diff_mines and diff_mines > 0:
                        for mine in diff_cells:
                            if mine not in self.known_mines:
                                self.known_mines.add(mine)
                                self.mines_found += 1
                                made_progress = True

                    # If remaining cell are safe, mark them as such
                    elif diff_mines == 0:
                        for safe in diff_cells:
                            if safe not in self.known_safe:
                                self.known_safe.add(safe)
                                made_progress = True

        return made_progress

    # Calculate risk probabilities for unopened cells for when there are no guaranteed safe moves
    def calculate_cell_probabilities(self) -> Dict[Tuple[int, int], float]:
        probabilities = defaultdict(float)
        remaining_mines = self.total_mines - self.mines_found

        # If no constraints, use global probability
        if not self.frontier:
            unopened_count = 0
            for i in range(1, self.game.ROW + 1):
                for j in range(1, self.game.COLUMNS + 1):
                    if not self.game.buttons[i][j].is_open:
                        unopened_count += 1
                        probabilities[(i, j)] = remaining_mines / \
                            unopened_count
            return probabilities

        # Calculate local probabilities based on constraints
        for cell, constraint_list in self.constraints.items():
            for unopened_cells, remaining_local_mines in constraint_list:
                if unopened_cells:  # Avoid division by zero
                    prob = remaining_local_mines / len(unopened_cells)
                    for pos in unopened_cells:
                        probabilities[pos] = max(probabilities[pos], prob)

        return probabilities

    # Get the unopened cell with the lowest risk probability
    def get_lowest_risk_move(self) -> Tuple[int, int]:
        probabilities = self.calculate_cell_probabilities()

        if not probabilities:
            # If no probabilities calculated, choose first unopened cell
            for i in range(1, self.game.ROW + 1):
                for j in range(1, self.game.COLUMNS + 1):
                    if not self.game.buttons[i][j].is_open:
                        return (i, j)

        # Return position with lowest probability of being a mine
        return min(probabilities.items(), key=lambda x: x[1])[0]

    def make_move(self) -> Tuple[int, int]:
        # First click should be in the center
        if self.game.IS_FIRST_CLICK:
            return (self.game.ROW // 2, self.game.COLUMNS // 2)

        # Click any known safe cells
        if self.known_safe:
            return self.known_safe.pop()

        # Apply solving techniques
        while self.basic_solve() or self.advanced_solve():
            if self.known_safe:
                return self.known_safe.pop()

        # If no safe moves found, use probability estimation
        return self.get_lowest_risk_move()
    

# Test class
class MinesweeperTester:
    def _init__(self):
        self.test = test
        self.is_first_run = True
        # list of list of results for each game [is_win, time, num_moves]
        self.game_results: List[List[bool, float, int]] = []

    @staticmethod
    def set_difficulty(game, difficulty):
        """Set the game difficulty before starting."""
        if difficulty in game.DIFFICULTY_PRESETS:
            game.CURRENT_DIFFICULTY = difficulty
            preset = game.DIFFICULTY_PRESETS[difficulty]
            game.ROW = preset['rows']
            game.COLUMNS = preset['columns']
            game.MINES = preset['mines']

    @staticmethod
    def run_one_game(difficulty=None):
        game = MineSweeper()
        if difficulty:
            MinesweeperTester.set_difficulty(game, difficulty)
        game.testing = True
        # Use headless mode instead of GUI
        game.start_headless()

    @classmethod
    def run_testing(cls, num_games, difficulty=None):
        is_win_index = 0
        time_index = 1
        num_moves_index = 2

        # Initialize variables to keep track of totals
        total_wins = 0
        total_losses = 0
 
        loss_times = []
        win_times = []
        loss_steps = []
        win_steps = []

        # Loop for number of games desired for testing
        for this_game in tqdm(range(num_games)):
            # Set booleans to know if variables need to be initialized
            if this_game == 0:
                test.is_first_run = True
            else:
                test.is_first_run = False

            # Run a game with specified difficulty
            cls.run_one_game(difficulty)

            if test.game_results[this_game][is_win_index]:
                total_wins += 1
                win_times.append(test.game_results[this_game][time_index] * 1000)
                win_steps.append(test.game_results[this_game][num_moves_index])
            else:
                total_losses += 1
                loss_times.append(test.game_results[this_game][time_index] * 1000)
                loss_steps.append(test.game_results[this_game][num_moves_index])

        # Print results with difficulty information

        difficulty_str = f" ({difficulty} difficulty)"
        print("TEST RESULTS (",difficulty,")")
        print("-" * (14 + len(difficulty_str)))

        print("Wins: ", total_wins, "/", num_games)
        print(f"Win Percentage: {total_wins / num_games * 100:.2f}%")
        print("---")

        print(f"Average Time To Win: {np.mean(win_times):.2f} ms" if total_wins > 0 else "Average Time To Win: N/A")
        print(f"Average Steps To Win: {np.mean(win_steps):.2f}" if total_wins > 0 else "Average Steps To Win: N/A")
        print(f"Median Steps To Win: {np.median(win_steps):.2f}" if total_wins > 0 else "Median Steps To Win: N/A")
        print(f"Standard Deviation Steps To Win: {np.std(win_steps):.2f}" if total_wins > 0 else "Standard Deviation Steps To Win: N/A")
        print("---")

        print(f"Average Time To Lose: {np.mean(loss_times):.2f} ms" if total_losses > 0 else "Average Time To Lose: N/A")
        print(f"Average Steps To Lose: {np.mean(loss_steps):.2f}" if total_losses > 0 else "Average Steps To Lose: N/A")
        print(f"Median Steps To Lose: {np.median(loss_steps):.2f}" if total_losses > 0 else "Median Steps To Lose: N/A")
        print(f"Standard Deviation Steps To Lose: {np.std(loss_steps):.2f}" if total_losses > 0 else "Standard Deviation Steps To Lose: N/A")
        print("---")

        print("---")

        cls.graph_frequencies(loss_steps, 4)

    @classmethod
    def graph_frequencies(cls, list, bucket_size):
        plt.ioff()  # Disable interactive mode temporarily
        
        max_value = max(list) if list else 0
        bins = np.arange(0, max_value + bucket_size, bucket_size)

        hist, bin_edges = np.histogram(list, bins=bins)
        plt.bar(bin_edges[:-1], hist, width=bucket_size, edgecolor="black", align="edge")
        plt.xlabel("Number of Steps to Lose (Buckets of 10)")
        plt.ylabel("Frequency")
        plt.title("Frequency of Steps to Lose")

        plt.tight_layout()
        plt.savefig("./Intermediate_Step_Frequencies.png")
        plt.close('all')  # Close all open figures to free resources
        
        
        
class MineSweeper:

    """ How we decided the varying board dimensions for each difficulty:
    https://minesweepergame.com/ranking-rules.php#:~:text=Players%20are%20ranked%20by%20the,(30x16%20with%2099%20mines).
    """
    DIFFICULTY_PRESETS = {
        'easy': {'rows': 8, 'columns': 8, 'mines': 10},
        'intermediate': {'rows': 16, 'columns': 16, 'mines': 40},
        'advanced': {'rows': 16, 'columns': 30, 'mines': 99}
    }

    # Default to easy difficulty
    CURRENT_DIFFICULTY = 'easy'

    # Update class variables to use the easy preset by default
    ROW = DIFFICULTY_PRESETS['easy']['rows']
    COLUMNS = DIFFICULTY_PRESETS['easy']['columns']
    MINES = DIFFICULTY_PRESETS['easy']['mines']

    def change_difficulty(self, difficulty: str):
        """Change the game difficulty and reload the board."""
        if difficulty in self.DIFFICULTY_PRESETS:
            MineSweeper.CURRENT_DIFFICULTY = difficulty
            preset = self.DIFFICULTY_PRESETS[difficulty]
            MineSweeper.ROW = preset['rows']
            MineSweeper.COLUMNS = preset['columns']
            MineSweeper.MINES = preset['mines']

            # Store current window reference
            if not self.testing and hasattr(self, 'window'):
                old_window = self.window
                old_window.destroy()

            # Reinitialize everything
            self.__init__()
            if not self.testing:
                self.create_widgets()

    def __init__(self):
        self.testing = False  # Skip GUI initialization if in testing mode
        self.buttons = []
        self.solver = MinesweeperSolver(self)
        self.auto_solve = False
        self.solve_start_time = None
        self.solve_total_time = 0.0
        self.move_count = 0

        self.IS_GAME_OVER = False
        self.IS_LOSS = False
        self.IS_WIN = False
        self.IS_FIRST_CLICK = True

        # Only initialize GUI elements if NOT in testing mode
        if not self.testing:
            self.window = tk.Tk()
            self.window.geometry('+800+200')

            for i in range(self.ROW+2):
                temp = []
                for j in range(self.COLUMNS+2):
                    btn = MyButton(self.window, x=i, y=j)
                    btn.config(command=lambda button=btn: self.click(button))
                    btn.bind('<Button-3>', self.right_click)
                    temp.append(btn)
                self.buttons.append(temp)

            # Load images after initializing Tkinter window
            self.flag_img = ImageTk.PhotoImage(Image.open("img/flag.png"))
            self.mine_img = ImageTk.PhotoImage(Image.open("img/mine.png"))

            # Timer label
            self.timer_label = tk.Label(
                self.window, text="Time: 0.00s | Moves: 0", font=('Calibri', 12))

    def insert_mines(self, number: int):
        index_mines = self.get_mines_places(number)
        # print(index_mines)
        for i in range(1, self.ROW+1):
            for j in range(1, self.COLUMNS+1):
                btn = self.buttons[i][j]
                if btn.number in index_mines:
                    btn.is_mine = True

    def start_headless(self):
        """Start the game in headless mode (no GUI) for faster testing"""
        if not self.testing:
            return

        # Initialize the game board without GUI elements
        self.buttons = []
        for i in range(self.ROW+2):
            temp = []
            for j in range(self.COLUMNS+2):
                btn = MyButton(None, x=i, y=j)  # None as master means no GUI
                btn.number = (i-1) * self.COLUMNS + \
                    j if 1 <= i <= self.ROW and 1 <= j <= self.COLUMNS else 0
                temp.append(btn)
            self.buttons.append(temp)

        # Start timer
        self.solve_start_time = time.time()

        # Make first move (center)
        center_x, center_y = self.ROW // 2, self.COLUMNS // 2
        first_btn = self.buttons[center_x][center_y]
        self.click(first_btn)

        # Keep making moves until game is over
        while not self.IS_GAME_OVER:
            x, y = self.solver.make_move()
            btn = self.buttons[x][y]
            self.click(btn)

            # Update total time
            current_time = time.time()
            self.solve_total_time = current_time - self.solve_start_time

    def get_mines_places(self, exclude_number: int):
        indexes = list(range(1, self.COLUMNS * self.ROW + 1))
        
        safe_squares = []
        for i in [-1, 0, 1]:
            for j in [-1, 0, 1]:
                safe_squares.append(exclude_number + i * self.COLUMNS + j)
        
        for i in safe_squares:
            if i > 0 and i < self.COLUMNS * self.ROW + 1:
                indexes.remove(i)
        

        shuffle(indexes)
        return indexes[:self.MINES]

    def breadth_first_search(self, btn: MyButton):
        queue = [btn]
        while queue:
            cur_btn = queue.pop()
            color = COLORS.get(cur_btn.count_bomb, 'black')
            if cur_btn.count_bomb:
                cur_btn.config(text=cur_btn.count_bomb,
                               disabledforeground=color,
                               # Set revealed color
                               background=BUTTON_COLORS['revealed'])
            else:
                cur_btn.config(text='',
                               disabledforeground=color,
                               # Set revealed color
                               background=BUTTON_COLORS['revealed'])
            cur_btn.is_open = True
            cur_btn.config(state='disabled')
            cur_btn.config(relief=tk.SUNKEN)
            if cur_btn.count_bomb == 0:
                x, y = cur_btn.x, cur_btn.y
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        next_btn = self.buttons[x+dx][y+dy]
                        if not next_btn.is_open and 1 <= next_btn.x <= self.ROW and \
                                1 <= next_btn.y <= self.COLUMNS and next_btn not in queue:
                            queue.append(next_btn)

    def count_mine_in_buttons(self):
        for i in range(1, self.ROW+1):
            for j in range(1, self.COLUMNS+1):
                btn = self.buttons[i][j]
                count_bomb = 0
                if not btn.is_mine:
                    for row_dx in [-1, 0, 1]:
                        for col_dx in [-1, 0, 1]:
                            neighbour = self.buttons[i+row_dx][j+col_dx]
                            if neighbour.is_mine:
                                count_bomb += 1
                btn.count_bomb = count_bomb

    def right_click(self, event):
        if self.IS_GAME_OVER or self.testing:  # Don't handle right clicks in testing mode
            return
        cur_btn = event.widget
        if cur_btn['state'] == 'normal':
            cur_btn['state'] = 'disabled'
            cur_btn.flag_image = self.flag_img
            cur_btn['image'] = cur_btn.flag_image
            # Set flagged color
            cur_btn.config(background=BUTTON_COLORS['flagged'])
        elif cur_btn['state'] == 'disabled':
            cur_btn['image'] = ''
            cur_btn.flag_image = None
            cur_btn['state'] = 'normal'
            # Reset to default color
            cur_btn.config(background=BUTTON_COLORS['default'])

    def click(self, clicked_button: MyButton):
        self.move_count += 1
        if self.IS_GAME_OVER:
            self.reload()
            return
        if self.IS_FIRST_CLICK:
            self.insert_mines(clicked_button.number)
            self.count_mine_in_buttons()
            self.IS_FIRST_CLICK = False
        if clicked_button.is_mine:
            if not self.testing:
                clicked_button.mine_image = self.mine_img
                clicked_button.config(image=clicked_button.mine_image,
                                      # Set mine color
                                      background=BUTTON_COLORS['mine'],
                                      disabledforeground='black')
            clicked_button.is_open = True
            self.IS_GAME_OVER = True
            self.IS_LOSS = True
            

            if self.testing:
                if test.is_first_run:
                    test.game_results = []
                test.game_results.append(
                    [False, self.solve_total_time, self.move_count])
                self.window.quit()
                return

            showinfo('Game over', 'You lose!')
            print("move count = ", self.move_count)
            if not self.testing:
                for i in range(1, self.ROW+1):
                    for j in range(1, self.COLUMNS+1):
                        btn = self.buttons[i][j]
                        if btn.is_mine:
                            btn.mine_image = self.mine_img
                            btn['image'] = btn.mine_image
                            # Set mine color
                            btn.config(background=BUTTON_COLORS['mine'])
                self.reload()
        else:
            color = COLORS.get(clicked_button.count_bomb, 'black')
            if clicked_button.count_bomb:
                clicked_button.config(text=clicked_button.count_bomb,
                                      disabledforeground=color,
                                      # Set revealed color
                                      background=BUTTON_COLORS['revealed'])
                clicked_button.is_open = True
            else:
                self.breadth_first_search(clicked_button)
        clicked_button.config(state='disabled')
        clicked_button.config(relief=tk.SUNKEN)

        # Check for win condition
        if self.check_win():
            self.IS_GAME_OVER = True
            self.IS_WIN = True

            # Different response for testing (due to looping)
            if self.testing:
                if test.is_first_run:
                    test.game_results = []
                test.game_results.append(
                    [True, self.solve_total_time, self.move_count])
                self.window.quit()
                return

            showinfo('Congratulations', 'You won!')

    # Check if all non-mine cells are opened
    def check_win(self):
        for i in range(1, self.ROW+1):
            for j in range(1, self.COLUMNS+1):
                btn = self.buttons[i][j]
                if not btn.is_mine and not btn.is_open:
                    return False
        return True

    def add_ai_controls(self):
        control_frame = tk.Frame(self.window)
        control_frame.grid(row=self.ROW + 1, column=1,
                           columnspan=self.COLUMNS, pady=10)

        hint_btn = tk.Button(control_frame, text="Get Hint",
                             command=self.make_ai_move)
        hint_btn.pack(side=tk.LEFT, padx=5)

        auto_btn = tk.Button(control_frame, text="Auto Solve",
                             command=self.toggle_auto_solve)
        auto_btn.pack(side=tk.LEFT, padx=5)

        # Add timer label to the control frame
        self.timer_label.grid(row=0, column=self.COLUMNS+2, padx=5)

    def make_ai_move(self):
        if not self.IS_GAME_OVER:
            # Start timer on first move
            if self.solve_start_time is None:
                self.solve_start_time = time.time()

            x, y = self.solver.make_move()
            btn = self.buttons[x][y]
            self.click(btn)

            # Update move count and timer
            self.move_count += 1
            current_time = time.time()
            self.solve_total_time = current_time - self.solve_start_time
            self.update_timer_label()

    def update_timer_label(self):
        self.timer_label.config(
            text=f"Time: {self.solve_total_time:.2f}s | Moves: {self.move_count}")

    def toggle_auto_solve(self):
        self.auto_solve = not self.auto_solve
        if self.auto_solve:
            # Reset timer and move count
            self.solve_start_time = time.time()
            self.solve_total_time = 0.0
            self.move_count = 0
            self.update_timer_label()
            self.auto_solve_step()

    def auto_solve_step(self):
        if self.auto_solve and not self.IS_GAME_OVER:
            self.make_ai_move()
            self.window.after(500, self.auto_solve_step)

    def create_widgets(self):
        menubar = tk.Menu(self.window)
        self.window.config(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label='Game', command=self.reload)
        settings_menu.add_command(
            label='Settings', command=self.create_settings_win)
        settings_menu.add_command(label='Exit', command=self.window.destroy)
        menubar.add_cascade(label='File', menu=settings_menu)
        count = 1
        for i in range(1, self.ROW+1):
            for j in range(1, self.COLUMNS+1):
                btn = self.buttons[i][j]
                btn.number = count
                btn.grid(row=i, column=j, stick='NWES')
                count += 1
        for i in range(1, self.ROW+1):
            tk.Grid.rowconfigure(self.window, i, weight=1)
        for i in range(1, self.COLUMNS+1):
            tk.Grid.columnconfigure(self.window, i, weight=1)
        self.add_ai_controls()

    def reload(self):
        # Store current window reference
        if not self.testing and hasattr(self, 'window'):
            old_window = self.window
            old_window.destroy()

        # Reinitialize everything
        self.__init__()
        if not self.testing:
            self.create_widgets()

        self.IS_FIRST_CLICK = True
        self.IS_GAME_OVER = False

        # Reset timer and move count
        self.solve_start_time = None
        self.solve_total_time = 0.0
        self.move_count = 0
        if not self.testing:
            self.update_timer_label()

    def create_settings_win(self):
        win_settings = tk.Toplevel(self.window)
        win_settings.wm_title('Settings')

        # Difficulty selection
        tk.Label(win_settings, text='Difficulty').grid(row=0, column=0)
        difficulty_var = tk.StringVar(value=self.CURRENT_DIFFICULTY)
        difficulty_frame = tk.Frame(win_settings)
        difficulty_frame.grid(row=0, column=1, padx=20, pady=10)

        for diff in self.DIFFICULTY_PRESETS.keys():
            tk.Radiobutton(
                difficulty_frame,
                text=diff.capitalize(),
                variable=difficulty_var,
                value=diff,
                command=lambda d=diff: self.change_difficulty(d)
            ).pack(side=tk.LEFT)

        # Custom settings section
        tk.Label(win_settings, text='Custom Settings').grid(
            row=1, column=0, columnspan=2, pady=(20, 5))

        tk.Label(win_settings, text='Rows').grid(row=2, column=0)
        row_entry = tk.Entry(win_settings)
        row_entry.insert(0, self.ROW)
        row_entry.grid(row=2, column=1, padx=20, pady=5)

        tk.Label(win_settings, text='Columns').grid(row=3, column=0)
        column_entry = tk.Entry(win_settings)
        column_entry.insert(0, self.COLUMNS)
        column_entry.grid(row=3, column=1, padx=20, pady=5)

        tk.Label(win_settings, text='Mines').grid(row=4, column=0)
        mine_entry = tk.Entry(win_settings)
        mine_entry.insert(0, self.MINES)
        mine_entry.grid(row=4, column=1, padx=20, pady=5)

        save_btn = tk.Button(
            win_settings,
            text='Apply Custom',
            command=lambda: self.change_settings(
                row_entry, column_entry, mine_entry)
        )
        save_btn.grid(row=5, column=0, columnspan=2, pady=20)

        win_settings.geometry('+790+300')

    def change_settings(self, row: tk.Entry, column: tk.Entry, mine: tk.Entry):
        try:
            int(row.get()), int(column.get()), int(mine.get())
        except ValueError:
            showerror('Error', 'Wrong entry')
            return
        MineSweeper.ROW = int(row.get())
        MineSweeper.COLUMNS = int(column.get())
        MineSweeper.MINES = int(mine.get())
        self.reload()

# Print the game board state to console for debugging
    def print_buttons(self):
        for i in range(1, MineSweeper.ROW + 1):
            for j in range(1, MineSweeper.COLUMNS + 1):
                btn = self.buttons[i][j]
                if btn.is_mine:
                    print('B', end='')
                else:
                    print(btn.count_bomb, end='')
            print()

    def start(self):
        if not self.testing:
            self.create_widgets()
            self.window.mainloop()
        else:
            self.start_headless()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Minesweeper Game vs Testing")
    parser.add_argument(
        '-test', type=int, help="Run testing for a given number of games", default=None)
    parser.add_argument('-difficulty', type=str, choices=['easy', 'intermediate', 'advanced'],
                        help="Set the difficulty level for testing or gameplay", default=None)
    args = parser.parse_args()

    if args.test is None:
        # Run the game
        game = MineSweeper()
        if args.difficulty:
            game.change_difficulty(args.difficulty)
        game.start()
    else:
        # Run testing with specified difficulty
        test = MinesweeperTester
        test.run_testing(args.test, args.difficulty)

