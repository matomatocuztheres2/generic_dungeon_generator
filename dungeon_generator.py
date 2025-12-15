import math
import random
import sys

# Increase recursion limit for the backtracking algorithm.
sys.setrecursionlimit(2000)

# --- 1. CONFIGURATION CONSTANTS ---
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

# MAZE & ROOM TILE TYPES
TILE_HALLWAY_HORZ = "Horizontal_Hallway"
TILE_HALLWAY_VERT = "Vertical_Hallway"
TILE_OPEN_SPACE = "Open_Space"

# CONTAINER TILE TYPES
TILE_CHEST = "Loot_Chest"
TILE_BARREL = "Loot_Barrel"
TILE_CRATE = "Loot_Crate"

# Enemy Spawner Type
TILE_SPAWNER = "Enemy_Spawner"

## Maze Generation Variables (Integer IDs for internal logic)
MAZE_PASSAGE = 1  # ID for a path carved by backtracking or room connection
MAZE_WALL = 0  # ID for an unvisited wall/unclaimed space

# ROOM & CONTAINER GENERATION CONFIGURATION
ROOM_MIN_COUNT = 3
ROOM_MAX_COUNT = 8
ROOM_MIN_EXITS = 1
ROOM_MAX_EXITS = 4

# Fixed Room Dimensions (Width, Height in Tiles)
ROOM_DIMENSIONS_SMALL = [(2, 2), (2, 3), (3, 2)]
ROOM_DIMENSIONS_MEDIUM = [(2, 4), (4, 2), (3, 4), (4, 3), (4, 4)]
ROOM_DIMENSIONS_LARGE = [(3, 7), (7, 3), (4, 6), (6, 4), (5, 5), (5, 6), (6, 5), (6, 6)]

# LOOT GENERATION CONFIGURATION
BARREL_COUNT_MIN = 1
BARREL_COUNT_MAX = 8
CRATE_COUNT_MIN = 1
CRATE_COUNT_MAX = 8

# Outside Loot Configuration (Only Barrels/Crates)
OUTSIDE_LOOT_MIN = 2
OUTSIDE_LOOT_MAX = 6

# Enemy Spawner Configuration (Enemy spawner amount is user-controlled)
ENEMY_SPAWNER_COUNT = 2

# All gear is ranked from F (lowest) to S (highest).
GEAR_TIERS = ["F", "E", "D", "C", "B", "A", "S"] # List of gear tiers.
GEAR_TYPES = ["Weapon Part", "Armor Part", "Food", "Scroll", "Spell", "Card", "Trinket", "Junk"] # List of item types.

# Defines the base probability (d100) for rolling a specific tier for standard loot.
GEAR_TIER_WEIGHTS = {
    "S": 3,
    "A": 5,   # Reduced rarity to make it feel more valuable and align with extraction risk.
    "B": 15,
    "C": 25,
    "D": 25,
    "E": 20,
    "F": 7    # Increased slightly to maintain 100% total weight.
}

# Default loot count range for barrels and crates.
MIN_LOOT_ITEMS = 1
MAX_LOOT_ITEMS = 8


# --- 2. DIMENSION CALCULATION ---
GRID_COLUMNS = ROOM_WIDTH_PIXELS // TILE_SIZE_WIDTH
GRID_ROWS = ROOM_HEIGHT_PIXELS // TILE_SIZE_HEIGHT


# --- Helper Function for Logging Coordinates (Added for Stray Chest logging) ---

def get_tile_coordinates_str(r, c, tile_w, tile_h):
    # Converts grid position to pixel coordinates string.
    center_x = (c * tile_w) + (tile_w / 2)
    center_y = (r * tile_h) + (tile_h / 2)
    return f"({center_x:.0f}x, {center_y:.0f}y)"

# --- 3. INVENTORY AND LOOT SYSTEM ---

