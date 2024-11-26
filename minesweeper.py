import tkinter as tk
from random import shuffle
from tkinter.messagebox import showinfo, showerror
from PIL import ImageTk, Image
from typing import List, Set, Tuple, Dict
from itertools import combinations
from collections import defaultdict

# Original color definitions
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

class MyButton(tk.Button):
    def __init__(self, master, x, y, number=0, *args, **kwargs):
        super(MyButton, self).__init__(
            master, *args, **kwargs, width=3, font='Calibri 15 bold')
        self.x = x
        self.y = y
        self.number = number
        self.is_mine = False
        self.count_bomb = 0
        self.is_open = False

    def __repr__(self):
        return f'MyButton{self.x} {self.y} {self.number} {self.is_mine}'

class MinesweeperSolver:
    def __init__(self, game: 'MineSweeper'):
        self.game = game
        self.known_mines: Set[Tuple[int, int]] = set()
        self.known_safe: Set[Tuple[int, int]] = set()
        self.frontier: Set[Tuple[int, int]] = set()
        self.constraints: Dict[Tuple[int, int], List[Tuple[Set[Tuple[int, int]], int]]] = defaultdict(list)
        
    def get_unopened_neighbors(self, x: int, y: int) -> Set[Tuple[int, int]]:
        """Get coordinates of unopened neighboring cells."""
        neighbors = set()
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                new_x, new_y = x + dx, y + dy
                if (1 <= new_x <= self.game.ROW and 
                    1 <= new_y <= self.game.COLUMNS and 
                    not self.game.buttons[new_x][new_y].is_open):
                    neighbors.add((new_x, new_y))
        return neighbors

    def update_constraints(self):
        """Update the constraint system based on opened cells."""
        self.constraints.clear()
        
        # Gather constraints from revealed numbers
        for i in range(1, self.game.ROW + 1):
            for j in range(1, self.game.COLUMNS + 1):
                btn = self.game.buttons[i][j]
                if btn.is_open and btn.count_bomb > 0:
                    unopened = self.get_unopened_neighbors(i, j)
                    if unopened:
                        # Count already known mines around this cell
                        known_mines = len(unopened.intersection(self.known_mines))
                        remaining_mines = btn.count_bomb - known_mines
                        # Remove known mines from unopened set
                        unopened = unopened.difference(self.known_mines)
                        if unopened:
                            self.constraints[(i, j)].append((unopened, remaining_mines))
                            self.frontier.update(unopened)

    def basic_solve(self) -> bool:
        """Apply basic solving techniques and return True if any progress was made."""
        made_progress = False
        
        self.update_constraints()
        
        # Check each constraint
        for cell, constraint_list in self.constraints.items():
            for unopened_cells, remaining_mines in constraint_list:
                # If remaining_mines equals unopened cells count, all are mines
                if len(unopened_cells) == remaining_mines:
                    for mine in unopened_cells:
                        if mine not in self.known_mines:
                            self.known_mines.add(mine)
                            made_progress = True
                
                # If remaining_mines is 0, all unopened cells are safe
                elif remaining_mines == 0:
                    for safe in unopened_cells:
                        if safe not in self.known_safe:
                            self.known_safe.add(safe)
                            made_progress = True
        
        return made_progress

    def advanced_solve(self) -> bool:
        """Apply advanced solving techniques using set operations."""
        made_progress = False
        
        # Compare pairs of constraints to deduce additional information
        for (cell1, constraints1), (cell2, constraints2) in combinations(self.constraints.items(), 2):
            for (cells1, mines1), (cells2, mines2) in [(c1, c2) 
                                                      for c1 in constraints1 
                                                      for c2 in constraints2]:
                # If one set of cells is a subset of another
                if cells1.issubset(cells2):
                    diff_cells = cells2.difference(cells1)
                    diff_mines = mines2 - mines1
                    
                    if len(diff_cells) == diff_mines:
                        # All cells in difference must be mines
                        for mine in diff_cells:
                            if mine not in self.known_mines:
                                self.known_mines.add(mine)
                                made_progress = True
                    elif diff_mines == 0:
                        # All cells in difference must be safe
                        for safe in diff_cells:
                            if safe not in self.known_safe:
                                self.known_safe.add(safe)
                                made_progress = True
        
        return made_progress

    def make_move(self) -> Tuple[int, int]:
        """Decide the next move based on current knowledge."""
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
    
    def get_lowest_risk_move(self) -> Tuple[int, int]:
        """Estimate probabilities and return the lowest risk move."""
        if not self.frontier:
            # If no frontier cells, choose any unopened cell
            for i in range(1, self.game.ROW + 1):
                for j in range(1, self.game.COLUMNS + 1):
                    if not self.game.buttons[i][j].is_open:
                        return (i, j)
        
        # Calculate risk for frontier cells
        risk_scores = defaultdict(float)
        for cell, constraints in self.constraints.items():
            for unopened, mines in constraints:
                prob = mines / len(unopened)
                for pos in unopened:
                    risk_scores[pos] += prob
        
        # Return position with lowest risk score
        return min(risk_scores.items(), key=lambda x: x[1])[0]

