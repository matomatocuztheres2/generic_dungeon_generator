import math
import random
import sys

# Increase recursion limit for the backtracking algorithm.
sys.setrecursionlimit(2000)

# --- 1. CONFIGURATION VARIABLES ---
# These variables control the dimensions and tile settings of the dungeon.

## Room Dimensions (Pixels)
ROOM_WIDTH_PIXELS = 3840
ROOM_HEIGHT_PIXELS = 2160

## Tile Dimensions (Pixels)
TILE_SIZE_WIDTH = 256
TILE_SIZE_HEIGHT = 256

## Tile Content/Names (Strings)
TILE_NO_WALL = "No_Wall"
TILE_CORNER_TL = "Top_Left_Corner"
TILE_CORNER_TR = "Top_Right_Corner"
TILE_CORNER_BL = "Bottom_Left_Corner"
TILE_CORNER_BR = "Bottom_Right_Corner"
TILE_WALL_TOP = "Top_Wall"
TILE_WALL_BOTTOM = "Bottom_Wall"
TILE_WALL_LEFT = "Left_Wall"
TILE_WALL_RIGHT = "Right_Wall"

# MAZE TILE TYPES
TILE_HALLWAY_HORZ = "Horizontal_Hallway" 
TILE_HALLWAY_VERT = "Vertical_Hallway" 
TILE_OPEN_SPACE = "Open_Space" 

## Maze Generation Variables (Integer IDs for internal logic)
MAZE_PASSAGE = 1  # ID for a path carved by backtracking or room connection
MAZE_WALL = 0  # ID for an unvisited wall/unclaimed space

# ROOM GENERATION CONFIGURATION
ROOM_MIN_COUNT = 3
ROOM_MAX_COUNT = 8
ROOM_MIN_EXITS = 1
ROOM_MAX_EXITS = 4

# --- NEW FIXED ROOM DIMENSIONS (Width, Height in Tiles) ---
ROOM_DIMENSIONS_SMALL = [(2, 2), (2, 3), (3, 2)]
ROOM_DIMENSIONS_MEDIUM = [(2, 4), (4, 2), (3, 4), (4, 3), (4, 4)]
ROOM_DIMENSIONS_LARGE = [(3, 7), (7, 3), (4, 6), (6, 4), (5, 5), (5, 6), (6, 5), (6, 6)]


# --- 2. DIMENSION CALCULATION ---
GRID_COLUMNS = ROOM_WIDTH_PIXELS // TILE_SIZE_WIDTH
GRID_ROWS = ROOM_HEIGHT_PIXELS // TILE_SIZE_HEIGHT

print(f"Calculated Grid Size: {GRID_ROWS} Rows x {GRID_COLUMNS} Columns")


# --- 3. DUNGEON GENERATION FUNCTIONS (Core Engine) ---

def generate_initial_box_dungeon(rows, columns):
    """Initializes a grid array and populates it with a sealed wall box."""
    dungeon = [[TILE_NO_WALL for _ in range(columns)] for _ in range(rows)]
    dungeon[0][0] = TILE_CORNER_TL
    dungeon[0][columns - 1] = TILE_CORNER_TR
    dungeon[rows - 1][0] = TILE_CORNER_BL
    dungeon[rows - 1][columns - 1] = TILE_CORNER_BR
    for r in range(rows):
        for c in range(columns):
            if r == 0 and 0 < c < columns - 1: dungeon[r][c] = TILE_WALL_TOP
            elif r == rows - 1 and 0 < c < columns - 1: dungeon[r][c] = TILE_WALL_BOTTOM
            elif c == 0 and 0 < r < rows - 1: dungeon[r][c] = TILE_WALL_LEFT
            elif c == columns - 1 and 0 < r < rows - 1: dungeon[r][c] = TILE_WALL_RIGHT
    return dungeon

def initialize_inner_grid(dungeon_grid):
    """Fills the inner grid area (1 to N-2) with the MAZE_WALL (0) marker."""
    rows = len(dungeon_grid)
    columns = len(dungeon_grid[0])
    for r in range(1, rows - 1):
        for c in range(1, columns - 1): 
            dungeon_grid[r][c] = MAZE_WALL
    return dungeon_grid