class InventoryManager:
    # Manages gear creation, tier rolling, and statistical attributes. (__init__)

    def __init__(self, tier_weights):
        # Initializes with tier weights.
        self.GEAR_STAT_IMPACTS = {}
        self.tier_weights = tier_weights
        self.GEAR_TIERS = GEAR_TIERS # Using the global constant

    def _roll_weighted_tier(self, min_tier, max_tier):
        # Rolls a single gear tier based on weights, constrained by min/max tiers. (_roll_weighted_tier)

        # 1. Determine the valid tiers based on min/max indices
        min_index = self.GEAR_TIERS.index(min_tier)
        max_index = self.GEAR_TIERS.index(max_tier)
        valid_tiers = self.GEAR_TIERS[min_index:max_index + 1]

        # 2. Filter weights and prepare for random.choices
        choices = []
        weights = []
        for tier in valid_tiers:
            if tier in self.tier_weights:
                choices.append(tier)
                weights.append(self.tier_weights[tier])

        # 3. Fallback: If no tiers are available, default to the lowest possible tier ("F")
        if not choices or sum(weights) == 0:
            return "F"

        # 4. Perform the weighted random choice
        try:
            rolled_tier = random.choices(choices, weights=weights, k=1)[0]
            return rolled_tier
        except ValueError:
            # Should not happen if weights are defined, but safety fallback is "F"
            return "F"

    def _roll_loot(self, min_count, max_count, min_tier, max_tier, is_chest=False):
        # Rolls gear for a container using weighted tiers. (_roll_loot)
        loot = []

        if is_chest:
            # CHEST LOGIC: Custom 80/20 A/S roll, plus weighted F-B rolls.

            # 1. Roll for high-tier items (A or S only), max 4 pieces
            high_count = random.randint(1, 4)
            for _ in range(high_count):
                # 20% S Tier, 80% A Tier, as specifically requested
                if random.random() < 0.20:
                    rolled_tier = "S"
                else:
                    rolled_tier = "A"

                loot.append(self.generate_gear(self.GEAR_TIERS.index(rolled_tier)))

            # 2. Roll for additional low-tier items (B tier and below)
            low_count = random.randint(0, 4)
            for _ in range(low_count):
                # Use general weighted system, constrained to F-B tiers
                rolled_tier = self._roll_weighted_tier("F", "B")
                loot.append(self.generate_gear(self.GEAR_TIERS.index(rolled_tier)))

            # Ensure total items <= MAX_LOOT_ITEMS (8)
            if len(loot) > MAX_LOOT_ITEMS:
                loot = random.sample(loot, MAX_LOOT_ITEMS)

        else:
            # BARRELS/CRATES LOGIC: Standard weighted roll F to A tier.
            total_count = random.randint(min_count, max_count) # Rolls total items.
            for _ in range(total_count):
                # Roll tier between min_tier (F) and max_tier (A) using weights.
                rolled_tier = self._roll_weighted_tier(min_tier, max_tier)
                loot.append(self.generate_gear(self.GEAR_TIERS.index(rolled_tier)))

        return loot

    def generate_gear(self, tier_index):
        # Creates a single gear dictionary item. (generate_gear)
        tier = self.GEAR_TIERS[tier_index] # Gets tier string from index.
        item_type = random.choice(GEAR_TYPES) # Randomly selects item type.

        gear_item = {
            "tier": tier,
            "type": item_type,
            "name": f"{tier} Tier {item_type}",
            "stats": self.GEAR_STAT_IMPACTS.get(item_type, "No defined stats yet") # Uses stat placeholder.
        }
        return gear_item


class LootContainer:
    # Base class for all loot containers in a room. (LootContainer)

    def __init__(self, inventory_manager):
        # Initializes the container with the manager. (LootContainer)
        self.manager = inventory_manager

    def generate_loot(self):
        # Must be implemented by derived classes. (generate_loot)
        raise NotImplementedError("Subclasses must implement generate_loot.")


class LootChest(LootContainer):
    # Chest: Spawns in large rooms, contains B-S tier gear. (LootChest)

    SPAWN_CHANCE = 0.20
    LOOT_TIER_MIN = "B"
    LOOT_TIER_MAX = "S"

    def generate_loot(self):
        # Generates 1-8 items (1-4 A/S + 0-4 F-B weighted). (LootChest)
        return self.manager._roll_loot(
            min_count=MIN_LOOT_ITEMS,
            max_count=MAX_LOOT_ITEMS,
            min_tier=self.LOOT_TIER_MIN,
            max_tier=self.LOOT_TIER_MAX,
            is_chest=True
        )


