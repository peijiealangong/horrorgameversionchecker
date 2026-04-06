import pygame, sys, random, math, os
from dataclasses import dataclass
#pyinstaller --onefile --icon="icon.ico" horrorgameforida.py 

# -------------------------------------------------------------------
# INITIAL SETUP
# -------------------------------------------------------------------
pygame.init()

FULLSCREEN = False
if FULLSCREEN:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((1280, 720))

WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Horror Arena - By Peijie Alan Gong")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont(None, 20)
BIG = pygame.font.SysFont(None, 44)
MID = pygame.font.SysFont(None, 28)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (18, 18, 20)
GRAY = (90, 90, 90)
LIGHT_GRAY = (140, 140, 140)
RED = (200, 40, 40)
GREEN = (40, 200, 80)
YELLOW = (240, 220, 60)
ORANGE = (255, 140, 0)
BLUE = (60, 140, 240)
PANEL = (28, 28, 34)

PROGRESS_FILE = "progress.txt"
GAME_VERSION = "v1.1.4"

# -------------------------------------------------------------------
# UTILS
# -------------------------------------------------------------------
def draw_text(surf, text, pos, color=WHITE, font=FONT):
    surf.blit(font.render(str(text), True, color), (int(pos[0]), int(pos[1])))


def draw_centered_text(surf, text, rect, color=WHITE, font=FONT):
    r = font.render(str(text), True, color)
    surf.blit(r, (rect.x + (rect.width - r.get_width()) // 2,
                  rect.y + (rect.height - r.get_height()) // 2))


def clamp(v, a, b):
    return max(a, min(b, v))


# -------------------------------------------------------------------
# BUTTON
# -------------------------------------------------------------------
@dataclass
class Button:
    rect: pygame.Rect
    label: str
    color: tuple = PANEL
    hover_color: tuple = LIGHT_GRAY
    text_color: tuple = WHITE
    enabled: bool = True

    def draw(self, surf):
        mpos = pygame.mouse.get_pos()
        base_col = self.color if self.enabled else (50, 50, 50)
        col = self.hover_color if self.enabled and self.rect.collidepoint(mpos) else base_col
        pygame.draw.rect(surf, col, self.rect)
        pygame.draw.rect(surf, GRAY, self.rect, 2)
        draw_centered_text(surf, self.label, self.rect,
                           self.text_color if self.enabled else (120, 120, 120))

    def clicked(self, event):
        return (
            self.enabled and
            event.type == pygame.MOUSEBUTTONDOWN and
            event.button == 1 and
            self.rect.collidepoint(event.pos)
        )


# -------------------------------------------------------------------
# GAME ENTITIES
# -------------------------------------------------------------------
@dataclass
class Player:
    pos: pygame.Vector2
    color: tuple = WHITE
    radius: int = 14
    base_speed: float = 2.6
    hp: float = 500.0
    max_hp: float = 500.0
    gold: int = 100
    xp: int = 0
    level: int = 1
    battery: float = 100.0
    stamina: float = 100.0
    damage: float = 20.0
    alive: bool = True
    inventory: list = None
    ability_cd: dict = None
    ability_max_cd: dict = None
    ability_level: dict = None
    food: float = 100.0
    food_decay_rate: float = 0.02
    food_regen_threshold_fast: float = 80.0
    food_regen_threshold_slow: float = 50.0
    out_of_combat_timer: float = 0.0

    def __post_init__(self):
        if self.inventory is None:
            self.inventory = []
        if self.ability_cd is None:
            self.ability_cd = {"Z": 0.0, "X": 0.0, "C": 0.0}
        if self.ability_max_cd is None:
            self.ability_max_cd = {"Z": 5.0, "X": 8.0, "C": 12.0}
        if self.ability_level is None:
            self.ability_level = {"Z": 1, "X": 1, "C": 1}

    def move(self, vel, walls):
        new = self.pos + vel
        rect = pygame.Rect(int(new.x - self.radius), int(new.y - self.radius),
                           self.radius * 2, self.radius * 2)
        for w in walls:
            if rect.colliderect(w):
                rect_x = pygame.Rect(int(new.x - self.radius), int(self.pos.y - self.radius),
                                     self.radius * 2, self.radius * 2)
                rect_y = pygame.Rect(int(self.pos.x - self.radius), int(new.y - self.radius),
                                     self.radius * 2, self.radius * 2)
                if not rect_x.colliderect(w):
                    new.y = self.pos.y
                elif not rect_y.colliderect(w):
                    new.x = self.pos.x
                else:
                    new = self.pos
                break
        self.pos = new

    def update_cooldowns(self, dt):
        for k in self.ability_cd:
            if self.ability_cd[k] > 0:
                self.ability_cd[k] = max(0.0, self.ability_cd[k] - dt)

    def cast_ability(self, key, target_pos, creeps, bosses, damage_numbers):
        if self.ability_cd.get(key, 0) > 0:
            return False
        lvl = self.ability_level.get(key, 1)

        if key == "Z":
            dirv = pygame.Vector2(target_pos) - self.pos
            if dirv.length() > 0:
                dash = dirv.normalize() * (160 + 20 * lvl)
                self.pos += dash
            for c in creeps:
                if (self.pos - c.pos).length() < 40 + 5 * lvl:
                    dmg = self.damage * (1 + 0.2 * lvl)
                    c.hp -= dmg
                    damage_numbers.append(DamageNumber((int(c.pos.x), int(c.pos.y)), dmg))
            for b in bosses:
                if b.alive and (self.pos - b.pos).length() < 60 + 5 * lvl:
                    dmg = self.damage * (1 + 0.2 * lvl)
                    b.hp -= dmg
                    damage_numbers.append(DamageNumber((int(b.pos.x), int(b.pos.y)), dmg))

        elif key == "X":
            for c in creeps:
                d = c.pos - self.pos
                if d.length() < 180:
                    c.pos += d.normalize() * (120 + 10 * lvl)
                    c.slow_timer = 1.5 + 0.2 * lvl
            for b in bosses:
                if b.alive and (b.pos - self.pos).length() < 220:
                    b.pos += (b.pos - self.pos).normalize() * (80 + 10 * lvl)
                    b.slow_timer = 1.5 + 0.2 * lvl

        elif key == "C":
            for c in creeps:
                d = c.pos - self.pos
                if d.length() < 220:
                    dmg = self.damage * (1.5 + 0.1 * lvl)
                    c.hp -= dmg
                    self.hp = clamp(self.hp + dmg * 0.3, 0, self.max_hp)
                    damage_numbers.append(DamageNumber((int(c.pos.x), int(c.pos.y)), dmg))
            for b in bosses:
                if b.alive and (b.pos - self.pos).length() < 260:
                    dmg = self.damage * (1.5 + 0.1 * lvl)
                    b.hp -= dmg
                    self.hp = clamp(self.hp + dmg * 0.2, 0, self.max_hp)
                    damage_numbers.append(DamageNumber((int(b.pos.x), int(b.pos.y)), dmg))

        self.ability_cd[key] = self.ability_max_cd[key]
        return True


@dataclass
class Creep:
    pos: pygame.Vector2
    hp: float = 80.0
    speed: float = 0.9
    radius: int = 10
    gold: int = 10
    xp: int = 18
    slow_timer: float = 0.0

    def update(self, dt, player):
        if self.slow_timer > 0:
            sp = self.speed * 0.4
            self.slow_timer -= dt
        else:
            sp = self.speed
        dirv = player.pos - self.pos
        if dirv.length_squared() > 0:
            self.pos += dirv.normalize() * sp * dt


@dataclass
class Boss:
    pos: pygame.Vector2
    hp: float
    max_hp: float
    radius: int
    speed: float
    kind: str
    alive: bool = True
    slow_timer: float = 0.0
    enraged: bool = False

    def update(self, dt, player):
        if not self.alive:
            return
        dirv = player.pos - self.pos
        if self.hp < self.max_hp * 0.4 and not self.enraged:
            self.enraged = True
            self.speed *= 1.3

        if dirv.length() < 420:
            sp = self.speed * (0.4 if self.slow_timer > 0 else 1.0)
            if self.kind == "charger":
                self.pos += dirv.normalize() * sp * 1.4 * dt
            elif self.kind == "lurker":
                self.pos += dirv.normalize() * sp * 0.6 * dt
                if random.random() < 0.002:
                    offset = pygame.Vector2(random.uniform(-120, 120),
                                            random.uniform(-120, 120))
                    self.pos = player.pos + offset
            elif self.kind == "roamer":
                if dirv.length() < 240:
                    self.pos += dirv.normalize() * sp * dt
                else:
                    self.pos += pygame.Vector2(
                        math.cos(pygame.time.get_ticks() / 1000.0 + id(self)),
                        math.sin(pygame.time.get_ticks() / 1000.0 + id(self))
                    ) * 0.3 * dt

        if self.slow_timer > 0:
            self.slow_timer -= dt
        if self.hp <= 0:
            self.alive = False


@dataclass
class DamageNumber:
    pos: tuple
    amount: float
    lifetime: float = 0.8
    vy: float = -0.4

    def update(self, dt):
        self.lifetime -= dt
        self.pos = (self.pos[0], self.pos[1] + self.vy * dt)


@dataclass
class ShopItem:
    name: str
    cost: int
    permanent: bool
    on_buy: callable = None
    on_use: callable = None
    description: str = ""

    def buy(self, player, persistent_gold, persistent_unlocked, persistent_inventory):
        if persistent_gold < self.cost:
            return False, persistent_gold
        if self.permanent and self.name in persistent_unlocked:
            return False, persistent_gold
        persistent_gold -= self.cost
        if self.permanent:
            persistent_unlocked.append(self.name)
            if self.on_buy:
                self.on_buy(player)
        else:
            persistent_inventory.append(self.name)
        return True, persistent_gold


# -------------------------------------------------------------------
# SHOP EFFECTS
# -------------------------------------------------------------------
def health_potion_use(player):
    player.hp = clamp(player.hp + 150, 0, player.max_hp)


def damage_talisman_buy(player):
    player.damage += 8


def speed_boots_buy(player):
    player.base_speed += 0.8


def battery_pack_use(player):
    player.battery = clamp(player.battery + 80, 0, 100)


def food_ration_use(player):
    player.food = clamp(player.food + 40, 0, 100)


SHOP_ITEMS = [
    ShopItem("Health Potion", 60, False, on_use=health_potion_use,
             description="Consumable: heal 150 HP"),
    ShopItem("Talisman of Might", 140, True, on_buy=damage_talisman_buy,
             description="Permanent: +8 damage"),
    ShopItem("Swift Boots", 160, True, on_buy=speed_boots_buy,
             description="Permanent: +0.8 base speed"),
    ShopItem("Battery Pack", 80, False, on_use=battery_pack_use,
             description="Consumable: restore 80 battery"),
    ShopItem("Food Ration", 40, False, on_use=food_ration_use,
             description="Consumable: restore 40 food"),
]

# -------------------------------------------------------------------
# WORLD GEOMETRY
# -------------------------------------------------------------------
walls = [
    pygame.Rect(20, 20, WIDTH - 40, 16),
    pygame.Rect(20, HEIGHT - 56, WIDTH - 40, 16),
    pygame.Rect(20, 20, 16, HEIGHT - 76),
    pygame.Rect(WIDTH - 36, 20, 16, HEIGHT - 76),
    pygame.Rect(260, 160, 680, 16),
    pygame.Rect(260, 560, 680, 16),
    pygame.Rect(260, 176, 16, 384),
    pygame.Rect(924, 176, 16, 384),
    pygame.Rect(520, 320, 160, 16),
]

TELEPORT_BOX = pygame.Rect(WIDTH // 2 - 140, HEIGHT // 2 - 100, 280, 200)
TELEPORT_KEY = pygame.K_t

# -------------------------------------------------------------------
# PERSISTENT DATA
# -------------------------------------------------------------------
persistent_gold = 300
persistent_unlocked = []
persistent_inventory = []
custom_settings = {"color": (255, 255, 255), "speed": 2.6}

best_score = 0
highest_level_unlocked = 1


def load_progress():
    global best_score, highest_level_unlocked, persistent_gold
    global persistent_unlocked, persistent_inventory

    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                lines = f.read().strip().splitlines()

                if len(lines) >= 1:
                    best_score = int(lines[0])
                if len(lines) >= 2:
                    highest_level_unlocked = max(1, int(lines[1]))
                if len(lines) >= 3:
                    persistent_gold = int(lines[2])
                if len(lines) >= 4:
                    persistent_unlocked = lines[3].split(",") if lines[3] else []
                if len(lines) >= 5:
                    persistent_inventory = lines[4].split(",") if lines[4] else []
        except Exception:
            pass


def save_progress():
    try:
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(best_score) + "\n")
            f.write(str(highest_level_unlocked) + "\n")
            f.write(str(persistent_gold) + "\n")
            f.write(",".join(persistent_unlocked) + "\n")
            f.write(",".join(persistent_inventory) + "\n")
    except Exception:
        pass


load_progress()

# -------------------------------------------------------------------
# GAME STATE INITIALIZATION
# -------------------------------------------------------------------
def make_default_player(custom=None):
    p = Player(pygame.Vector2(WIDTH // 2, HEIGHT // 2 + 160))
    if custom:
        p.color = custom.get("color", WHITE)
        p.base_speed = custom.get("speed", p.base_speed)
    return p


player = make_default_player(custom_settings)
player.gold = persistent_gold
player.inventory = persistent_inventory.copy()

creeps = []
bosses = []
pickups = []
damage_numbers = []

current_level = 1
level_enemy_cap = 10
spawn_timer = 0.0
spawn_interval = 3.0
score = 0
run_time = 0.0

difficulty = "Normal"  # "Easy", "Normal", "Hard"

# -------------------------------------------------------------------
# LEVEL / SPAWN SYSTEM
# -------------------------------------------------------------------
def difficulty_modifiers():
    if difficulty == "Easy":
        return 0.8, 0.8, 1.2
    elif difficulty == "Hard":
        return 1.3, 1.3, 0.8
    return 1.0, 1.0, 1.0


def spawn_initial_bosses_for_level(level):
    bosses.clear()
    hp_mod, _, _ = difficulty_modifiers()
    for _ in range(level):
        kind = random.choice(["charger", "lurker", "roamer"])
        x = random.randint(200, WIDTH - 200)
        y = random.randint(160, HEIGHT - 200)
        base_hp = 700 + level * 80
        hp = int(base_hp * hp_mod)
        r = 28
        sp = 0.5 + 0.02 * level
        bosses.append(Boss(pygame.Vector2(x, y), hp=hp, max_hp=hp,
                           radius=r, speed=sp, kind=kind))


def spawn_initial_pickups():
    pickups.clear()
    for _ in range(4):
        kind = random.choice(["health", "battery", "gold", "damage", "speed", "food"])
        val = {"health": 80, "battery": 60, "gold": 25,
               "damage": 4, "speed": 0.4, "food": 30}[kind]
        pickups.append({
            'pos': pygame.Vector2(random.randint(80, WIDTH - 80),
                                  random.randint(80, HEIGHT - 80)),
            'kind': kind,
            'value': val
        })


def drop_food_at(pos, value=30):
    pickups.append({
        'pos': pygame.Vector2(pos.x, pos.y),
        'kind': 'food',
        'value': value
    })


def spawn_creep():
    hp_mod, _, spawn_mod = difficulty_modifiers()
    active = len(creeps) + sum(1 for b in bosses if b.alive)
    if active >= level_enemy_cap:
        return
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        pos = pygame.Vector2(random.randint(300, WIDTH - 300), 100)
    elif side == "bottom":
        pos = pygame.Vector2(random.randint(300, WIDTH - 300), HEIGHT - 140)
    elif side == "left":
        pos = pygame.Vector2(120, random.randint(140, HEIGHT - 140))
    else:
        pos = pygame.Vector2(WIDTH - 120, random.randint(140, HEIGHT - 140))
    base_hp = 70 + random.randint(-10, 20)
    creeps.append(Creep(pos, hp=base_hp * hp_mod,
                        speed=0.8 + random.random() * 0.4))


def all_bosses_dead():
    return len(bosses) > 0 and all(not b.alive for b in bosses)


def setup_level(level):
    global level_enemy_cap, spawn_timer, current_level, run_time
    current_level = level
    creeps.clear()
    damage_numbers.clear()
    spawn_initial_bosses_for_level(level)
    spawn_initial_pickups()
    level_enemy_cap = 10 + (level - 1) * 3
    spawn_timer = 0.0
    run_time = 0.0


def reset_player_for_new_run():
    global player
    player = make_default_player(custom_settings)
    player.gold = persistent_gold
    for name in persistent_unlocked:
        if name == "Talisman of Might":
            player.damage += 8
        if name == "Swift Boots":
            player.base_speed += 0.8
    player.inventory = persistent_inventory.copy()


def start_level(level):
    global score
    reset_player_for_new_run()
    if level == 1:
        score = 0
    setup_level(level)


# -------------------------------------------------------------------
# COMBAT / PICKUPS / INVENTORY
# -------------------------------------------------------------------
def handle_combat(dt):
    global score
    _, dmg_mod, _ = difficulty_modifiers()
    player_hit = False

    for c in list(creeps):
        if c.hp <= 0:
            player.gold += c.gold
            player.xp += c.xp
            score += 5
            if random.random() < 0.30:
                drop_food_at(c.pos, value=30)
            creeps.remove(c)
            continue
        if (player.pos - c.pos).length() < player.radius + c.radius + 4:
            c.hp -= player.damage * 0.06 * dt
            player.hp -= 0.12 * dmg_mod * dt
            player_hit = True

    for b in bosses:
        if not b.alive:
            continue
        if (player.pos - b.pos).length() < player.radius + b.radius + 6:
            player.hp -= 0.6 * dmg_mod * dt
            b.hp -= player.damage * 0.04 * dt
            player_hit = True
        if b.hp <= 0 and b.alive:
            b.alive = False
            player.gold += 160
            player.xp += 220
            score += 50
            drop_food_at(b.pos, value=50)

    if player_hit:
        player.out_of_combat_timer = 0.0
    else:
        player.out_of_combat_timer += dt


def pickup_check():
    for p in list(pickups):
        if (player.pos - p['pos']).length() < player.radius + 10 + 4:
            if p['kind'] == "health":
                player.hp = clamp(player.hp + p['value'], 0, player.max_hp)
            elif p['kind'] == "battery":
                player.battery = clamp(player.battery + p['value'], 0, 100)
            elif p['kind'] == "gold":
                player.gold += int(p['value'])
            elif p['kind'] == "damage":
                player.damage += p['value']
            elif p['kind'] == "speed":
                player.base_speed += p['value']
            elif p['kind'] == "food":
                player.food = clamp(player.food + p['value'], 0, 100)
            pickups.remove(p)


def use_inventory_slot(slot):
    if 0 <= slot < len(player.inventory):
        name = player.inventory.pop(slot)
        if name == "Health Potion":
            health_potion_use(player)
        elif name == "Battery Pack":
            battery_pack_use(player)
        elif name == "Food Ration":
            food_ration_use(player)


# -------------------------------------------------------------------
# HUD / DRAWING
# -------------------------------------------------------------------
def draw_minimap():
    w, h = 240, 160
    mini = pygame.Surface((w, h))
    mini.fill((12, 12, 12))
    world_rect = pygame.Rect(20, 20, WIDTH - 40, HEIGHT - 76)
    sx = w / world_rect.width
    sy = h / world_rect.height
    px = int((player.pos.x - world_rect.x) * sx)
    py = int((player.pos.y - world_rect.y) * sy)
    pygame.draw.circle(mini, GREEN, (px, py), 4)
    for c in creeps:
        cx = int((c.pos.x - world_rect.x) * sx)
        cy = int((c.pos.y - world_rect.y) * sy)
        pygame.draw.circle(mini, RED, (cx, cy), 2)
    for b in bosses:
        if b.alive:
            bx = int((b.pos.x - world_rect.x) * sx)
            by = int((b.pos.y - world_rect.y) * sy)
            pygame.draw.circle(mini, ORANGE, (bx, by), 4)
    screen.blit(mini, (WIDTH - w - 12, HEIGHT - h - 12))
    pygame.draw.rect(screen, GRAY, (WIDTH - w - 12, HEIGHT - h - 12, w, h), 2)


def draw_hud():
    draw_text(screen, "Controls: WASD move  Shift sprint  Mouse aim  E pickup  F eat ration  1-4 use items  Q dashboard",
              (12, 8), LIGHT_GRAY)
    draw_text(screen, "Z/X/C abilities  T teleport  ESC pause", (12, 26), LIGHT_GRAY)

    if any(b.alive for b in bosses):
        draw_text(screen, "⚠ Boss Active!", (WIDTH // 2 - 60, 8), ORANGE, MID)

    bar_x = 32
    bar_w = 360
    icon_x = bar_x - 36
    base_y = HEIGHT - 160

    draw_heart(screen, icon_x + 12, base_y + 8, size=18)
    pygame.draw.rect(screen, (40, 40, 40), (bar_x, base_y, bar_w, 18))
    hpw = int(bar_w * (player.hp / player.max_hp))
    pygame.draw.rect(screen, RED, (bar_x, base_y, hpw, 18))
    draw_text(screen, f"HP: {int(player.hp)}/{int(player.max_hp)}", (bar_x + 4, base_y - 2))

    bat_y = base_y + 24
    draw_battery(screen, icon_x + 2, bat_y + 1, w=36, h=12, pct=player.battery / 100)
    pygame.draw.rect(screen, (40, 40, 40), (bar_x, bat_y, bar_w, 14))
    bw = int(bar_w * (player.battery / 100))
    pygame.draw.rect(screen, YELLOW, (bar_x, bat_y, bw, 14))
    draw_text(screen, f"Battery: {int(player.battery)}%", (bar_x + 4, bat_y - 2))

    stam_y = bat_y + 20
    draw_sprint_icon(screen, icon_x + 12, stam_y + 6)
    pygame.draw.rect(screen, (40, 40, 40), (bar_x, stam_y, bar_w, 12))
    sw = int(bar_w * (player.stamina / 100))
    pygame.draw.rect(screen, BLUE, (bar_x, stam_y, sw, 12))
    draw_text(screen, f"Stamina: {int(player.stamina)}", (bar_x + 4, stam_y - 2))

    food_y = stam_y + 18
    draw_food_icon(screen, icon_x + 12, food_y + 6)
    pygame.draw.rect(screen, (40, 40, 40), (bar_x, food_y, bar_w, 12))
    fw = int(bar_w * (player.food / 100))
    pygame.draw.rect(screen, (200, 160, 60), (bar_x, food_y, fw, 12))
    draw_text(screen, f"Food: {int(player.food)}%", (bar_x + 4, food_y - 2))

    pygame.draw.rect(screen, (40, 40, 40), (420, HEIGHT - 180, 380, 10))
    xp_ratio = (player.xp % 100) / 100
    pygame.draw.rect(screen, BLUE, (420, HEIGHT - 180, int(380 * xp_ratio), 10))
    draw_text(screen, f"XP Progress: {int(xp_ratio * 100)}%", (420, HEIGHT - 192), LIGHT_GRAY)

    draw_text(screen, f"Gold: {player.gold}", (420, HEIGHT - 160), YELLOW)
    draw_text(screen, f"XP: {player.xp}", (420, HEIGHT - 140), BLUE)
    draw_text(screen, f"Hero Level: {player.level}", (420, HEIGHT - 120), ORANGE)
    draw_text(screen, f"Game Level: {current_level}", (420, HEIGHT - 100), WHITE)
    draw_text(screen, f"Score: {score}  Best: {best_score}", (420, HEIGHT - 80), LIGHT_GRAY)
    draw_text(screen, f"Difficulty: {difficulty}", (420, HEIGHT - 60), LIGHT_GRAY)
    draw_text(screen, f"Run Time: {run_time:.1f}s", (420, HEIGHT - 40), LIGHT_GRAY)

    if player.battery < 20 and int(pygame.time.get_ticks() / 300) % 2 == 0:
        draw_text(screen, "LOW BATTERY!", (WIDTH // 2 - 60, HEIGHT - 200), YELLOW, MID)

    draw_text(screen, f"Teleport key: T (toggle inside/outside box)", (720, HEIGHT - 160), LIGHT_GRAY)
    draw_text(screen, "Inventory (1-4):", (720, HEIGHT - 140))

    for i in range(4):
        x = 720 + i * 110
        rect = pygame.Rect(x, HEIGHT - 120, 104, 28)
        pygame.draw.rect(screen, (30, 30, 40), rect)
        pygame.draw.rect(screen, GRAY, rect, 2)
        if i < len(player.inventory):
            draw_text(screen, f"{i + 1}: {player.inventory[i]}", (x + 6, HEIGHT - 116), WHITE)
        else:
            draw_text(screen, f"{i + 1}: ---", (x + 6, HEIGHT - 116), LIGHT_GRAY)

    ax = 12
    for k in ["Z", "X", "C"]:
        rect = pygame.Rect(ax, HEIGHT - 220, 64, 32)
        pygame.draw.rect(screen, (30, 30, 40), rect)
        pygame.draw.rect(screen, GRAY, rect, 2)
        draw_text(screen, f"{k}", (ax + 6, HEIGHT - 218))
        cd = player.ability_cd[k]
        if cd > 0:
            draw_text(screen, f"CD: {cd:.1f}s", (ax + 6, HEIGHT - 202), RED)
        else:
            draw_text(screen, "Ready", (ax + 6, HEIGHT - 202), GREEN)
        ax += 80

    fps = int(clock.get_fps())
    draw_text(screen, f"{fps} FPS", (WIDTH - 90, 10), LIGHT_GRAY)


def draw_world():
    screen.fill(DARK)

    for w in walls:
        pygame.draw.rect(screen, GRAY, w)

    pygame.draw.rect(screen, (40, 40, 60), TELEPORT_BOX)
    draw_text(screen, "Teleport Box", (TELEPORT_BOX.x + 8, TELEPORT_BOX.y + 8), LIGHT_GRAY)

    for p in pickups:
        kind = p['kind']
        col = GREEN if kind == "health" else (YELLOW if kind == "battery"
                                              else (ORANGE if kind == "gold" else BLUE))
        if kind == "food":
            col = (200, 160, 60)
        px, py = int(p['pos'].x), int(p['pos'].y)
        pygame.draw.circle(screen, col, (px, py), 10)
        draw_text(screen, kind, (px - 12, py + 12), WHITE)

    for c in creeps:
        cx, cy = int(c.pos.x), int(c.pos.y)
        pygame.draw.circle(screen, RED, (cx, cy), c.radius)
        hpw = int(18 * max(0, c.hp) / 100)
        pygame.draw.rect(screen, (30, 30, 30), (cx - 9, cy - 18, 18, 4))
        pygame.draw.rect(screen, GREEN, (cx - 9, cy - 18, hpw, 4))

    for b in bosses:
        if b.alive:
            bx, by = int(b.pos.x), int(b.pos.y)
            color = ORANGE if not b.enraged else (255, 80, 0)
            pygame.draw.circle(screen, color, (bx, by), b.radius)
            hpw = int(80 * max(0, b.hp) / b.max_hp)
            pygame.draw.rect(screen, (30, 30, 30), (bx - 40, by - b.radius - 14, 80, 8))
            pygame.draw.rect(screen, RED, (bx - 40, by - b.radius - 14, hpw, 8))

    pygame.draw.circle(screen, player.color, (int(player.pos.x), int(player.pos.y)), player.radius)

    mouse_pos = pygame.mouse.get_pos()
    radius = int(360 * (player.battery / 100)) if player.battery > 0 else 100
    darkness = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, 220))
    pygame.draw.circle(darkness, (0, 0, 0, 0), (int(mouse_pos[0]), int(mouse_pos[1])), radius)
    screen.blit(darkness, (0, 0))

    for dn in damage_numbers:
        alpha = int(255 * (dn.lifetime / 0.8))
        txt = FONT.render(str(int(dn.amount)), True, (255, 255, 255))
        txt.set_alpha(alpha)
        screen.blit(txt, (int(dn.pos[0]), int(dn.pos[1])))

    draw_hud()
    draw_minimap()


def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        test = cur + (" " if cur else "") + w
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_text_block(surf, text, pos, max_width, color=WHITE, font=FONT, line_spacing=4):
    lines = wrap_text(text, font, max_width)
    x, y = pos
    for i, line in enumerate(lines):
        surf.blit(font.render(line, True, color), (x, y + i * (font.get_height() + line_spacing)))
    return y + len(lines) * (font.get_height() + line_spacing)


def draw_heart(surf, x, y, size=16, color=RED):
    r = size // 3
    pygame.draw.circle(surf, color, (int(x - r), int(y)), r)
    pygame.draw.circle(surf, color, (int(x + r), int(y)), r)
    points = [(x - size // 2, y), (x + size // 2, y), (x, y + size // 2)]
    pygame.draw.polygon(surf, color, points)


def draw_battery(surf, x, y, w=36, h=14, pct=1.0, color=YELLOW, bg=(40, 40, 40)):
    pygame.draw.rect(surf, bg, (int(x), int(y), int(w), int(h)))
    inner_w = max(2, int((w - 4) * clamp(pct, 0.0, 1.0)))
    pygame.draw.rect(surf, color, (int(x + 2), int(y + 2), inner_w, int(h - 4)))
    pygame.draw.rect(surf, bg, (int(x + w), int(y + h // 4), 4, int(h // 2)))


def draw_sprint_icon(surf, x, y, size=14, color=BLUE):
    points = [(x - size // 2, y + size // 2), (x + size // 2, y), (x - size // 2, y - size // 2)]
    pygame.draw.polygon(surf, color, points)


def draw_food_icon(surf, x, y, size=14, color=(200, 160, 60)):
    pygame.draw.circle(surf, color, (int(x - size // 4), int(y)), size // 3)
    pygame.draw.rect(surf, color, (int(x - size // 4), int(y - size // 6), int(size), int(size // 3)))


# -------------------------------------------------------------------
# DASHBOARD / SHOP / CUSTOMIZE / RESULTS / PAUSE
# -------------------------------------------------------------------
btn_start = Button(pygame.Rect(80, 140, 260, 64), "Quick Start (Level 1)")
btn_shop = Button(pygame.Rect(80, 220, 260, 64), "Shop")
btn_customize = Button(pygame.Rect(80, 300, 260, 64), "Customize")
btn_changelog = Button(pygame.Rect(80, 380, 260, 64), "Changelog")
btn_quit = Button(pygame.Rect(80, 460, 260, 64), "Quit")

btn_easy = Button(pygame.Rect(380, 140, 160, 40), "Easy")
btn_normal = Button(pygame.Rect(380, 190, 160, 40), "Normal")
btn_hard = Button(pygame.Rect(380, 240, 160, 40), "Hard")

shop_buttons = [Button(pygame.Rect(380, 120 + i * 84, 520, 64),
                       f"{SHOP_ITEMS[i].name} — {SHOP_ITEMS[i].cost}g")
                for i in range(len(SHOP_ITEMS))]

color_presets = [(255, 255, 255), (200, 200, 255), (255, 200, 200),
                 (200, 255, 200), (255, 240, 120)]
preset_buttons = [Button(pygame.Rect(380 + i * 84, 120, 72, 72), "") for i in range(len(color_presets))]
speed_minus = Button(pygame.Rect(380, 220, 56, 40), "-")
speed_plus = Button(pygame.Rect(448, 220, 56, 40), "+")
apply_custom = Button(pygame.Rect(380, 300, 160, 48), "Apply")

RESULT_CONTINUE = Button(pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 + 60, 160, 50), "Continue")
RESULT_REPLAY = Button(pygame.Rect(WIDTH // 2 - 80, HEIGHT // 2 + 60, 160, 50), "Replay Level")
RESULT_DASH = Button(pygame.Rect(WIDTH // 2 + 100, HEIGHT // 2 + 60, 160, 50), "Dashboard")

LEVEL_BUTTON_AREA = pygame.Rect(720, 140, 360, 420)
LEVEL_BUTTON_HEIGHT = 40
level_scroll_offset = 0
btn_scroll_up = Button(pygame.Rect(LEVEL_BUTTON_AREA.x - 48, LEVEL_BUTTON_AREA.y + 8, 40, 40), "▲")
btn_scroll_down = Button(pygame.Rect(LEVEL_BUTTON_AREA.x - 48, LEVEL_BUTTON_AREA.y + LEVEL_BUTTON_AREA.height - 48, 40, 40), "▼")


def draw_dashboard():
    screen.fill(DARK)
    left_x = 80
    left_w = 320
    left_y = 40
    left_gap = 12

    right_x = 360
    right_w = WIDTH - right_x - 80
    right_y = 40

    draw_text(screen, "Welcome to Horror Arena!", (left_x, left_y), WHITE, BIG)
    draw_text(screen, f"{GAME_VERSION} — Made with Microsoft Copilot", (left_x, left_y + 40), LIGHT_GRAY)

    btn_y = left_y + 96
    for b in (btn_start, btn_shop, btn_customize, btn_changelog, btn_quit):
        b.rect.topleft = (left_x, btn_y)
        b.draw(screen)
        btn_y += b.rect.height + left_gap

    instr_x = right_x
    instr_y = right_y + 40
    draw_text(screen, "Instructions:", (instr_x, instr_y), WHITE, MID)
    instr_lines = [
        "Survive waves of enemies and defeat bosses.",
        "Move with WASD, sprint with Shift.",
        "Aim with mouse, use abilities with Z/X/C.",
        "Pick up items with E, use inventory with 1–4.",
        "Eat food rations with F to restore hunger.",
        "Teleport with T when inside the teleport box."
    ]
    cur_y = instr_y + MID.get_height() + 8
    for line in instr_lines:
        cur_y = draw_text_block(screen, "• " + line, (instr_x + 8, cur_y), right_w - 16, LIGHT_GRAY, FONT, line_spacing=2) + 6

    stats_x = right_x
    stats_y = cur_y + 12
    draw_text(screen, f"Gold: {persistent_gold}", (stats_x, stats_y), YELLOW)
    draw_text(screen, f"Best Score: {best_score}", (stats_x, stats_y + 26), ORANGE)
    draw_text(screen, f"Highest Level Unlocked: {highest_level_unlocked}", (stats_x, stats_y + 52), LIGHT_GRAY)
    draw_text(screen, f"Saved Gold: {persistent_gold}", (stats_x, stats_y + 78), YELLOW)

    diff_y = stats_y + 110
    draw_text(screen, "Difficulty:", (stats_x, diff_y), WHITE)
    btn_easy.rect.topleft = (stats_x + 100, diff_y - 6)
    btn_normal.rect.topleft = (stats_x + 100, diff_y + 38)
    btn_hard.rect.topleft = (stats_x + 100, diff_y + 82)
    btn_easy.draw(screen); btn_normal.draw(screen); btn_hard.draw(screen)
    draw_text(screen, f"Current: {difficulty}", (stats_x, diff_y + 130), LIGHT_GRAY)

    pygame.draw.rect(screen, (25, 25, 30), LEVEL_BUTTON_AREA)
    pygame.draw.rect(screen, GRAY, LEVEL_BUTTON_AREA, 2)
    draw_text(screen, "Level Select", (LEVEL_BUTTON_AREA.x + 8, LEVEL_BUTTON_AREA.y - 24), WHITE)

    visible_slots = LEVEL_BUTTON_AREA.height // LEVEL_BUTTON_HEIGHT
    start_level_val = max(1, level_scroll_offset + 1)
    for i in range(visible_slots):
        lvl = start_level_val + i
        y = LEVEL_BUTTON_AREA.y + i * LEVEL_BUTTON_HEIGHT
        rect = pygame.Rect(LEVEL_BUTTON_AREA.x + 4, y + 2, LEVEL_BUTTON_AREA.width - 8, LEVEL_BUTTON_HEIGHT - 4)
        unlocked = lvl <= highest_level_unlocked
        label = f"Level {lvl}" + (" (locked)" if not unlocked else "")
        btn = Button(rect, label, enabled=unlocked)
        btn.draw(screen)

    btn_scroll_up.draw(screen)
    btn_scroll_down.draw(screen)

    footer_text = "Buy Food Rations in Shop. Press F in-game to eat a ration from inventory. Q in-game returns here. Scroll level list with mouse wheel or arrows."
    draw_text_block(screen, footer_text, (left_x, HEIGHT - 80), WIDTH - 160, LIGHT_GRAY, FONT, line_spacing=2)


def draw_shop():
    screen.fill(DARK)
    draw_text(screen, "Shop — Buy powerups (permanent or consumable)", (80, 80), WHITE, BIG)
    draw_text(screen, f"Gold: {persistent_gold}", (80, 120), YELLOW)
    for i, b in enumerate(shop_buttons):
        b.draw(screen)
        it = SHOP_ITEMS[i]
        draw_text(screen, it.description, (b.rect.x + 8, b.rect.y + 36), LIGHT_GRAY)
    draw_text(screen, "Click an item to buy. Permanent items apply immediately. Consumables go to inventory.", (80, 520), LIGHT_GRAY)
    draw_text(screen, "Back: press ESC", (80, 540), LIGHT_GRAY)


def draw_customize(current_speed):
    screen.fill(DARK)
    draw_text(screen, "Customize Hero", (80, 80), WHITE, BIG)
    draw_text(screen, f"Current speed: {current_speed:.2f}", (380, 200), WHITE)
    draw_text(screen, "Choose color:", (380, 100), WHITE)
    for i, b in enumerate(preset_buttons):
        pygame.draw.rect(screen, color_presets[i], b.rect)
        pygame.draw.rect(screen, GRAY, b.rect, 2)
    speed_minus.draw(screen)
    speed_plus.draw(screen)
    apply_custom.draw(screen)
    draw_text(screen, "Back: press ESC", (80, 520), LIGHT_GRAY)


def draw_results(success, level, final_score, final_time):
    screen.fill(DARK)
    title = "LEVEL CLEARED" if success else "YOU DIED"
    color = GREEN if success else RED
    draw_centered_text(screen, title, pygame.Rect(0, HEIGHT // 2 - 140, WIDTH, 60), color, BIG)
    draw_centered_text(screen, f"Level: {level}   Score: {final_score}   Time: {final_time:.1f}s",
                       pygame.Rect(0, HEIGHT // 2 - 80, WIDTH, 40), WHITE, MID)
    draw_centered_text(screen, f"Best Score: {best_score}", pygame.Rect(0, HEIGHT // 2 - 40, WIDTH, 40), ORANGE, MID)

    RESULT_CONTINUE.draw(screen)
    RESULT_REPLAY.draw(screen)
    RESULT_DASH.draw(screen)


def draw_pause():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))
    draw_centered_text(screen, "PAUSED", pygame.Rect(0, HEIGHT // 2 - 60, WIDTH, 40), WHITE, BIG)
    draw_centered_text(screen, "ESC resume   Q dashboard", pygame.Rect(0, HEIGHT // 2, WIDTH, 40), LIGHT_GRAY, MID)


def draw_changelog():
    screen.fill(DARK)
    draw_text(screen, "Changelog", (80, 80), WHITE, BIG)

    changelog_entries = [
        "v1.1.4 — Fixed ability keys, save handling, and HUD cleanup",
        "v1.1.3 — Fixed ability key bugs; BUG FIX",
        "v1.1.2.1 — Added start-screen instructions, gold & purchase saving",
        "v1.1.2 — HUD enhancements, warnings, XP bar, bug fixes",
        "v1.1.1 — Added changelog screen, welcome message, version watermark",
        "v1.1 — Arrow scrolling, Copilot credit, dashboard improvements",
        "v1.0 — Initial release of Horror Arena"
    ]

    y = 160
    for entry in changelog_entries:
        draw_text(screen, entry, (80, y), LIGHT_GRAY)
        y += 30

    draw_text(screen, "Press ESC to return", (80, HEIGHT - 80), LIGHT_GRAY)


# -------------------------------------------------------------------
# MAIN LOOP
# -------------------------------------------------------------------
STATE_DASHBOARD = "dashboard"
STATE_SHOP = "shop"
STATE_CUSTOMIZE = "customize"
STATE_PLAYING = "playing"
STATE_RESULTS = "results"
STATE_PAUSE = "pause"
STATE_CHANGELOG = "changelog"

state = STATE_DASHBOARD
custom_speed = custom_settings["speed"]
running = True

results_level = 1
results_success = False
results_score = 0
results_time = 0.0

spawn_timer = 0.0

while running:
    dt = clock.tick(60) / (1000.0 / 60.0)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if state == STATE_DASHBOARD:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_start.clicked(event):
                    start_level(1)
                    state = STATE_PLAYING
                if btn_shop.clicked(event):
                    state = STATE_SHOP
                if btn_customize.clicked(event):
                    state = STATE_CUSTOMIZE
                if btn_changelog.clicked(event):
                    state = STATE_CHANGELOG
                if btn_quit.clicked(event):
                    running = False

                if btn_easy.clicked(event):
                    difficulty = "Easy"
                if btn_normal.clicked(event):
                    difficulty = "Normal"
                if btn_hard.clicked(event):
                    difficulty = "Hard"

                if LEVEL_BUTTON_AREA.collidepoint(event.pos):
                    rel_y = event.pos[1] - LEVEL_BUTTON_AREA.y
                    idx = rel_y // LEVEL_BUTTON_HEIGHT
                    start_level_num = max(1, level_scroll_offset + 1)
                    lvl = start_level_num + idx
                    if lvl <= highest_level_unlocked:
                        start_level(lvl)
                        state = STATE_PLAYING

                if btn_scroll_up.clicked(event):
                    level_scroll_offset = max(0, level_scroll_offset - 1)
                if btn_scroll_down.clicked(event):
                    max_scroll = max(0, highest_level_unlocked - (LEVEL_BUTTON_AREA.height // LEVEL_BUTTON_HEIGHT))
                    level_scroll_offset = min(level_scroll_offset + 1, max_scroll)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    level_scroll_offset = max(0, level_scroll_offset - 1)
                elif event.key == pygame.K_DOWN:
                    max_scroll = max(0, highest_level_unlocked - (LEVEL_BUTTON_AREA.height // LEVEL_BUTTON_HEIGHT))
                    level_scroll_offset = min(level_scroll_offset + 1, max_scroll)

            if event.type == pygame.MOUSEWHEEL:
                visible_slots = LEVEL_BUTTON_AREA.height // LEVEL_BUTTON_HEIGHT
                max_scroll = max(0, highest_level_unlocked - visible_slots)
                level_scroll_offset -= event.y
                level_scroll_offset = clamp(level_scroll_offset, 0, max_scroll)

        elif state == STATE_SHOP:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_DASHBOARD
            for i, b in enumerate(shop_buttons):
                if b.clicked(event):
                    item = SHOP_ITEMS[i]
                    dummy_player = make_default_player(custom_settings)
                    ok, persistent_gold = item.buy(dummy_player, persistent_gold, persistent_unlocked, persistent_inventory)

        elif state == STATE_CUSTOMIZE:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_DASHBOARD
            for i, b in enumerate(preset_buttons):
                if b.clicked(event):
                    custom_settings["color"] = color_presets[i]
            if speed_minus.clicked(event):
                custom_speed = clamp(custom_speed - 0.1, 1.4, 4.0)
            if speed_plus.clicked(event):
                custom_speed = clamp(custom_speed + 0.1, 1.4, 4.0)
            if apply_custom.clicked(event):
                custom_settings["speed"] = custom_speed
                state = STATE_DASHBOARD

        elif state == STATE_CHANGELOG:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                state = STATE_DASHBOARD

        elif state == STATE_PLAYING:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    persistent_gold = player.gold
                    persistent_inventory = player.inventory.copy()
                    if score > best_score:
                        best_score = score
                    save_progress()
                    state = STATE_DASHBOARD

                elif event.key == pygame.K_ESCAPE:
                    state = STATE_PAUSE
                elif event.key == pygame.K_1:
                    use_inventory_slot(0)
                elif event.key == pygame.K_2:
                    use_inventory_slot(1)
                elif event.key == pygame.K_3:
                    use_inventory_slot(2)
                elif event.key == pygame.K_4:
                    use_inventory_slot(3)
                elif event.key == TELEPORT_KEY:
                    if TELEPORT_BOX.collidepoint(player.pos.x, player.pos.y):
                        player.pos = pygame.Vector2(120, 120)
                    else:
                        player.pos = pygame.Vector2(TELEPORT_BOX.centerx, TELEPORT_BOX.centery)
                elif event.key == pygame.K_z:
                    player.cast_ability("Z", pygame.mouse.get_pos(), creeps, bosses, damage_numbers)
                elif event.key == pygame.K_x:
                    player.cast_ability("X", pygame.mouse.get_pos(), creeps, bosses, damage_numbers)
                elif event.key == pygame.K_c:
                    player.cast_ability("C", pygame.mouse.get_pos(), creeps, bosses, damage_numbers)
                elif event.key == pygame.K_e:
                    pickup_check()
                elif event.key == pygame.K_f:
                    if "Food Ration" in player.inventory:
                        idx = player.inventory.index("Food Ration")
                        use_inventory_slot(idx)

        elif state == STATE_RESULTS:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if RESULT_CONTINUE.clicked(event):
                    if results_success:
                        persistent_gold = player.gold
                        persistent_inventory = player.inventory.copy()
                        next_level = results_level + 1
                        if next_level > highest_level_unlocked:
                            highest_level_unlocked = next_level
                        save_progress()
                        start_level(next_level)
                        state = STATE_PLAYING
                    else:
                        persistent_gold = player.gold
                        persistent_inventory = player.inventory.copy()
                        save_progress()
                        state = STATE_DASHBOARD
                if RESULT_REPLAY.clicked(event):
                    persistent_gold = player.gold
                    persistent_inventory = player.inventory.copy()
                    save_progress()
                    start_level(results_level)
                    state = STATE_PLAYING
                if RESULT_DASH.clicked(event):
                    persistent_gold = player.gold
                    persistent_inventory = player.inventory.copy()
                    save_progress()
                    state = STATE_DASHBOARD

        elif state == STATE_PAUSE:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    state = STATE_PLAYING
                elif event.key == pygame.K_q:
                    persistent_gold = player.gold
                    persistent_inventory = player.inventory.copy()
                    if score > best_score:
                        best_score = score
                    save_progress()
                    state = STATE_DASHBOARD

    if state == STATE_PLAYING:
        run_time += dt

        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        speed = player.base_speed

        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            if player.stamina > 0:
                speed *= 1.6
                player.stamina = max(0, player.stamina - 0.4 * dt)
        else:
            player.stamina = clamp(player.stamina + 0.25 * dt, 0, 100)

        if keys[pygame.K_w]: move.y -= speed
        if keys[pygame.K_s]: move.y += speed
        if keys[pygame.K_a]: move.x -= speed
        if keys[pygame.K_d]: move.x += speed
        if move.length_squared() > 0:
            move = move.normalize() * speed
        player.move(move, walls)

        if player.battery > 0:
            player.battery = max(0, player.battery - 0.01 * dt)

        player.food = max(0, player.food - player.food_decay_rate * dt)

        if player.out_of_combat_timer > 120:
            if player.food > player.food_regen_threshold_fast:
                player.hp = clamp(player.hp + 0.4 * dt, 0, player.max_hp)
            elif player.food > player.food_regen_threshold_slow:
                player.hp = clamp(player.hp + 0.15 * dt, 0, player.max_hp)

        player.update_cooldowns(dt)

        for c in creeps:
            c.update(dt, player)
        for b in bosses:
            b.update(dt, player)

        handle_combat(dt)

        _, _, spawn_mod = difficulty_modifiers()
        spawn_timer += dt
        if spawn_timer >= spawn_interval * spawn_mod:
            spawn_timer = 0.0
            spawn_creep()

        for dn in list(damage_numbers):
            dn.update(dt)
            if dn.lifetime <= 0:
                damage_numbers.remove(dn)

        if player.hp <= 0:
            persistent_gold = player.gold
            persistent_inventory = player.inventory.copy()
            results_level = current_level
            results_success = False
            results_score = score
            results_time = run_time
            if score > best_score:
                best_score = score
            save_progress()
            state = STATE_RESULTS

        if all_bosses_dead():
            persistent_gold = player.gold
            persistent_inventory = player.inventory.copy()
            results_level = current_level
            results_success = True
            results_score = score
            results_time = run_time
            if current_level + 1 > highest_level_unlocked:
                highest_level_unlocked = current_level + 1
            if score > best_score:
                best_score = score
            save_progress()
            state = STATE_RESULTS

    if state == STATE_DASHBOARD:
        draw_dashboard()
    elif state == STATE_SHOP:
        draw_shop()
    elif state == STATE_CUSTOMIZE:
        draw_customize(custom_speed)
    elif state == STATE_PLAYING:
        draw_world()
    elif state == STATE_RESULTS:
        draw_results(results_success, results_level, results_score, results_time)
    elif state == STATE_PAUSE:
        draw_world()
        draw_pause()
    elif state == STATE_CHANGELOG:
        draw_changelog()

    draw_text(screen, GAME_VERSION, (WIDTH - 60, HEIGHT - 30), LIGHT_GRAY)
    pygame.display.flip()

pygame.quit()
sys.exit()