def recursive_backtracking_maze_generator(grid, r, c):
    """Recursively carves paths from the current cell (r, c) outwards."""
    grid[r][c] = MAZE_PASSAGE 
    directions = [(0, 2), (0, -2), (2, 0), (-2, 0)]
    random.shuffle(directions) 
    for dr, dc in directions:
        next_r, next_c = r + dr, c + dc
        wall_r, wall_c = r + dr // 2, c + dc // 2
        
        if 1 <= next_r < GRID_ROWS - 1 and 1 <= next_c < GRID_COLUMNS - 1:
            if grid[next_r][next_c] == MAZE_WALL:
                grid[wall_r][wall_c] = MAZE_PASSAGE 
                recursive_backtracking_maze_generator(grid, next_r, next_c)

def generate_hallways_in_remaining_space(dungeon_grid):
    """
    Runs the backtracking maze generator on remaining MAZE_WALL tiles,
    and converts all MAZE IDs to final tiles.
    """
    rows = len(dungeon_grid)
    columns = len(dungeon_grid[0])
    
    # 1. Run Recursive Backtracking on remaining MAZE_WALLs
    wall_starts = []
    for r in range(1, rows - 1, 2):
        for c in range(1, columns - 1, 2):
            if dungeon_grid[r][c] == MAZE_WALL:
                wall_starts.append((r, c))
    
    start_r, start_c = -1, -1 
    if wall_starts:
        start_r, start_c = random.choice(wall_starts)
        recursive_backtracking_maze_generator(dungeon_grid, start_r, start_c)
        
    # 2. Convert Maze IDs (0, 1) to final String Tile Names
    for r in range(1, rows - 1):
        for c in range(1, columns - 1):
            tile = dungeon_grid[r][c]
            
            if tile == MAZE_PASSAGE:
                dungeon_grid[r][c] = TILE_OPEN_SPACE
            elif tile == MAZE_WALL:
                is_passage_or_room = lambda tr, tc: dungeon_grid[tr][tc] in [TILE_OPEN_SPACE, MAZE_PASSAGE]
                
                has_passage_N = r > 0 and is_passage_or_room(r - 1, c)
                has_passage_S = r < rows - 1 and is_passage_or_room(r + 1, c)
                has_passage_W = c > 0 and is_passage_or_room(r, c - 1)
                has_passage_E = c < columns - 1 and is_passage_or_room(r, c + 1)
                
                if has_passage_N or has_passage_S:
                    dungeon_grid[r][c] = TILE_HALLWAY_VERT
                elif has_passage_W or has_passage_E:
                    dungeon_grid[r][c] = TILE_HALLWAY_HORZ
                else:
                    dungeon_grid[r][c] = TILE_OPEN_SPACE 
                    
    return dungeon_grid, start_r, start_c


# --- 4. ROOM GENERATION AND PLACEMENT LOGIC ---

def generate_rooms_data():
    """Generates a list of dictionaries defining the size, type, and required exits."""
    rooms_data = []
    num_rooms = random.randint(ROOM_MIN_COUNT, ROOM_MAX_COUNT)
    
    for i in range(num_rooms):
        roll = random.random()
        
        # Select dimensions based on the new fixed lists
        if roll < 0.33:
            room_type = "Small"
            room_width, room_height = random.choice(ROOM_DIMENSIONS_SMALL)
        elif roll < 0.66:
            room_type = "Medium"
            room_width, room_height = random.choice(ROOM_DIMENSIONS_MEDIUM)
        else:
            room_type = "Large"
            room_width, room_height = random.choice(ROOM_DIMENSIONS_LARGE)
            
        num_exits = random.randint(ROOM_MIN_EXITS, ROOM_MAX_EXITS)
        
        rooms_data.append({
            "id": i,
            "type": room_type,
            "width": room_width,
            "height": room_height,
            "exits_required": num_exits,
            "placed": False,
            "start_r": -1,
            "start_c": -1
        })
        
    return rooms_data

def is_area_clear(grid, start_r, start_c, width, height):
    """
    Checks if a rectangular area is valid and currently contains only 
    the initial MAZE_WALL (0) tiles.
    """
    rows = len(grid)
    cols = len(grid[0])
    
    # 1. Check if the area is within the inner grid bounds (1 to N-2)
    if (start_r < 1 or start_c < 1 or 
        start_r + height > rows - 1 or start_c + width > cols - 1):
        return False
    
    # 2. Check every tile in the proposed room area
    for r in range(start_r, start_r + height):
        for c in range(start_c, start_c + width):
            if grid[r][c] != MAZE_WALL:
                return False 
    
    return True