class LootBarrel(LootContainer):
    # Barrel: Spawns in any room/hallway, contains F-A tier gear. (LootBarrel)

    LOOT_TIER_MIN = "F"
    LOOT_TIER_MAX = "A"
    FIXED_LOOT_COUNT = 4

    def generate_loot(self):
        # Generates 4 items (F-A tier, weighted). (LootBarrel)
        return self.manager._roll_loot(
            min_count=self.FIXED_LOOT_COUNT,
            max_count=self.FIXED_LOOT_COUNT,
            min_tier=self.LOOT_TIER_MIN,
            max_tier=self.LOOT_TIER_MAX
        )


class LootCrate(LootContainer):
    # Crate: Spawns in any room/hallway, contains F-A tier gear. (LootCrate)

    LOOT_TIER_MIN = "F"
    LOOT_TIER_MAX = "A"
    FIXED_LOOT_COUNT = 6

    def generate_loot(self):
        # Generates 6 items (F-A tier, weighted). (LootCrate)
        return self.manager._roll_loot(
            min_count=self.FIXED_LOOT_COUNT,
            max_count=self.FIXED_LOOT_COUNT,
            min_tier=self.LOOT_TIER_MIN,
            max_tier=self.LOOT_TIER_MAX
        )


# --- 4. DUNGEON GENERATION CORE FUNCTIONS ---

def generate_initial_box_dungeon(rows, columns):
    # Initializes grid with a sealed wall box. (generate_initial_box_dungeon)
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
    # Fills the inner grid area with MAZE_WALL (0). (initialize_inner_grid)
    rows = len(dungeon_grid)
    columns = len(dungeon_grid[0])
    for r in range(1, rows - 1):
        for c in range(1, columns - 1):
            dungeon_grid[r][c] = MAZE_WALL
    return dungeon_grid


def recursive_backtracking_maze_generator(grid, r, c):
    # Recursively carves paths outwards. (recursive_backtracking_maze_generator)
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
    # Runs backtracking and converts IDs to tiles. (generate_hallways_in_remaining_space)
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

            # Check for existing room/loot tiles which should not be overwritten
            if isinstance(tile, str) and tile not in [MAZE_WALL, MAZE_PASSAGE]:
                continue

            if tile == MAZE_PASSAGE:
                dungeon_grid[r][c] = TILE_OPEN_SPACE
            elif tile == MAZE_WALL:
                # Determine wall type based on neighbors (paths, rooms, containers)
                is_passage_or_room = lambda tr, tc: dungeon_grid[tr][tc] in [
                    TILE_OPEN_SPACE, MAZE_PASSAGE, TILE_BARREL, TILE_CRATE, TILE_CHEST, TILE_SPAWNER
                ] or (isinstance(dungeon_grid[tr][tc], str) and dungeon_grid[tr][tc].endswith("Wall"))


                has_passage_N = r > 0 and is_passage_or_room(r - 1, c)
                has_passage_S = r < rows - 1 and is_passage_or_room(r + 1, c)
                has_passage_W = c > 0 and is_passage_or_room(r, c - 1)
                has_passage_E = c < columns - 1 and is_passage_or_room(r, c + 1)

                # Check for vertical or horizontal alignment
                if (has_passage_N or has_passage_S) and not (has_passage_W or has_passage_E):
                    dungeon_grid[r][c] = TILE_HALLWAY_VERT
                elif (has_passage_W or has_passage_E) and not (has_passage_N or has_passage_S):
                    dungeon_grid[r][c] = TILE_HALLWAY_HORZ
                else:
                    dungeon_grid[r][c] = TILE_OPEN_SPACE

    return dungeon_grid, start_r, start_c


# --- 5. ROOM AND CONTAINER PLACEMENT LOGIC ---

