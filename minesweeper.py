import tkinter as tk
from random import shuffle
from tkinter.messagebox import showinfo, showerror
from PIL import ImageTk, Image
from typing import List, Set, Tuple, Dict
from itertools import combinations
from collections import defaultdict
import time

# Original color definitions for display
colors = {
    1: '#0000FF',
    2: '#008200',
    3: '#FF0000',
    4: '#000084',
    5: '#840000',
    6: '#008284',
    7: '#840084',
    8: '#800020'
}


# Button class to represent each cell in the grid
class MyButton(tk.Button):
    def __init__(self, master, x, y, number=0, *args, **kwargs):
        super(MyButton, self).__init__(
            master, *args, **kwargs, width=3, font='Calibri 15 bold')
        self.x = x # row index
        self.y = y # column index
        self.number = number # cell number
        self.is_mine = False
        self.count_bomb = 0 # number of neighboring mines
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
        for dx in [-1, 0, 1]: # iterate over neighboring rows
            for dy in [-1, 0, 1]: # iterate over neighboring columns

                # Skip the cell itself
                if dx == 0 and dy == 0:
                    continue

                new_x, new_y = x + dx, y + dy # calculate coordinates of the neighboring cell

                # Add the cell to neighbors after checking for bounds and unopened state
                if (1 <= new_x <= self.game.ROW and
                    1 <= new_y <= self.game.COLUMNS and
                        not self.game.buttons[new_x][new_y].is_open):
                    neighbors.add((new_x, new_y))

        return neighbors # return the set of unopened neighbors

    def update_constraints(self):
        self.constraints.clear()
        self.frontier.clear()

        for i in range(1, self.game.ROW + 1): # iterate through rows
            for j in range(1, self.game.COLUMNS + 1): # iterate through columns
                btn = self.game.buttons[i][j]
                if btn.is_open and btn.count_bomb > 0: # only for cells with neighboring mines
                    unopened = self.get_unopened_neighbors(i, j)
                    if unopened: # only if there are unopened neighbor cells
                        known_mines = len(unopened.intersection(self.known_mines)) # number of neighboring KNOWN mines
                        remaining_mines = btn.count_bomb - known_mines # number of undiscovered neighboring mines
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


# Functionality and GUI for the actual Minesweeper game
class MineSweeper:
    window = tk.Tk()
    ROW = 10
    COLUMNS = 7
    MINES = 7
    IS_GAME_OVER = False
    IS_FIRST_CLICK = True
    window.geometry('+800+200')

    def __init__(self):
        self.buttons = []
        self.solver = MinesweeperSolver(self)
        self.auto_solve = False
        self.solve_start_time = None
        self.solve_total_time = 0.0
        self.move_count = 0
        
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
        self.timer_label = tk.Label(self.window, text="Time: 0.00s | Moves: 0", font=('Calibri', 12))


    def insert_mines(self, number: int):
        index_mines = self.get_mines_places(number)
        print(index_mines)
        for i in range(1, self.ROW+1):
            for j in range(1, self.COLUMNS+1):
                btn = self.buttons[i][j]
                if btn.number in index_mines:
                    btn.is_mine = True

    def get_mines_places(self, exclude_number: int):
        indexes = list(range(1, self.COLUMNS * self.ROW + 1))
        print(f'Exclude number {exclude_number}')
        indexes.remove(exclude_number)
        shuffle(indexes)
        return indexes[:self.MINES]

    def breadth_first_search(self, btn: MyButton):
        queue = [btn]
        while queue:
            cur_btn = queue.pop()
            color = colors.get(cur_btn.count_bomb, 'black')
            if cur_btn.count_bomb:
                cur_btn.config(text=cur_btn.count_bomb,
                               disabledforeground=color)
            else:
                cur_btn.config(text='', disabledforeground=color)
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
        if self.IS_GAME_OVER:
            return
        cur_btn = event.widget
        if cur_btn['state'] == 'normal':
            cur_btn['state'] = 'disabled'
            cur_btn['image'] = self.flag_img
        elif cur_btn['state'] == 'disabled':
            cur_btn['image'] = ''
            cur_btn['state'] = 'normal'

    def click(self, clicked_button: MyButton):
        if self.IS_GAME_OVER:
            return
        if self.IS_FIRST_CLICK:
            self.insert_mines(clicked_button.number)
            self.count_mine_in_buttons()
            self.print_buttons()
            self.IS_FIRST_CLICK = False
        if clicked_button.is_mine:
            clicked_button.config(image=self.mine_img, background='red',
                                  disabledforeground='black')
            clicked_button.is_open = True
            self.IS_GAME_OVER = True
            showinfo('Game over', 'You lose!')
            for i in range(1, self.ROW+1):
                for j in range(1, self.COLUMNS+1):
                    btn = self.buttons[i][j]
                    if btn.is_mine:
                        btn['image'] = self.mine_img
        else:
            color = colors.get(clicked_button.count_bomb, 'black')
            if clicked_button.count_bomb:
                clicked_button.config(text=clicked_button.count_bomb,
                                      disabledforeground=color)
                clicked_button.is_open = True
            else:
                self.breadth_first_search(clicked_button)
        clicked_button.config(state='disabled')
        clicked_button.config(relief=tk.SUNKEN)

        # Check for win condition
        if self.check_win():
            self.IS_GAME_OVER = True
            showinfo('Congratulations', 'You won!')

    def check_win(self):
        """Check if all non-mine cells are opened."""
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
        self.timer_label.config(text=f"Time: {self.solve_total_time:.2f}s | Moves: {self.move_count}")

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
        [child.destroy() for child in self.window.winfo_children()]
        self.__init__()
        self.create_widgets()
        MineSweeper.IS_FIRST_CLICK = True
        MineSweeper.IS_GAME_OVER = False
        
        # Reset timer and move count
        self.solve_start_time = None
        self.solve_total_time = 0.0
        self.move_count = 0
        self.update_timer_label()

    def create_settings_win(self):
        win_settings = tk.Toplevel(self.window)
        win_settings.wm_title('Settings')
        tk.Label(win_settings, text='Rows').grid(row=0, column=0)
        row_entry = tk.Entry(win_settings)
        row_entry.insert(0, self.ROW)
        row_entry.grid(row=0, column=1, padx=20, pady=20)
        tk.Label(win_settings, text='Columns').grid(row=1, column=0)
        column_entry = tk.Entry(win_settings)
        column_entry.insert(0, self.COLUMNS)
        column_entry.grid(row=1, column=1, padx=20, pady=20)
        tk.Label(win_settings, text='Mines').grid(row=2, column=0)
        mine_entry = tk.Entry(win_settings)
        mine_entry.insert(0, self.MINES)
        mine_entry.grid(row=2, column=1, padx=20, pady=20)
        save_btn = tk.Button(win_settings, text='Apply',
                             command=lambda: self.change_settings(row_entry, column_entry, mine_entry))
        save_btn.grid(row=3, column=8, columnspan=2, padx=20, pady=20)
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

    def print_buttons(self):
        """Print the game board state to console for debugging."""
        for i in range(1, MineSweeper.ROW + 1):
            for j in range(1, MineSweeper.COLUMNS + 1):
                btn = self.buttons[i][j]
                if btn.is_mine:
                    print('B', end='')
                else:
                    print(btn.count_bomb, end='')
            print()

    def start(self):
        self.create_widgets()
        MineSweeper.window.mainloop()


if __name__ == "__main__":
    game = MineSweeper()
    game.start()