def find_clear_area(grid, room_width, room_height):
    """Attempts to find a suitable top-left starting coordinate (r, c)."""
    rows = len(grid)
    cols = len(grid[0])
    
    possible_starts = []
    for r in range(1, rows - room_height):
        for c in range(1, cols - room_width):
            possible_starts.append((r, c))
            
    random.shuffle(possible_starts)
    
    for start_r, start_c in possible_starts:
        if is_area_clear(grid, start_r, start_c, room_width, room_height):
            return start_r, start_c
            
    return -1, -1

def carve_small_room(grid, start_r, start_c, width, height, exits_required):
    """Carves and places a Small Room (no interior walls) at the given coordinates."""
    end_r = start_r + height - 1
    end_c = start_c + width - 1
    
    for r in range(start_r, start_r + height):
        for c in range(start_c, start_c + width):
            
            is_border = (r == start_r or r == end_r or 
                         c == start_c or c == end_c)
            is_corner = ((r == start_r and c == start_c) or 
                         (r == start_r and c == end_c) or
                         (r == end_r and c == start_c) or 
                         (r == end_r and c == end_c))

            if is_corner:
                if r == start_r and c == start_c: grid[r][c] = TILE_CORNER_TL
                elif r == start_r and c == end_c: grid[r][c] = TILE_CORNER_TR
                elif r == end_r and c == start_c: grid[r][c] = TILE_CORNER_BL
                elif r == end_r and c == end_c: grid[r][c] = TILE_CORNER_BR
            elif is_border:
                if r == start_r: grid[r][c] = TILE_WALL_TOP
                elif r == end_r: grid[r][c] = TILE_WALL_BOTTOM
                elif c == start_c: grid[r][c] = TILE_WALL_LEFT
                elif c == end_c: grid[r][c] = TILE_WALL_RIGHT
            else:
                # Fill Interior 
                grid[r][c] = TILE_OPEN_SPACE

    # Place Exits (randomly replace wall tiles with open space)
    wall_tiles = []
    for c in range(start_c + 1, end_c):
        wall_tiles.append((start_r, c))
        wall_tiles.append((end_r, c))
    for r in range(start_r + 1, end_r):
        wall_tiles.append((r, start_c))
        wall_tiles.append((r, end_c))

    random.shuffle(wall_tiles)
    
    placed_exits = 0
    for r, c in wall_tiles:
        if placed_exits >= exits_required:
            break
        grid[r][c] = TILE_OPEN_SPACE
        placed_exits += 1
        
    return grid

def carve_medium_room(grid, start_r, start_c, width, height, exits_required):
    """Carves and places a Medium Room (with interior walls, no sub-rooms)."""
    # 1. Place Perimeter and Exits (Same as Small Room)
    grid = carve_small_room(grid, start_r, start_c, width, height, exits_required)
    
    # 2. Add Interior Walls
    end_r = start_r + height - 1
    end_c = start_c + width - 1
    inner_start_r, inner_start_c = start_r + 1, start_c + 1
    inner_height, inner_width = height - 2, width - 2

    if inner_width >= 2 and inner_height >= 2:
        num_interior_walls = random.randint(1, 3) 
        
        for _ in range(num_interior_walls):
            is_horizontal = random.choice([True, False])
            
            if is_horizontal:
                wall_r = random.randint(inner_start_r, inner_start_r + inner_height - 1)
                for c in range(inner_start_c, inner_start_c + inner_width):
                    grid[wall_r][c] = TILE_HALLWAY_HORZ
            else:
                wall_c = random.randint(inner_start_c, inner_start_c + inner_width - 1)
                for r in range(inner_start_r, inner_start_r + inner_height):
                    grid[r][wall_c] = TILE_HALLWAY_VERT

    return grid