def place_containers_in_room(grid, start_r, start_c, width, height, room_type, inventory_manager, placed_loot):
    """Identifies open tiles and places containers in a room. (place_containers_in_room)"""
    end_r = start_r + height - 1
    end_c = start_c + width - 1

    open_tiles = []
    # Only check interior tiles for placement (1 tile in from the wall)
    for r in range(start_r + 1, end_r):
        for c in range(start_c + 1, end_c):
            if grid[r][c] == TILE_OPEN_SPACE:
                open_tiles.append((r, c))

    random.shuffle(open_tiles)

    tiles_used = 0

    # 1. Chest Placement (Large Rooms Only)
    if room_type == "Large" and random.random() < LootChest.SPAWN_CHANCE:
        if open_tiles and tiles_used < len(open_tiles):
            r, c = open_tiles[tiles_used]
            grid[r][c] = TILE_CHEST

            chest = LootChest(inventory_manager)
            loot_data = chest.generate_loot()

            placed_loot.append({
                "type": "Chest",
                "row": r,
                "column": c,
                "loot": loot_data
            })
            tiles_used += 1

    # 2. Barrel Placement (Reduced by half for in-room placement)
    # The max is BARREL_COUNT_MAX // 2, minimum is BARREL_COUNT_MIN (1)
    max_barrels_in_room = BARREL_COUNT_MAX // 2 if BARREL_COUNT_MAX > 1 else 1
    num_barrels = random.randint(BARREL_COUNT_MIN, max_barrels_in_room)

    for _ in range(num_barrels):
        if open_tiles and tiles_used < len(open_tiles):
            r, c = open_tiles[tiles_used]
            grid[r][c] = TILE_BARREL

            barrel = LootBarrel(inventory_manager)
            loot_data = barrel.generate_loot()

            placed_loot.append({
                "type": "Barrel",
                "row": r,
                "column": c,
                "loot": loot_data
            })
            tiles_used += 1
        else:
            break

    # 3. Crate Placement (Reduced by half for in-room placement)
    # The max is CRATE_COUNT_MAX // 2, minimum is CRATE_COUNT_MIN (1)
    max_crates_in_room = CRATE_COUNT_MAX // 2 if CRATE_COUNT_MAX > 1 else 1
    num_crates = random.randint(CRATE_COUNT_MIN, max_crates_in_room)

    for _ in range(num_crates):
        if open_tiles and tiles_used < len(open_tiles):
            r, c = open_tiles[tiles_used]
            grid[r][c] = TILE_CRATE

            crate = LootCrate(inventory_manager)
            loot_data = crate.generate_loot()

            placed_loot.append({
                "type": "Crate",
                "row": r,
                "column": c,
                "loot": loot_data
            })
            tiles_used += 1
        else:
            break

    return grid

# --- Rare Stray Chest Spawning ---
def spawn_stray_chest_if_lucky(grid, inventory_manager, placed_loot):
    """
    Implements the 1% chance for a Chest to spawn in any truly open tile
    (hallways or rooms that haven't been used by fixed loot/spawners).
    """
    STRAY_CHANCE = 0.01  # 1% chance

    # 1. Check the 1% chance
    if random.random() < STRAY_CHANCE:

        # 2. Find all truly empty floor tiles
        # Tiles that are still 'open' after all room/hallway/standard loot placement.
        valid_floor_tiles = [TILE_OPEN_SPACE, TILE_HALLWAY_HORZ, TILE_HALLWAY_VERT]
        potential_spots = []
        rows, cols = len(grid), len(grid[0])

        for r in range(1, rows - 1):
            for c in range(1, cols - 1):
                # We are looking for tiles that have not been used by walls, corners,
                # or existing containers/spawners.
                if grid[r][c] in valid_floor_tiles:
                    potential_spots.append((r, c))

        if not potential_spots:
            return grid, False

        # 3. Select a random empty tile
        r, c = random.choice(potential_spots)

        # 4. Place the Chest and generate its specialized loot
        grid[r][c] = TILE_CHEST

        chest = LootChest(inventory_manager)
        loot_data = chest.generate_loot()

        # 5. Add to the loot summary with a special marker
        placed_loot.append({
            "type": "Chest [RARE STRAY CHEST]",
            "row": r,
            "column": c,
            "loot": loot_data
        })

        print(f"[RARE LOOT] Stray Chest placed at {get_tile_coordinates_str(r, c, TILE_SIZE_WIDTH, TILE_SIZE_HEIGHT)}")
        return grid, True

    return grid, False