class MineSweeper:
    window = tk.Tk()
    ROW = 10
    COLUMNS = 7
    MINES = 7
    IS_GAME_OVER = False
    IS_FIRST_CLICK = True
    window.geometry('+800+200')

    flag_img = ImageTk.PhotoImage(Image.open("img/flag.png"))
    mine_img = ImageTk.PhotoImage(Image.open("img/mine.png"))

    def __init__(self):
        self.buttons = []
        self.solver = MinesweeperSolver(self)
        self.auto_solve = False
        for i in range(MineSweeper.ROW+2):
            temp = []
            for j in range(MineSweeper.COLUMNS+2):
                btn = MyButton(MineSweeper.window, x=i, y=j)
                btn.config(command=lambda button=btn: self.click(button))
                btn.bind('<Button-3>', self.right_click)
                temp.append(btn)
            self.buttons.append(temp)
    def insert_mines(self, number: int):
        """Insert mines into the game board, avoiding the first clicked position."""
        index_mines = self.get_mines_places(number)
        print(index_mines)
        for i in range(1, MineSweeper.ROW+1):
            for j in range(1, MineSweeper.COLUMNS+1):
                btn = self.buttons[i][j]
                if btn.number in index_mines:
                    btn.is_mine = True

    def get_mines_places(self, exclude_number: int):
        """Get random positions for mines, excluding the first clicked position."""
        indexes = list(range(1, MineSweeper.COLUMNS * MineSweeper.ROW + 1))
        print(f'Exclude number {exclude_number}')
        indexes.remove(exclude_number)
        shuffle(indexes)
        return indexes[:MineSweeper.MINES]

    def breadth_first_search(self, btn: MyButton):
        """Reveal empty cells using breadth-first search."""
        queue = [btn]
        while queue:
            cur_btn = queue.pop()
            color = colors.get(cur_btn.count_bomb, 'black')
            if cur_btn.count_bomb:
                cur_btn.config(text=cur_btn.count_bomb, disabledforeground=color)
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
                        if not next_btn.is_open and 1 <= next_btn.x <= MineSweeper.ROW and \
                                1 <= next_btn.y <= MineSweeper.COLUMNS and next_btn not in queue:
                            queue.append(next_btn)

    def count_mine_in_buttons(self):
        """Count the number of adjacent mines for each cell."""
        for i in range(1, MineSweeper.ROW+1):
            for j in range(1, MineSweeper.COLUMNS+1):
                btn = self.buttons[i][j]
                count_bomb = 0
                if not btn.is_mine:
                    for row_dx in [-1, 0, 1]:
                        for col_dx in [-1, 0, 1]:
                            neighbour = self.buttons[i+row_dx][j+col_dx]
                            if neighbour.is_mine:
                                count_bomb += 1
                btn.count_bomb = count_bomb

    def add_ai_controls(self):
        """Add AI control buttons to the game interface."""
        control_frame = tk.Frame(self.window)
        control_frame.grid(row=self.ROW + 1, column=1, columnspan=self.COLUMNS, pady=10)
        
        hint_btn = tk.Button(control_frame, text="Get Hint", 
                           command=self.make_ai_move)
        hint_btn.pack(side=tk.LEFT, padx=5)
        
        auto_btn = tk.Button(control_frame, text="Auto Solve",
                           command=self.toggle_auto_solve)
        auto_btn.pack(side=tk.LEFT, padx=5)

    def make_ai_move(self):
        """Execute a single AI move."""
        if not self.IS_GAME_OVER:
            x, y = self.solver.make_move()
            btn = self.buttons[x][y]
            self.click(btn)

    def toggle_auto_solve(self):
        """Toggle automatic solving mode."""
        self.auto_solve = not self.auto_solve
        if self.auto_solve:
            self.auto_solve_step()

    def auto_solve_step(self):
        """Recursively make AI moves while auto-solve is enabled."""
        if self.auto_solve and not self.IS_GAME_OVER:
            self.make_ai_move()
            self.window.after(500, self.auto_solve_step)

    # [Include all your original MineSweeper methods here: right_click, click, reload, etc.]
    def right_click(self, event):
        if MineSweeper.IS_GAME_OVER:
            return
        cur_btn = event.widget
        if cur_btn['state'] == 'normal':
            cur_btn['state'] = 'disabled'
            cur_btn['image'] = self.flag_img
        elif cur_btn['state'] == 'disabled':
            cur_btn['image'] = ''
            cur_btn['state'] = 'normal'

    def click(self, clicked_button: MyButton):
        if MineSweeper.IS_GAME_OVER:
            return
        if MineSweeper.IS_FIRST_CLICK:
            self.insert_mines(clicked_button.number)
            self.count_mine_in_buttons()
            self.print_buttons()
            MineSweeper.IS_FIRST_CLICK = False
        if clicked_button.is_mine:
            clicked_button.config(image=self.mine_img, background='red',
                                  disabledforeground='black')
            clicked_button.is_open = True
            MineSweeper.IS_GAME_OVER = True
            showinfo('Game over', 'You lose!')
            for i in range(1, MineSweeper.ROW+1):
                for j in range(1, MineSweeper.COLUMNS+1):
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
        for i in range(1, MineSweeper.ROW+1):
            for j in range(1, MineSweeper.COLUMNS+1):
                btn = self.buttons[i][j]
                btn.number = count
                btn.grid(row=i, column=j, stick='NWES')
                count += 1
        for i in range(1, MineSweeper.ROW+1):
            tk.Grid.rowconfigure(self.window, i, weight=1)
        for i in range(1, MineSweeper.COLUMNS+1):
            tk.Grid.columnconfigure(self.window, i, weight=1)
        self.add_ai_controls()

    def reload(self):
        [child.destroy() for child in self.window.winfo_children()]
        self.__init__()
        self.create_widgets()
        MineSweeper.IS_FIRST_CLICK = True
        MineSweeper.IS_GAME_OVER = False

    def create_settings_win(self):
        win_settings = tk.Toplevel(self.window)
        win_settings.wm_title('Settings')
        tk.Label(win_settings, text='Rows').grid(row=0, column=0)
        row_entry = tk.Entry(win_settings)
        row_entry.insert(0, MineSweeper.ROW)
        row_entry.grid(row=0, column=1, padx=20, pady=20)
        tk.Label(win_settings, text='Columns').grid(row=1, column=0)
        column_entry = tk.Entry(win_settings)
        column_entry.insert(0, MineSweeper.COLUMNS)
        column_entry.grid(row=1, column=1, padx=20, pady=20)
        tk.Label(win_settings, text='Mines').grid(row=2, column=0)
        mine_entry = tk.Entry(win_settings)
        mine_entry.insert(0, MineSweeper.MINES)
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
            print()  # New line after each row

    def start(self):
        self.create_widgets()
        MineSweeper.window.mainloop()

game = MineSweeper()
game.start()