def carve_large_room(grid, start_r, start_c, width, height, exits_required):
    """Carves and places a Large Room (with interior walls and up to one small sub-room)."""
    # 1. Place Perimeter and Exits (Same as Small Room)
    grid = carve_small_room(grid, start_r, start_c, width, height, exits_required)
    
    # Define interior bounds
    inner_start_r, inner_start_c = start_r + 1, start_c + 1
    inner_height, inner_width = height - 2, width - 2
    
    # 2. Add Interior Walls (Same logic as Medium Room)
    if inner_width >= 2 and inner_height >= 2:
        num_interior_walls = random.randint(1, 3) 
        for _ in range(num_interior_walls):
            is_horizontal = random.choice([True, False])
            
            if is_horizontal:
                wall_r = random.randint(inner_start_r, inner_start_r + inner_height - 1)
                for c in range(inner_start_c, inner_start_c + inner_width):
                    grid[wall_r][c] = TILE_HALLWAY_HORZ
            else:
                wall_c = random.randint(inner_start_c, inner_start_c + inner_width - 1)
                for r in range(inner_start_r, inner_start_r + inner_height):
                    grid[r][wall_c] = TILE_HALLWAY_VERT

    # 3. Place Sub-Room (Up to one small room)
    # We select a sub-room size from the small room list
    sub_width, sub_height = random.choice(ROOM_DIMENSIONS_SMALL) 
    
    inner_possible_starts = []
    # Loop over the interior space, ensuring the sub-room (plus its perimeter) fits
    for r in range(inner_start_r, inner_start_r + inner_height - sub_height + 1):
        for c in range(inner_start_c, inner_start_c + inner_width - sub_width + 1):
            inner_possible_starts.append((r, c))
    
    random.shuffle(inner_possible_starts)
    
    for sub_r, sub_c in inner_possible_starts:
        is_clear_for_sub = True
        for r_check in range(sub_r, sub_r + sub_height):
            for c_check in range(sub_c, sub_c + sub_width):
                # Check if the space is TILE_OPEN_SPACE (unblocked by interior walls)
                if grid[r_check][c_check] != TILE_OPEN_SPACE:
                    is_clear_for_sub = False
                    break
            if not is_clear_for_sub: break
            
        if is_clear_for_sub:
            # Sub-room exits are fixed at 1 for simplicity
            grid = carve_small_room(grid, sub_r, sub_c, sub_width, sub_height, exits_required=1)
            break
    
    return grid

def place_rooms_in_dungeon(dungeon_grid, rooms_data):
    """Attempts to place the defined rooms into the dungeon grid."""
    for room in rooms_data:
        start_r, start_c = find_clear_area(
            dungeon_grid, room['width'], room['height']
        )

        if start_r != -1:
            room['placed'] = True
            room['start_r'] = start_r
            room['start_c'] = start_c
            
            if room['type'] == "Small":
                dungeon_grid = carve_small_room(
                    dungeon_grid, start_r, start_c, 
                    room['width'], room['height'], room['exits_required']
                )
            elif room['type'] == "Medium":
                dungeon_grid = carve_medium_room(
                    dungeon_grid, start_r, start_c, 
                    room['width'], room['height'], room['exits_required']
                )
            elif room['type'] == "Large":
                dungeon_grid = carve_large_room(
                    dungeon_grid, start_r, start_c, 
                    room['width'], room['height'], room['exits_required']
                )
            
        else:
            print(f"[WARNING] Could not place Room ID {room['id']} ({room['type']}: {room['width']}x{room['height']}).")

    return dungeon_grid


def connect_rooms_to_hallways(grid, rooms_data):
    """
    Ensures every placed room's exit connects to the MAZE_WALL area 
    by carving a single MAZE_PASSAGE cell outside the exit.
    """
    
    for room in rooms_data:
        if not room['placed']:
            continue
            
        start_r, start_c = room['start_r'], room['start_c']
        end_r = start_r + room['height'] - 1
        end_c = start_c + room['width'] - 1
        
        # Iterate over the room's perimeter (walls and exits)
        for r in range(start_r, end_r + 1):
            for c in range(start_c, end_c + 1):
                
                # We only care about exits, which are TILE_OPEN_SPACE on the border
                if grid[r][c] == TILE_OPEN_SPACE and \
                   (r == start_r or r == end_r or c == start_c or c == end_c):
                    
                    # Determine the adjacent tile outside the room
                    dr, dc = 0, 0
                    if r == start_r: dr = -1  # Top wall, connect up
                    elif r == end_r: dr = 1   # Bottom wall, connect down
                    elif c == start_c: dc = -1 # Left wall, connect left
                    elif c == end_c: dc = 1  # Right wall, connect right
                    
                    connect_r, connect_c = r + dr, c + dc
                    
                    # Check if the connection point is valid (inside the permanent box)
                    if 1 <= connect_r < GRID_ROWS - 1 and 1 <= connect_c < GRID_COLUMNS - 1:
                        # Only carve if the space is still MAZE_WALL (0)
                        if grid[connect_r][connect_c] == MAZE_WALL:
                            # Carve a path: this is the connection point
                            grid[connect_r][connect_c] = MAZE_PASSAGE
                            
    return grid