def place_outside_loot(grid, inventory_manager, placed_loot):
    #Places Barrels/Crates (place_outside_loot)
    valid_tiles = [TILE_OPEN_SPACE, TILE_HALLWAY_HORZ, TILE_HALLWAY_VERT]

    potential_spots = []
    rows, cols = len(grid), len(grid[0])
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            if grid[r][c] in valid_tiles:
                potential_spots.append((r, c))

    random.shuffle(potential_spots)

    num_to_place = random.randint(OUTSIDE_LOOT_MIN, OUTSIDE_LOOT_MAX)
    placed_count = 0

    for r, c in potential_spots:
        if placed_count >= num_to_place: break

        container_type = random.choice(["Barrel", "Crate"])

        if container_type == "Barrel":
            container = LootBarrel(inventory_manager)
            loot_data = container.generate_loot()
            grid[r][c] = TILE_BARREL
        else: # Crate
            container = LootCrate(inventory_manager)
            loot_data = container.generate_loot()
            grid[r][c] = TILE_CRATE

        placed_loot.append({
            "type": container_type,
            "row": r,
            "column": c,
            "loot": loot_data
        })
        placed_count += 1

    return grid

def place_enemy_spawners(grid, spawner_count):
    # Places enemy spawners on any available open tile. (place_enemy_spawners)
    # Spawners can be placed on open space, hallways, or inside empty rooms.
    valid_tiles = [TILE_OPEN_SPACE, TILE_HALLWAY_HORZ, TILE_HALLWAY_VERT]

    potential_spots = []
    rows, cols = len(grid), len(grid[0])
    for r in range(1, rows - 1):
        for c in range(1, cols - 1):
            # Place only on tiles that are not walls/corners/loot containers
            if grid[r][c] in valid_tiles:
                potential_spots.append((r, c))

    random.shuffle(potential_spots)

    placed_count = 0
    spawner_locations = []

    for r, c in potential_spots:
        if placed_count >= spawner_count: break

        grid[r][c] = TILE_SPAWNER
        spawner_locations.append({
            'row': r,
            'column': c,
            'center_x_pixels': (c * TILE_SIZE_WIDTH) + (TILE_SIZE_WIDTH / 2),
            'center_y_pixels': (r * TILE_SIZE_HEIGHT) + (TILE_SIZE_HEIGHT / 2)
        })
        placed_count += 1

    return grid, spawner_locations


# --- Room Carving Functions ---

def carve_small_room(grid, start_r, start_c, width, height, exits_required, inventory_manager, placed_loot):
    """Carves a Small Room and places containers. (carve_small_room)"""
    end_r = start_r + height - 1
    end_c = start_c + width - 1
    # Perimeter Carving Logic
    for r in range(start_r, start_r + height):
        for c in range(start_c, start_c + width):
            is_border = (r == start_r or r == end_r or c == start_c or c == end_c)
            is_corner = ((r == start_r and c == start_c) or (r == start_r and c == end_c) or (r == end_r and c == start_c) or (r == end_r and c == end_c))
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
            else: grid[r][c] = TILE_OPEN_SPACE

    # Exit Placement Logic
    wall_tiles = []
    for c in range(start_c + 1, end_c): wall_tiles.extend([(start_r, c), (end_r, c)])
    for r in range(start_r + 1, end_r): wall_tiles.extend([(r, start_c), (r, end_c)])
    random.shuffle(wall_tiles)
    placed_exits = 0
    for r, c in wall_tiles:
        if placed_exits >= exits_required: break
        grid[r][c] = TILE_OPEN_SPACE
        placed_exits += 1

    # Place Containers
    grid = place_containers_in_room(grid, start_r, start_c, width, height, "Small", inventory_manager, placed_loot)
    return grid

def carve_medium_room(grid, start_r, start_c, width, height, exits_required, inventory_manager, placed_loot):
    """Carves a Medium Room, interior walls, places containers. (carve_medium_room)"""
    # Carve perimeter and place initial containers (Small Room logic)
    grid = carve_small_room(grid, start_r, start_c, width, height, exits_required, inventory_manager, placed_loot)

    end_r = start_r + height - 1
    end_c = start_c + width - 1
    inner_start_r, inner_start_c = start_r + 1, start_c + 1
    inner_height, inner_width = height - 2, width - 2

    # Interior Wall Logic
    if inner_width >= 2 and inner_height >= 2:
        num_interior_walls = random.randint(1, 3)
        for _ in range(num_interior_walls):
            is_horizontal = random.choice([True, False])
            if is_horizontal:
                wall_r = random.randint(inner_start_r, inner_start_r + inner_height - 1)
                for c in range(inner_start_c, inner_start_c + inner_width):
                    if grid[wall_r][c] == TILE_OPEN_SPACE:
                         grid[wall_r][c] = TILE_HALLWAY_HORZ
            else:
                wall_c = random.randint(inner_start_c, inner_start_c + inner_width - 1)
                for r in range(inner_start_r, inner_start_r + inner_height):
                    if grid[r][wall_c] == TILE_OPEN_SPACE:
                        grid[r][wall_c] = TILE_HALLWAY_VERT

    # Re-run container placement to use remaining open space after wall carving
    grid = place_containers_in_room(grid, start_r, start_c, width, height, "Medium", inventory_manager, placed_loot)
    return grid

