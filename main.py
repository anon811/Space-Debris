# -*- coding: utf-8 -*-


import curses
import asyncio
import random
from itertools import cycle
from time import sleep

SPACE_KEY_CODE = 32
LEFT_KEY_CODE = 260
RIGHT_KEY_CODE = 261
UP_KEY_CODE = 259
DOWN_KEY_CODE = 258
STARS = '+*.:'

with open('./data/frame1.txt', 'r') as f1, open('./data/frame2.txt', 'r') as f2:
    frame1 = f1.read()
    frame2 = f2.read()
    frames = [frame1, frame2]


def read_controls(canvas):
    """Read keys pressed and returns tuple witl controls state."""

    rows_direction = columns_direction = 0
    space_pressed = False

    while True:
        pressed_key_code = canvas.getch()

        if pressed_key_code == -1:
            # https://docs.python.org/3/library/curses.html#curses.window.getch
            break

        if pressed_key_code == UP_KEY_CODE:
            rows_direction = -1

        if pressed_key_code == DOWN_KEY_CODE:
            rows_direction = 1

        if pressed_key_code == RIGHT_KEY_CODE:
            columns_direction = 1

        if pressed_key_code == LEFT_KEY_CODE:
            columns_direction = -1

        if pressed_key_code == SPACE_KEY_CODE:
            space_pressed = True

    return rows_direction, columns_direction, space_pressed


def get_frame_size(text):
    """Calculate size of multiline text fragment, return pair — number of rows and colums."""

    lines = text.splitlines()
    rows = len(lines)
    columns = max([len(line) for line in lines])
    return rows, columns


def draw_frame(canvas, start_row, start_column, text, negative=False):
    """Draw multiline text fragment on canvas, erase text instead of drawing if negative=True is specified."""

    rows_number, columns_number = canvas.getmaxyx()

    for row, line in enumerate(text.splitlines(), round(start_row)):
        if row < 0:
            continue

        if row >= rows_number:
            break

        for column, symbol in enumerate(line, round(start_column)):
            if column < 0:
                continue

            if column >= columns_number:
                break

            if symbol == ' ':
                continue

            # Check that current position it is not in a lower right corner of the window
            # Curses will raise exception in that case. Don`t ask why…
            # https://docs.python.org/3/library/curses.html#curses.window.addch
            if row == rows_number - 1 and column == columns_number - 1:
                continue

            symbol = symbol if not negative else ' '
            canvas.addch(row, column, symbol)


def get_stars(canvas, rows, cols, min_stars=30, max_stars=70):
    coroutines = []
    stars_count = random.randint(min_stars, max_stars)
    for i in range(stars_count):
        coroutine = blink(canvas,
                          random.randint(1, rows - 1),
                          random.randint(1, cols - 1),
                          symbol=random.choice(STARS),
                          tic_timeout=random.random())
        coroutines.append(coroutine)
    return coroutines


async def fire(canvas, start_row, start_column, rows_speed=-0.1, columns_speed=0):
    """Display animation of gun shot, direction and speed can be specified."""

    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()

    while 0 < row < max_row and 0 < column < max_column:
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


def constraint_spaceship_position(canvas, frame, spaceship_pos_rows, spaceship_pos_cols):
    """Constraint spaceship position to prevent desertion from the battlefield with space debris."""

    canvas_height, canvas_width = canvas.getmaxyx()
    frame_height, frame_width = get_frame_size(frame)
    field_height = canvas_height - frame_height
    field_width = canvas_width - frame_width
    rows = min(field_height, max(0, spaceship_pos_rows))
    cols = min(field_width, max(0, spaceship_pos_cols))
    return rows, cols


async def animate_spaceship(canvas, row, column, tic_timeout=1):
    spaceship_pos_rows = row
    spaceship_pos_cols = column
    frames_iter = cycle(frames)
    while True:
        frame = next(frames_iter)
        spaceship_pos_rows, spaceship_pos_cols = constraint_spaceship_position(canvas, frame,
                                                                               spaceship_pos_rows,
                                                                               spaceship_pos_cols)
        # Сохраняем положение кадра анимации, потребуется ниже для очистки экрана
        previous_rows = spaceship_pos_rows
        previous_cols = spaceship_pos_cols
        draw_frame(canvas, spaceship_pos_rows, spaceship_pos_cols, frame)
        for i in range(int(500 * tic_timeout)):
            rows_direction, columns_direction, space_pressed = read_controls(canvas)
            spaceship_pos_rows += rows_direction
            spaceship_pos_cols += columns_direction
            await asyncio.sleep(0)
        # Очищаем экран от "старого" кадра анимации
        draw_frame(canvas, previous_rows, previous_cols, frame, negative=True)


async def blink(canvas, row, column, symbol='*', tic_timeout=1):
    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        for i in range(int(1000 * 20 * tic_timeout)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(int(1000 * 3 * tic_timeout)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        for i in range(int(1000 * 5 * tic_timeout)):
            await asyncio.sleep(0)

        canvas.addstr(row, column, symbol)
        for i in range(int(1000 * 3 * tic_timeout)):
            await asyncio.sleep(0)


def draw(canvas):
    canvas_height, canvas_width = canvas.getmaxyx()
    curses.curs_set(False)
    canvas.nodelay(True)
    coroutines = get_stars(canvas, canvas_height, canvas_width, min_stars=100, max_stars=250)
    coroutines.append(fire(canvas, start_row=canvas_height // 2, start_column=canvas_width // 2, rows_speed=-0.05))
    coroutines.append(animate_spaceship(canvas, canvas_height // 2, canvas_width // 2, tic_timeout=0.3))
    while len(coroutines):
        sleep(0.001)
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
            except StopIteration:
                coroutines.remove(coroutine)
        canvas.refresh()


if __name__ == '__main__':
    curses.update_lines_cols()
    curses.wrapper(draw)
