import random

GRID_W = 24
GRID_H = 18

EMPTY = 0
FOOD = 1
WOOD = 2

ACTIONS = ("up", "down", "left", "right", "eat", "gather", "rest")

ACTION_DELTAS = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


class SurvivalEnv:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.reset()

    def reset(self):
        self.grid = [
            [EMPTY for _ in range(GRID_W)]
            for _ in range(GRID_H)
        ]

        self.x = GRID_W // 2
        self.y = GRID_H // 2

        self.health = 100
        self.hunger = 20
        self.energy = 100

        self.food_inventory = 1
        self.wood_inventory = 0

        self.steps = 0
        self.done = False

        self._spawn_resources(32, 42)
        return self.get_state()

    def _spawn_resources(self, food_count, wood_count):
        cells = [
            (x, y)
            for y in range(GRID_H)
            for x in range(GRID_W)
            if (x, y) != (self.x, self.y)
        ]

        self.rng.shuffle(cells)

        for x, y in cells[:food_count]:
            self.grid[y][x] = FOOD

        for x, y in cells[food_count:food_count + wood_count]:
            self.grid[y][x] = WOOD

    def get_state(self):
        tile = self.grid[self.y][self.x]

        hunger_band = min(4, self.hunger // 25)
        energy_band = min(3, self.energy // 25)
        health_band = min(3, self.health // 25)
        inventory_band = min(2, self.food_inventory)

        nearby = []

        for resource in (FOOD, WOOD):
            found = any(
                0 <= self.x + dx < GRID_W
                and 0 <= self.y + dy < GRID_H
                and self.grid[self.y + dy][self.x + dx] == resource
                for dx, dy in (
                    (0, -1),
                    (0, 1),
                    (-1, 0),
                    (1, 0),
                )
            )
            nearby.append(int(found))

        return (
            tile,
            hunger_band,
            energy_band,
            health_band,
            inventory_band,
            nearby[0],
            nearby[1],
        )

    def step(self, action):
        if self.done:
            return self.get_state(), 0.0, True, {}

        name = ACTIONS[action]
        reward = -0.03
        self.steps += 1

        if name in ACTION_DELTAS:
            dx, dy = ACTION_DELTAS[name]
            nx = self.x + dx
            ny = self.y + dy

            if 0 <= nx < GRID_W and 0 <= ny < GRID_H:
                self.x = nx
                self.y = ny
            else:
                reward -= 0.2

            self.energy = max(0, self.energy - 2)

        elif name == "eat":
            if self.food_inventory > 0 and self.hunger > 0:
                self.food_inventory -= 1
                self.hunger = max(0, self.hunger - 45)
                reward += 1.0
            else:
                reward -= 0.15

            self.energy = max(0, self.energy - 1)

        elif name == "gather":
            tile = self.grid[self.y][self.x]

            if tile == FOOD:
                self.food_inventory = min(
                    2, self.food_inventory + 1
                )
                self.grid[self.y][self.x] = EMPTY
                reward += 1.5

            elif tile == WOOD:
                self.wood_inventory = min(
                    9, self.wood_inventory + 1
                )
                self.grid[self.y][self.x] = EMPTY
                reward += 0.5

            else:
                reward -= 0.2

            self.energy = max(0, self.energy - 3)

        elif name == "rest":
            self.energy = min(100, self.energy + 16)

        # Hunger increases as time passes.
        self.hunger = min(100, self.hunger + 1)

        # Low needs can cause damage.
        if self.hunger >= 75:
            damage = 2 if self.hunger >= 90 else 1
            self.health = max(0, self.health - damage)

        if self.energy <= 0:
            self.health = max(0, self.health - 1)

        # Resources occasionally regrow.
        if self.steps % 35 == 0:
            self._regrow_one_resource()

        # End the episode if the agent dies or survives long enough.
        if self.health <= 0:
            self.done = True
            reward -= 10.0

        elif self.steps >= 1200:
            self.done = True
            reward += 5.0

        info = {
            "action": name,
            "steps": self.steps,
            "health": self.health,
            "hunger": self.hunger,
            "energy": self.energy,
            "food": self.food_inventory,
            "wood": self.wood_inventory,
        }

        return self.get_state(), reward, self.done, info

    def _regrow_one_resource(self):
        cells = [
            (x, y)
            for y in range(GRID_H)
            for x in range(GRID_W)
            if self.grid[y][x] == EMPTY
        ]

        if cells:
            x, y = self.rng.choice(cells)

            if self.rng.random() < 0.45:
                self.grid[y][x] = FOOD
            else:
                self.grid[y][x] = WOOD