def carve_large_room(grid, start_r, start_c, width, height, exits_required, inventory_manager, placed_loot):
    """Carves a Large Room, sub-room, places containers. (carve_large_room)"""
    # Carve perimeter and place initial containers (Small Room logic)
    grid = carve_small_room(grid, start_r, start_c, width, height, exits_required, inventory_manager, placed_loot)

    inner_start_r, inner_start_c = start_r + 1, start_c + 1
    inner_height, inner_width = height - 2, width - 2

    # Interior Wall Logic (Same as Medium)
    if inner_width >= 2 and inner_height >= 2:
        num_interior_walls = random.randint(1, 3)
        for _ in range(num_interior_walls):
            is_horizontal = random.choice([True, False])
            if is_horizontal:
                wall_r = random.randint(inner_start_r, inner_start_r + inner_height - 1)
                for c in range(inner_start_c, inner_start_c + inner_width):
                    if grid[wall_r][c] == TILE_OPEN_SPACE:
                        grid[wall_r][c] = TILE_HALLWAY_HORZ
            else:
                wall_c = random.randint(inner_start_c, inner_start_c + inner_width - 1)
                for r in range(inner_start_r, inner_start_r + inner_height):
                    if grid[r][wall_c] == TILE_OPEN_SPACE:
                        grid[r][wall_c] = TILE_HALLWAY_VERT

    # Sub-Room Placement Logic
    sub_width, sub_height = random.choice(ROOM_DIMENSIONS_SMALL)
    inner_possible_starts = []
    for r in range(inner_start_r, inner_start_r + inner_height - sub_height + 1):
        for c in range(inner_start_c, inner_start_c + inner_width - sub_width + 1):
            inner_possible_starts.append((r, c))
    random.shuffle(inner_possible_starts)
    for sub_r, sub_c in inner_possible_starts:
        is_clear_for_sub = True
        for r_check in range(sub_r, sub_r + sub_height):
            for c_check in range(sub_c, sub_c + sub_width):
                if grid[r_check][c_check] != TILE_OPEN_SPACE:
                    is_clear_for_sub = False; break
            if not is_clear_for_sub: break
        if is_clear_for_sub:
            # Place the sub-room (recursively calls carve_small_room)
            grid = carve_small_room(grid, sub_r, sub_c, sub_width, sub_height, exits_required=1, inventory_manager=inventory_manager, placed_loot=placed_loot)
            break

    # Place Containers in the main large room space
    grid = place_containers_in_room(grid, start_r, start_c, width, height, "Large", inventory_manager, placed_loot)
    return grid

# --- Room Finding/Connecting Logic ---

def generate_rooms_data():
    """Generates a list of dictionaries defining room parameters. (generate_rooms_data)"""
    rooms_data = []
    num_rooms = random.randint(ROOM_MIN_COUNT, ROOM_MAX_COUNT)
    for i in range(num_rooms):
        roll = random.random()
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
    """Checks if a rectangular area contains only MAZE_WALL (0). (is_area_clear)"""
    rows = len(grid)
    cols = len(grid[0])
    # Ensure room is within the non-border area
    if (start_r < 1 or start_c < 1 or start_r + height > rows - 1 or start_c + width > cols - 1): return False
    for r in range(start_r, start_r + height):
        for c in range(start_c, start_c + width):
            if grid[r][c] != MAZE_WALL: return False
    return True

def find_clear_area(grid, room_width, room_height):
    """Finds a suitable top-left starting coordinate (r, c). (find_clear_area)"""
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