# --- 5. UTILITY FUNCTION: GRID TO DICTIONARY (Unchanged) ---

def grid_to_detailed_dictionary(grid, tile_w, tile_h):
    """Converts the 2D grid array into the final dictionary format."""
    detailed_dict = {}
    rows = len(grid)
    cols = len(grid[0])
    CENTER_OFFSET_X = tile_w / 2
    CENTER_OFFSET_Y = tile_h / 2
    for r in range(rows):
        for c in range(cols):
            tile_name = grid[r][c]
            pixel_x = (c * tile_w) + CENTER_OFFSET_X
            pixel_y = (r * tile_h) + CENTER_OFFSET_Y
            key = (r, c)
            detailed_dict[key] = {
                "tile_name": tile_name,
                "row": r,
                "column": c,
                "center_x_pixels": pixel_x,
                "center_y_pixels": pixel_y
            }
    return detailed_dict


# --- 6. EXECUTION AND OUTPUT ---

# 6.1. Generate the initial box structure
dungeon_grid = generate_initial_box_dungeon(GRID_ROWS, GRID_COLUMNS)

# 6.2. Initialize the inner area with MAZE_WALL (0)
dungeon_grid = initialize_inner_grid(dungeon_grid)

# 6.3. Generate Room Parameters
rooms_to_place = generate_rooms_data()
print("--- Generated Room Parameters ---")
for room in rooms_to_place:
    print(f"ID {room['id']} | Type: {room['type']:<6} | Size: {room['width']}x{room['height']} | Exits: {room['exits_required']}")


# 6.4. Place Rooms (Small, Medium, and Large rooms carve the MAZE_WALL canvas)
dungeon_grid = place_rooms_in_dungeon(dungeon_grid, rooms_to_place)

# 6.5. Connect Rooms to the Maze System 
dungeon_grid = connect_rooms_to_hallways(dungeon_grid, rooms_to_place)

# 6.6. Generate Hallways (Backtracking fills the remaining MAZE_WALL gaps)
dungeon_grid, _, _ = generate_hallways_in_remaining_space(dungeon_grid)


# 6.7. Print a visual representation of the dungeon grid
print("\n--- Dungeon Grid Visual (Fully Generated) ---")
tile_map = {
    "Top_Left_Corner": "╔", "Top_Right_Corner": "╗",
    "Bottom_Left_Corner": "╚", "Bottom_Right_Corner": "╝",
    "Top_Wall": "═", "Bottom_Wall": "═",
    "Left_Wall": "║", "Right_Wall": "║",
    "Horizontal_Hallway": "─", 
    "Vertical_Hallway": "│",   
    "Open_Space": " " ,
    # Fallback for remaining IDs (should be none in final state)
    MAZE_WALL: "X", 
    MAZE_PASSAGE: "." 
}

# Find the center of the first placed room (for visualization focus)
first_placed_room = next((r for r in rooms_to_place if r['placed']), None)
focus_r, focus_c = (first_placed_room['start_r'], first_placed_room['start_c']) if first_placed_room else (-1, -1)

for r in range(GRID_ROWS):
    row_output = "".join([
        'R' if r == focus_r and c == focus_c else tile_map.get(dungeon_grid[r][c], "?") 
        for c in range(GRID_COLUMNS)
    ])
    print(f"R{r:02}: {row_output}")


# 6.8. Convert to the final dictionary format
dungeon_map_dict = grid_to_detailed_dictionary(
    dungeon_grid, TILE_SIZE_WIDTH, TILE_SIZE_HEIGHT
)

# 6.9. Print an example of the dictionary output
print("\n--- Example Dictionary Output (Focus Tile) ---")
if (focus_r, focus_c) in dungeon_map_dict:
    print(dungeon_map_dict[(focus_r, focus_c)])
else:
    print("Could not find start tile for first placed room in dictionary.")