def place_rooms_in_dungeon(dungeon_grid, rooms_data, inventory_manager, placed_loot):
    """Attempts to place the defined rooms into the dungeon grid. (place_rooms_in_dungeon)"""
    for room in rooms_data:
        start_r, start_c = find_clear_area(dungeon_grid, room['width'], room['height'])

        if start_r != -1:
            room['placed'] = True
            room['start_r'] = start_r
            room['start_c'] = start_c

            if room['type'] == "Small":
                dungeon_grid = carve_small_room(dungeon_grid, start_r, start_c, room['width'], room['height'], room['exits_required'], inventory_manager, placed_loot)
            elif room['type'] == "Medium":
                dungeon_grid = carve_medium_room(dungeon_grid, start_r, start_c, room['width'], room['height'], room['exits_required'], inventory_manager, placed_loot)
            elif room['type'] == "Large":
                dungeon_grid = carve_large_room(dungeon_grid, start_r, start_c, room['width'], room['height'], room['exits_required'], inventory_manager, placed_loot)

        else:
            print(f"[WARNING] Could not place Room ID {room['id']} ({room['type']}: {room['width']}x{room['height']}).")

    return dungeon_grid

def connect_rooms_to_hallways(grid, rooms_data):
    """Ensures every placed room's exit connects to the MAZE_WALL area. (connect_rooms_to_hallways)"""
    for room in rooms_data:
        if not room['placed']: continue
        start_r, start_c = room['start_r'], room['start_c']
        end_r = start_r + room['height'] - 1
        end_c = start_c + room['width'] - 1

        for r in range(start_r, end_r + 1):
            for c in range(start_c, end_c + 1):
                # Check for tiles on the perimeter that are now open space (i.e., carved exit)
                if grid[r][c] in [TILE_OPEN_SPACE, TILE_BARREL, TILE_CRATE, TILE_CHEST] and \
                   (r == start_r or r == end_r or c == start_c or c == end_c):
                    dr, dc = 0, 0
                    if r == start_r: dr = -1
                    elif r == end_r: dr = 1
                    elif c == start_c: dc = -1
                    elif c == end_c: dc = 1

                    connect_r, connect_c = r + dr, c + dc

                    if 1 <= connect_r < GRID_ROWS - 1 and 1 <= connect_c < GRID_COLUMNS - 1:
                        # If the tile outside the exit is MAZE_WALL (0), connect it with a path (1)
                        if grid[connect_r][connect_c] == MAZE_WALL:
                            grid[connect_r][connect_c] = MAZE_PASSAGE

    return grid


# --- 6. UTILITY FUNCTIONS (Printing & Data Conversion) ---

def process_final_loot_output(placed_loot, tile_w, tile_h):
    """Converts grid coordinates to pixel positions and formats loot. (process_final_loot_output)"""
    final_output = []
    CENTER_OFFSET_X = tile_w / 2
    CENTER_OFFSET_Y = tile_h / 2

    for container in placed_loot:
        r, c = container['row'], container['column']
        pixel_x = (c * tile_w) + CENTER_OFFSET_X
        pixel_y = (r * tile_h) + CENTER_OFFSET_Y

        # Extract gear tiers for concise display
        loot_summary = [
            {"tier": item['tier'], "name": item['name']}
            for item in container['loot']
        ]

        final_output.append({
            "container_type": container['type'],
            "x_position_pixels": pixel_x,
            "y_position_pixels": pixel_y,
            "total_loot_count": len(container['loot']),
            "loot_contents": loot_summary
        })

    return final_output

def grid_to_detailed_dictionary(grid, tile_w, tile_h):
    """Converts the 2D grid array into the final dictionary format. (grid_to_detailed_dictionary)"""
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


# --- 7. EXECUTION AND OUTPUT ---

def generate_dungeon_and_loot():
    """Main execution function runs all generation steps. (generate_dungeon_and_loot)"""

    # Initialize InventoryManager with the defined tier weights
    inventory_manager = InventoryManager(GEAR_TIER_WEIGHTS)
    placed_loot = []
    spawner_locations = []

    # 6.1. Generate the initial box structure
    dungeon_grid = generate_initial_box_dungeon(GRID_ROWS, GRID_COLUMNS)
    dungeon_grid = initialize_inner_grid(dungeon_grid)
    rooms_to_place = generate_rooms_data()

    print("Calculated Grid Size: %d Rows x %d Columns" % (GRID_ROWS, GRID_COLUMNS))
    print("--- Generated Room Parameters ---")
    for room in rooms_to_place:
        print(f"ID {room['id']} | Type: {room['type']:<6} | Size: {room['width']}x{room['height']} | Exits: {room['exits_required']}")

    # 6.4. Place Rooms and Loot (In-room loot is placed here)
    dungeon_grid = place_rooms_in_dungeon(dungeon_grid, rooms_to_place, inventory_manager, placed_loot)

    # 6.5. Connect Rooms to the Maze System
    dungeon_grid = connect_rooms_to_hallways(dungeon_grid, rooms_to_place)

    # 6.6. Generate Hallways (Backtracking fills the remaining MAZE_WALL gaps)
    dungeon_grid, _, _ = generate_hallways_in_remaining_space(dungeon_grid)

    # 6.6b. Place Enemy Spawners (Can be in rooms or hallways)
    dungeon_grid, spawner_locations = place_enemy_spawners(dungeon_grid, ENEMY_SPAWNER_COUNT)

    # 6.6c. Place Outside Loot (Barrels/Crates in hallways/open space)
    dungeon_grid = place_outside_loot(dungeon_grid, inventory_manager, placed_loot)

    # 6.6d. Place Rare Stray Chest (1% chance)
    dungeon_grid, _ = spawn_stray_chest_if_lucky(dungeon_grid, inventory_manager, placed_loot)


    # 6.7. Process and Print Loot Summary
    final_loot_data = process_final_loot_output(placed_loot, TILE_SIZE_WIDTH, TILE_SIZE_HEIGHT)

    print("\n--- FINAL LOOT PLACEMENT SUMMARY ---")
    if not final_loot_data:
        print("[WARNING] No loot containers were successfully placed in the dungeon.")

    for container in final_loot_data:
        x_pos = container['x_position_pixels']
        y_pos = container['y_position_pixels']
        count = container['total_loot_count']
        c_type = container['container_type']

        # Check if it is the rare stray chest for the printout
        is_stray = "[RARE STRAY CHEST]" in c_type
        clean_c_type = c_type.replace(" [RARE STRAY CHEST]", "")

        print(f"\n{clean_c_type}: ({x_pos:.0f}x, {y_pos:.0f}y) | Items: {count}{' [RARE STRAY CHEST]' if is_stray else ''}")
        for item in container['loot_contents']:
            print(f"  - {item['tier']} Tier: {item['name']}")

    print("\n--- FINAL ENEMY SPAWNER LOCATIONS ---")
    if not spawner_locations:
        print("[WARNING] No enemy spawners were placed.")
    else:
        for spawner in spawner_locations:
            print(f"Spawner: ({spawner['center_x_pixels']:.0f}x, {spawner['center_y_pixels']:.0f}y)")

    # 6.8. Print a visual representation of the dungeon grid
    print("\n--- Dungeon Grid Visual (Fully Generated) ---")
    tile_map = {
        "Top_Left_Corner": "╔", "Top_Right_Corner": "╗",
        "Bottom_Left_Corner": "╚", "Bottom_Right_Corner": "╝",
        "Top_Wall": "═", "Bottom_Wall": "═",
        "Left_Wall": "║", "Right_Wall": "║",
        "Horizontal_Hallway": "─",
        "Vertical_Hallway": "│",
        "Open_Space": " ",
        "Loot_Chest": "C", "Loot_Barrel": "B", "Loot_Crate": "K",
        TILE_SPAWNER: "S", # Spawner
        MAZE_WALL: "X", MAZE_PASSAGE: "."
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

    # 6.9. Convert to the final dictionary format
    dungeon_map_dict = grid_to_detailed_dictionary(dungeon_grid, TILE_SIZE_WIDTH, TILE_SIZE_HEIGHT)

    # 6.10. Print an example of the dictionary output (using focus tile)
    print("\n--- Example Dictionary Output (Focus Tile) ---")
    if (focus_r, focus_c) in dungeon_map_dict:
        print(dungeon_map_dict[(focus_r, focus_c)])
    else:
        # Fallback to a standard tile if no room was placed
        print(dungeon_map_dict[(1, 1)])

    return dungeon_map_dict, final_loot_data

# Execute the generation
generate_dungeon_and_loot()
