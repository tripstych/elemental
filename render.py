import pygame
import imgui
from seed.dungeon_generator import DungeonGenerator

from constants import *

class Render:
    """Rendering class for Elemental Game"""
    
    def __init__(self, game):
        self.game = game
        self.COLORS = game.COLORS
        
        # Transmutation state
        self._transmute_step = 0  # 0=item, 1=pattern (auto-calc amounts)
        self._transmute_item = None
        self._transmute_coagulant_amount = 0
        self._transmute_pattern = None

    def render(self):
        """Main render method"""
        self.game.game_surface.fill(self.COLORS['black'])
        
        # Render game world
        self.render_dungeon()
        self.render_entities()
        self.render_items()
        
        # Render UI
        self.render_sidebar()
        self.render_messages()
        self.render_controls()
        
        # Render overlays
        if self.game.show_spell_book:
            self.render_spell_book()

    def render_dungeon(self):
        """Render dungeon tiles"""
        tile_colors = {
            DungeonGenerator.FLOOR: self.game.COLORS['floor'],
            DungeonGenerator.WALL: self.game.COLORS['wall'],
            DungeonGenerator.DOOR: self.game.COLORS['door'],
            DungeonGenerator.CORRIDOR: self.game.COLORS['corridor'],
            DungeonGenerator.ROOM_FLOOR: self.game.COLORS['floor'],
            DungeonGenerator.ENTRANCE: self.game.COLORS['entrance'],
            DungeonGenerator.EXIT: self.game.COLORS['exit'],
        }
        
        for screen_y in range(self.game.viewport_height):
            for screen_x in range(self.game.viewport_width):
                world_x = self.game.camera_x + screen_x
                world_y = self.game.camera_y + screen_y
                
                if 0 <= world_x < self.game.world.width and 0 <= world_y < self.game.world.height:
                    tile = self.game.world.dungeon.grid[world_y, world_x]
                    color = tile_colors.get(tile, self.game.COLORS['black'])
                    
                    rect = pygame.Rect(
                        10 + screen_x * TILE_SIZE,
                        10 + screen_y * TILE_SIZE,
                        TILE_SIZE - 1,
                        TILE_SIZE - 1
                    )
                    pygame.draw.rect(self.game.game_surface, color, rect)
                    
                    # Draw wall borders
                    if tile == DungeonGenerator.WALL:
                        pygame.draw.rect(self.game.game_surface, self.COLORS['dark_gray'], rect, 1)
                    
                    # Draw path if in pathfinding mode
                    if self.game.path_mode and (world_x, world_y) in self.game.path:
                        pygame.draw.rect(self.game.game_surface, self.COLORS['yellow'], rect, 2)
                    
                    # Draw target position
                    if self.game.target_pos and (world_x, world_y) == self.game.target_pos:
                        pygame.draw.rect(self.game.game_surface, self.COLORS['green'], rect, 3)
    
    def render_entities(self):
        """Render player and monsters"""
        player = self.game.world.player
        
        # Player
        if self.game.camera_x <= player.x < self.game.camera_x + self.game.viewport_width and \
           self.game.camera_y <= player.y < self.game.camera_y + self.game.viewport_height:
            screen_x = (player.x - self.game.camera_x) * TILE_SIZE + 10
            screen_y = (player.y - self.game.camera_y) * TILE_SIZE + 10
            
            # Player circle
            center = (screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2)
            pygame.draw.circle(self.game.game_surface, self.COLORS['player'], center, TILE_SIZE // 2 - 2)
            pygame.draw.circle(self.game.game_surface, self.COLORS['white'], center, TILE_SIZE // 2 - 2, 2)
            
            # @ symbol
            text = self.game.font.render("@", True, self.COLORS['white'])
            text_rect = text.get_rect(center=center)
            self.game.game_surface.blit(text, text_rect)
        
        # Monsters
        for monster in self.game.world.monsters:
            if not monster.stats.is_alive():
                continue
            
            if self.game.camera_x <= monster.x < self.game.camera_x + self.game.viewport_width and \
               self.game.camera_y <= monster.y < self.game.camera_y + self.game.viewport_height:
                screen_x = (monster.x - self.game.camera_x) * TILE_SIZE + 10
                screen_y = (monster.y - self.game.camera_y) * TILE_SIZE + 10
                
                # Monster circle
                center = (screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2)
                pygame.draw.circle(self.game.game_surface, self.COLORS['monster'], center, TILE_SIZE // 2 - 2)
                pygame.draw.circle(self.game.game_surface, self.COLORS['dark_red'], center, TILE_SIZE // 2 - 2, 2)
                
                # First letter
                text = self.game.font.render(monster.name[0].upper(), True, self.COLORS['white'])
                text_rect = text.get_rect(center=center)
                self.game.game_surface.blit(text, text_rect)
                
                # Health bar above monster
                hp_pct = monster.stats.current_health / monster.stats.max_health
                bar_width = TILE_SIZE - 4
                bar_rect = pygame.Rect(screen_x + 2, screen_y - 4, int(bar_width * hp_pct), 3)
                bg_rect = pygame.Rect(screen_x + 2, screen_y - 4, bar_width, 3)
                pygame.draw.rect(self.game.game_surface, self.COLORS['dark_red'], bg_rect)
                pygame.draw.rect(self.game.game_surface, self.COLORS['red'], bar_rect)
    
    def render_items(self):
        """Render items on ground"""
        for pos, items in self.game.world.items_on_ground.items():
            if not items:
                continue
            
            x, y = pos
            if self.game.camera_x <= x < self.game.camera_x + self.game.viewport_width and \
               self.game.camera_y <= y < self.game.camera_y + self.game.viewport_height:
                screen_x = (x - self.game.camera_x) * TILE_SIZE + 10
                screen_y = (y - self.game.camera_y) * TILE_SIZE + 10
                
                # Item diamond(s)
                center = (screen_x + TILE_SIZE // 2, screen_y + TILE_SIZE // 2)
                
                if len(items) == 1:
                    # Single item - draw one diamond
                    points = [
                        (center[0], center[1] - 6),
                        (center[0] + 6, center[1]),
                        (center[0], center[1] + 6),
                        (center[0] - 6, center[1]),
                    ]
                    pygame.draw.polygon(self.game.game_surface, self.COLORS['item'], points)
                    pygame.draw.polygon(self.game.game_surface, self.COLORS['orange'], points, 1)
                else:
                    # Multiple items - draw stacked diamonds
                    for i in range(min(3, len(items))):  # Show max 3 items
                        offset = i * 3
                        points = [
                            (center[0] + offset, center[1] - 6),
                            (center[0] + 6 + offset, center[1]),
                            (center[0] + offset, center[1] + 6),
                            (center[0] - 6 + offset, center[1]),
                        ]
                        # Use different colors to show multiple items
                        color = self.game.COLORS['item'] if i == 0 else self.COLORS['light_gray']
                        pygame.draw.polygon(self.game.game_surface, color, points)
                        pygame.draw.polygon(self.game.game_surface, self.COLORS['orange'], points, 1)
                    
                    # Show count if more than 3 items
                    if len(items) > 3:
                        count_text = self.game.font_small.render(str(len(items)), True, self.COLORS['white'])
                        text_rect = count_text.get_rect(center=(center[0] + 12, center[1] - 8))
                        self.game.game_surface.blit(count_text, text_rect)
    
    def render_sidebar(self):
        """Render right sidebar with stats"""
        sidebar_x = self.game.game_area_width + 20
        y = 10
        
        # Background
        sidebar_rect = pygame.Rect(sidebar_x, 0, self.game.sidebar_width, SCREEN_HEIGHT)
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_bg'], sidebar_rect)
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_border'], sidebar_rect, 2)
        
        player = self.game.world.player
        
        # Player name
        title = self.game.font_large.render(player.name, True, self.COLORS['white'])
        self.game.game_surface.blit(title, (sidebar_x + 10, y))
        y += 40
        
        # Health bar
        self.render_bar(sidebar_x + 10, y, "HP", 
                       player.stats.current_health, player.stats.max_health,
                       self.game.COLORS['hp_bar'], self.COLORS['dark_red'])
        y += 30
        
        # Stamina bar
        self.render_bar(sidebar_x + 10, y, "ST",
                       player.stats.current_stamina, player.stats.max_stamina,
                       self.game.COLORS['stamina_bar'], self.COLORS['blue'])
        y += 40
        
        # Essences
        essence_label = self.game.font.render("ESSENCES", True, self.COLORS['white'])
        self.game.game_surface.blit(essence_label, (sidebar_x + 10, y))
        y += 25
        
        essence_colors = {
            'fire': self.game.COLORS['essence_fire'],
            'water': self.game.COLORS['essence_water'],
            'earth': self.game.COLORS['essence_earth'],
            'air': self.game.COLORS['essence_air'],
        }
        
        max_ess = player.inventory.max_essence
        for elem, amount in player.inventory.essences.items():
            color = essence_colors.get(elem, self.game.COLORS['white'])
            self.render_bar(sidebar_x + 10, y, elem[:3].upper(),
                           amount, max_ess, color, self.game.COLORS['dark_gray'], bar_width=150)
            y += 22
        
        y += 20
        
        # Stats
        stats_label = self.game.font.render("STATS", True, self.COLORS['white'])
        self.game.game_surface.blit(stats_label, (sidebar_x + 10, y))
        y += 25
        
        s = player.stats
        xp_to_next = player.xp_for_next_level()
        stats_text = [
            f"Level: {player.level}  XP: {player.experience}/{player.level * 100}",
            f"STR: {s.strength}  DEX: {s.dexterity}",
            f"CON: {s.constitution}  INT: {s.intelligence}",
            f"ATK: {s.attack_power}  DEF: {s.defense}",
        ]
        for line in stats_text:
            text = self.game.font_small.render(line, True, self.COLORS['light_gray'])
            self.game.game_surface.blit(text, (sidebar_x + 10, y))
            y += 18
        
        y += 20
        
        # Inventory
        inv_label = self.game.font.render("INVENTORY", True, self.COLORS['white'])
        self.game.game_surface.blit(inv_label, (sidebar_x + 10, y))
        y += 25
        
        if player.inventory.objects:
            # Separate items, solvents, and coagulants for display
            for i, item in enumerate(player.inventory.objects):
                item['index'] = i +1
            # items = [item['index']=i+1 for i, item in enumerate(player.inventory.objects)]
            items = [obj for obj in player.inventory.objects if not obj.get('is_solvent') and not obj.get('is_coagulant')]
            solvents = [obj for obj in player.inventory.objects if obj.get('is_solvent')]
            coagulants = [obj for obj in player.inventory.objects if obj.get('is_coagulant')]
            
            
            # Show regular items
            if items:
                for i, item in enumerate(items):  # Show first 8 items
                    # Item name with type color
                    type_colors = {
                        'weapon': self.game.COLORS['orange'],
                        'armor': self.game.COLORS['blue'], 
                        'potion': self.game.COLORS['green'],
                        'scroll': self.game.COLORS['purple'],
                        'essence': self.game.COLORS['cyan']
                    }
                    color = type_colors.get(item.get('type', ''), self.game.COLORS['light_gray'])
                    
                    item_text = f"{item['index']}. {item['name']} / {item['weight']}g"
                    
                    text = self.game.font_small.render(item_text, True, color)
                    self.game.game_surface.blit(text, (sidebar_x + 10, y))
                    y += 18
                
            # Show solvents
            if solvents:
                y += 5
                solvent_label = self.game.font_small.render("SOLVENTS:", True, self.COLORS['yellow'])
                self.game.game_surface.blit(solvent_label, (sidebar_x + 10, y))
                y += 18
                
                for i, solvent in enumerate(solvents):  # Show first 4 solvents
                    solvent_text = f"{solvent['index']}. {solvent['name']}"
                    color = self.game.COLORS['yellow']
                    text = self.game.font_small.render(solvent_text, True, color)
                    self.game.game_surface.blit(text, (sidebar_x + 10, y))
                    y += 18
                
            # Show coagulants
            if coagulants:
                y += 5
                coag_label = self.game.font_small.render("COAGULANTS:", True, self.COLORS['cyan'])
                self.game.game_surface.blit(coag_label, (sidebar_x + 10, y))
                y += 18

                for i, coag in enumerate(coagulants):  # Show first 4 coagulants
                    # Highlight if selected in transmute mode
                    if self.game.transmutation_engine.transmute_mode and self.game.transmutation_engine.transmute_coagulant == coag:
                        coag_text = f"> {coag['index']}. {coag['name']} ({coag.get('quantity', 0)}ml) <"
                        color = self.game.COLORS['cyan']
                    else:
                        coag_text = f"{coag['index']}. {coag['name']} ({coag.get('quantity', 0)}ml)"
                        color = self.game.COLORS['cyan']

                    text = self.game.font_small.render(coag_text, True, color)
                    self.game.game_surface.blit(text, (sidebar_x + 10, y))
                    y += 18
        else:
            empty_text = self.game.font_small.render("Empty", True, self.COLORS['gray'])
            self.game.game_surface.blit(empty_text, (sidebar_x + 10, y))
            y += 18
        
        y += 15
        
        # Movement mode
        if self.game.transmutation_engine.transmute_mode:
            mode_color = self.game.COLORS['cyan']
            step_names = ["Item", "Solvent", "Sol.Amt", "Coagulant", "Coag.Amt", "Pattern"]
            mode_text = f"MODE: TRANSMUTE ({step_names[self.game.transmutation_engine.transmute_step]})"
        elif self.game.meditate_mode:
            mode_color = self.game.COLORS['purple']
            mode_text = "MODE: MEDITATE"
        elif self.game.melee_target_mode:
            mode_color = self.game.COLORS['red']
            mode_text = "MODE: MELEE TARGET"
        elif self.game.spell_target_mode:
            player = self.game.world.player
            spell_range = 3 + int(player.stats.magic_power / 10)
            mode_color = self.game.COLORS['purple']
            mode_text = f"MODE: SPELL TARGET ({spell_range} tiles)"
        elif self.game.ranged_mode:
            mode_color = self.game.COLORS['orange']
            mode_text = f"MODE: RANGED ({self.game.ranged_range} tiles)"
        elif self.game.path_mode:
            mode_color = self.game.COLORS['green']
            mode_text = "MODE: PATHFINDING"
        else:
            mode_color = self.game.COLORS['white']
            mode_text = "MODE: WASD"

        # Autotarget indicator
        if self.game.autotarget_mode:
            mode_text += " [AUTO]"
            mode_color = self.game.COLORS['cyan']
        mode_label = self.game.font.render(mode_text, True, mode_color)
        self.game.game_surface.blit(mode_label, (sidebar_x + 10, y))
        y += 25
        
        # Path info
        if self.game.path_mode and self.path:
            path_text = f"Path: {len(self.game.path)} steps"
            path_label = self.game.font_small.render(path_text, True, self.COLORS['yellow'])
            self.game.game_surface.blit(path_label, (sidebar_x + 10, y))
            y += 20
        
        # Visible entities (using FOV system)
        visible = self.game.get_visible_info(radius=10)
        
        if visible['monsters']:
            for m in visible['monsters']:
                # Format: "Goblin:n3e2 (HP)"
                hp_text = f"{m['formatted']} ({m['hp']}/{m['max_hp']})"
                color = self.game.COLORS['orange'] if m['adjacent'] else self.game.COLORS['red']
                text = self.game.font_small.render(hp_text, True, color)
                self.game.game_surface.blit(text, (sidebar_x + 10, y))
                y += 16
        
        if visible['items']:
            for item in visible['items']:
                # Format: "Sword:n2w1"
                item_text = f"{item['formatted']}"
                color = self.game.COLORS['yellow'] if item['type'] == 'solvent' else self.COLORS['item']
                text = self.game.font_small.render(item_text, True, color)
                self.game.game_surface.blit(text, (sidebar_x + 10, y))
                y += 16
        else:
            text = self.game.font_small.render("No items visible", True, self.COLORS['gray'])
            self.game.game_surface.blit(text, (sidebar_x + 10, y))
    
    def render_bar(self, x: int, y: int, label: str, 
                   current: float, maximum: float,
                   fg_color, bg_color, bar_width: int = 180):
        """Render a status bar"""
        # Label
        label_text = self.game.font_small.render(label, True, self.COLORS['white'])
        self.game.game_surface.blit(label_text, (x, y))
        
        # Bar background
        bar_x = x + 35
        bar_rect = pygame.Rect(bar_x, y + 2, bar_width, 14)
        pygame.draw.rect(self.game.game_surface, bg_color, bar_rect)
        
        # Bar fill
        fill_width = int(bar_width * (current / maximum)) if maximum > 0 else 0
        fill_rect = pygame.Rect(bar_x, y + 2, fill_width, 14)
        pygame.draw.rect(self.game.game_surface, fg_color, fill_rect)
        
        # Border
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_border'], bar_rect, 1)
        
        # Value text
        value_text = self.game.font_small.render(f"{int(current)}/{int(maximum)}", True, self.COLORS['white'])
        text_rect = value_text.get_rect(center=(bar_x + bar_width // 2, y + 9))
        self.game.game_surface.blit(value_text, text_rect)
    
    def render_messages(self):
        """Render message log at bottom"""
        msg_y = self.game.game_area_height + 30
        
        # Background
        msg_rect = pygame.Rect(10, msg_y - 5, self.game.game_area_width, 100)
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_bg'], msg_rect)
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_border'], msg_rect, 1)
        
        # Messages
        for i, msg in enumerate(self.game.messages[-6:]):
            alpha = 128 + int(127 * (i / 6))
            text = self.game.font_small.render(msg, True, self.COLORS['light_gray'])
            self.game.game_surface.blit(text, (15, msg_y + i * 15))
    
    def render_overlay(self, overlay_title, render_text):
         # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(self.game.COLORS['black'])
        overlay.set_alpha(200)
        self.game.game_surface.blit(overlay, (0, 0))

        # Overlay window
        overlay_width = 600
        overlay_height = 500
        overlay_x = (SCREEN_WIDTH - overlay_width) // 2
        overlay_y = (SCREEN_HEIGHT - overlay_height) // 2

        # Background
        overlay_rect = pygame.Rect(overlay_x, overlay_y, overlay_width, overlay_height)
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_bg'], overlay_rect)
        pygame.draw.rect(self.game.game_surface, self.COLORS['purple'], overlay_rect, 3)

        # Title
        title = self.game.font_large.render(overlay_title, True, self.COLORS['purple'])
        title_rect = title.get_rect(centerx=overlay_x + overlay_width // 2, top=overlay_y + 15)
        self.game.game_surface.blit(title, title_rect)
        
        y = overlay_y + 60
        
        # Render content if provided
        if render_text:
            for line in render_text:
                if line["type"]=="header":
                    header = self.game.font_large.render(line["text"], True, self.COLORS[line["color"]])       
                    self.game.game_surface.blit(header, (overlay_x + 20, y))
                    y += 35
                elif line["type"]=="text":
                    content = self.game.font.render(line["text"], True, self.COLORS[line["color"]])
                    self.game.game_surface.blit(content, (overlay_x + 20, y))
                    y += 25
                elif line["type"]=="seperator":
                    y += 15
                    pygame.draw.line(self.game.screen, self.COLORS['ui_border'], (overlay_x + 15, y), (overlay_x + overlay_width - 15, y))
                    y += 15
        else:
            # Show placeholder text when no content provided
            placeholder = self.game.font.render("No content to display", True, self.COLORS['gray'])
            self.game.game_surface.blit(placeholder, (overlay_x + 20, y))

    def render_spell_book(self):

        """Render spell book overlay"""
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(self.game.COLORS['black'])
        overlay.set_alpha(200)
        self.game.game_surface.blit(overlay, (0, 0))

        # Spell book window
        book_width = 600
        book_height = 500
        book_x = (SCREEN_WIDTH - book_width) // 2
        book_y = (SCREEN_HEIGHT - book_height) // 2

        # Background
        book_rect = pygame.Rect(book_x, book_y, book_width, book_height)
        pygame.draw.rect(self.game.game_surface, self.COLORS['ui_bg'], book_rect)
        pygame.draw.rect(self.game.game_surface, self.COLORS['purple'], book_rect, 3)

        # Title
        title = self.game.font_large.render("SPELL BOOK", True, self.COLORS['purple'])
        title_rect = title.get_rect(centerx=book_x + book_width // 2, top=book_y + 15)
        self.game.game_surface.blit(title, title_rect)

        # Instructions
        instr = self.game.font_small.render("Press B to close", True, self.COLORS['gray'])
        self.game.game_surface.blit(instr, (book_x + book_width - 120, book_y + 20))

        y = book_y + 60

        if not self.game.spell_book:
            empty_text = self.game.font.render("No entries yet. Meditate (Q) on items to learn their essence.", True, self.COLORS['gray'])
            self.game.game_surface.blit(empty_text, (book_x + 20, y))
        else:
            # Column headers
            header_color = self.game.COLORS['cyan']
            self.game.game_surface.blit(self.game.font_small.render("NAME", True, header_color), (book_x + 20, y))

            # wrong! don't SHOW the synset
            # self.game.game_surface.blit(self.game.font_small.render("SYNSET", True, header_color), (book_x + 180, y))
            self.game.game_surface.blit(self.game.font_small.render("ESSENCE (F/W/E/A)", True, header_color), (book_x + 350, y))
            y += 25

            # Draw separator line
            pygame.draw.line(self.game.screen, self.COLORS['ui_border'], (book_x + 15, y), (book_x + book_width - 15, y))
            y += 10

            # List entries (scrollable area - show first 15)
            entries = list(self.game.spell_book.values())
            for i, entry in enumerate(entries):
                # Alternate row colors
                if i % 2 == 0:
                    row_rect = pygame.Rect(book_x + 15, y - 2, book_width - 30, 22)
                    pygame.draw.rect(self.game.game_surface, (40, 40, 50), row_rect)

                # Name (truncate if too long)
                name = entry.name
                name_text = self.game.font_small.render(name, True, self.COLORS['white'])
                self.game.game_surface.blit(name_text, (book_x + 20, y))

                # Synset #should never show [-20LLM]
                # synset = entry['synset'][:20] if len(entry['synset']) > 20 else entry['synset']
                # synset_text = self.game.font_small.render(synset, True, self.COLORS['light_gray'])
                # self.game.game_surface.blit(synset_text, (book_x + 180, y))

                # Essence composition
                comp = entry['composition']
                essence_str = f"F:{comp.get('fire', 0)} W:{comp.get('water', 0)} E:{comp.get('earth', 0)} A:{comp.get('air', 0)}"
                essence_text = self.game.font_small.render(essence_str, True, self.COLORS['yellow'])
                self.game.game_surface.blit(essence_text, (book_x + 350, y))

                y += 22

            # Show count if more entries
            if len(entries) > 15:
                more_text = self.game.font_small.render(f"...and {len(entries) - 15} more entries", True, self.COLORS['gray'])
                self.game.game_surface.blit(more_text, (book_x + 20, y + 10))

        # Footer with total count
        footer_y = book_y + book_height - 30
        pygame.draw.line(self.game.screen, self.COLORS['ui_border'], (book_x + 15, footer_y - 10), (book_x + book_width - 15, footer_y - 10))
        count_text = self.game.font_small.render(f"Total entries: {len(self.game.spell_book)}", True, self.COLORS['light_gray'])
        self.game.game_surface.blit(count_text, (book_x + 20, footer_y))

    def render_controls(self):
        controls_y = SCREEN_HEIGHT - 30
        
        if self.game.is_menu_mode():
            # Menu mode controls
            if self.game.show_spell_book:
                controls = "B: Close Spell Book"
            elif self.game.transmutation_engine.transmute_mode:
                step_hints = [
                    "1-9: Select item | ESC: Cancel",
                    "1-9: Select pattern | ESC: Cancel",
                ]
                controls = step_hints[self._transmute_step]
            elif self.game.meditate_mode:
                controls = "Click item to meditate | ESC: Cancel"
            elif self.game.show_drop_menu:
                controls = "Click item to drop | ESC: Cancel"
            elif self.game.melee_target_mode:
                controls = "LEFT CLICK: Select adjacent enemy to attack | ESC: Cancel"
            elif self.game.spell_target_mode:
                player = self.game.world.player
                spell_range = 3 + int(player.stats.magic_power / 10)
                controls = f"LEFT CLICK: Target enemy (range: {spell_range}) | ESC: Cancel spell"
            elif self.game.ranged_mode:
                controls = f"LEFT CLICK: Target enemy (range: {self.game.ranged_range}) | R: Exit ranged mode | ESC: Cancel"
            elif self.game.path_mode:
                controls = "LEFT CLICK: Set target | ENTER: Auto-move | RIGHT CLICK/P: Toggle mode | T: Autotarget | ESC: Quit"
            elif self.game.imgui_ui.speak_mode:
                controls = "Click item | Type syllables | SPEAK SPELL! | ESC: Cancel"
            else:
                controls = "ESC: Cancel"
        else:
            # Gameplay mode controls
            auto_status = "[AUTO ON]" if self.game.autotarget_mode else ""
            controls = f"WASD: Move | SPACE: Attack | Q: Meditate | V: Speak | B: Spell Book | T: Auto {auto_status} | G: Transmute | ESC: Quit"
        
        text = self.game.font_small.render(controls, True, self.COLORS['gray'])
        self.game.game_surface.blit(text, (10, controls_y))

    def render_transmutation(self):
        """Render transmutation mode overlay - simplified 2-step wizard"""
        imgui.set_next_window_size(700, 500, imgui.FIRST_USE_EVER)
        imgui.set_next_window_position(
            SCREEN_WIDTH // 2 - 350, SCREEN_HEIGHT // 2 - 250,
            imgui.FIRST_USE_EVER
        )

        expanded, opened = imgui.begin("Transmutation", True)
        if not opened:
            self.game.transmutation_engine.transmute_mode = False
            self._reset_transmute()
            imgui.end()
            return

        if not expanded:
            imgui.end()
            return

        # Two column layout
        imgui.columns(2, "transmute_cols", True)
        imgui.set_column_width(0, 400)

        # Left panel: current step
        self._render_transmute_left_panel()

        imgui.next_column()

        # Right panel: known essences reference
        self._render_transmute_right_panel()

        imgui.columns(1)

        # Bottom bar
        imgui.separator()
        if imgui.button("Cancel [ESC]"):
            self.game.transmutation_engine.transmute_mode = False
            self._reset_transmute()

        # Back button (if not on first step)
        if self._transmute_step > 0:
            imgui.same_line()
            if imgui.button("< Back"):
                self._transmute_step -= 1

        # Transmute button when ready
        if self._can_transmute():
            imgui.same_line(imgui.get_window_width() - 120)
            if imgui.button("TRANSMUTE!"):
                self._do_transmute()

        imgui.end()

    def _render_transmute_left_panel(self):
        """Render the left panel with step-by-step selections"""
        step_names = ["Select Item", "Select Pattern"]

        imgui.text_colored(f"Step {self._transmute_step + 1}/2: {step_names[self._transmute_step]}", 0.4, 0.8, 1.0)
        imgui.text_colored("(UP/DOWN + ENTER, or click)", 0.5, 0.5, 0.5)
        imgui.separator()

        # Show current selections
        imgui.text("Current Selections:")
        if self._transmute_item:
            imgui.bullet_text(f"Item: {self._transmute_item['name']}/{self._transmute_item['weight']}g")
            essence = self.game.controller.get_essence_for_item(self._transmute_item)
            if essence:
                imgui.same_line()
                self._render_essence_inline(essence)
            else:
                imgui.same_line()
                imgui.text_colored("(unknown)", 1.0, 0.3, 0.3)

        if self._transmute_pattern:
            imgui.bullet_text(f"Pattern: {self._transmute_pattern.name}")

        imgui.spacing()
        imgui.separator()
        imgui.spacing()

        # Get known patterns for step 1
        patterns = self.game.controller.get_known_essences()

        # Render current step
        if not patterns:
            imgui.text_colored("No patterns known!", 0.8, 0.3, 0.3)
            imgui.text("Meditate (Q) on items first.")
            return

        def select_pattern(pattern):
            self._transmute_pattern = pattern
            self.reset_selection("transmute_pattern")
            
            # Calculate transmutation cost using new system
            cost, target_weight, solvent, coagulant, error = self.calculate_required_amounts(pattern)
            
            if error:
                self.game.add_message(f"Cannot transmute: {error}")
            elif cost:
                # Store cost for display purposes only
                self._calculated_cost = cost
            else:
                self._calculated_cost = None

        def label_fn(entry, i):
            return entry.name

        self._render_selectable_list(
            list_id="transmute_pattern",
            items=patterns,
            label_fn=label_fn,
            on_select=select_pattern
        )

        # Show essence composition for selected pattern
        if self._transmute_pattern:
            imgui.spacing()
            imgui.text("Target essence:")
            imgui.same_line()
            self._render_essence_inline(self._transmute_pattern.composition)
            
            # Show automatically calculated amounts
            imgui.spacing()
            imgui.separator()
            imgui.text_colored("Automatically calculated amounts:", 0.4, 0.8, 1.0)
            
            # Show source item weight
            if self._transmute_item:
                source_weight = self._transmute_item.get('weight', 0)
                imgui.bullet_text(f"Source item weight: {source_weight:.1f}g")
            
            # Show target spell weight
            cost, target_weight, _, _, error = self.calculate_required_amounts(self._transmute_pattern)
            if target_weight:
                imgui.bullet_text(f"Target spell weight: {target_weight:.1f}g")
            
            if hasattr(self, '_calculated_cost') and self._calculated_cost:
                imgui.bullet_text(f"Essence Cost: {sum(self._calculated_cost.values()):.1f} total")
                
                # Show individual essence costs
                for element, amount in self._calculated_cost.items():
                    imgui.bullet_text(f"  {element.capitalize()}: {amount:.1f}")
            else:
                imgui.text_colored("No suitable materials available", 0.8, 0.3, 0.3)

    def _render_transmute_right_panel(self):
        """Render the right panel with known essences reference"""
        imgui.text_colored("Known Essences (Reference)", 0.8, 0.4, 1.0)
        imgui.separator()

        known = self.game.controller.get_known_essences()
        if not known:
            imgui.text_colored("No essences known!", 0.5, 0.5, 0.5)
            imgui.text("Meditate (Q) on items")
            imgui.text("to learn their essence.")
            return

        # Table
        imgui.columns(5, "essence_ref_table", True)
        imgui.set_column_width(0, 100)
        imgui.set_column_width(1, 35)
        imgui.set_column_width(2, 35)
        imgui.set_column_width(3, 35)
        imgui.set_column_width(4, 35)

        imgui.text("Name")
        imgui.next_column()
        imgui.text_colored("F", 1.0, 0.4, 0.2)
        imgui.next_column()
        imgui.text_colored("W", 0.2, 0.6, 1.0)
        imgui.next_column()
        imgui.text_colored("E", 0.6, 0.4, 0.2)
        imgui.next_column()
        imgui.text_colored("A", 0.7, 0.7, 1.0)
        imgui.next_column()

        imgui.separator()

        for entry in known:
            comp = entry.composition
            name = entry.name[:12] + ".." if len(entry.name) > 12 else entry.name

            imgui.text(name)
            imgui.next_column()
            imgui.text_colored(str(comp.get('fire', 0)), 1.0, 0.4, 0.2)
            imgui.next_column()
            imgui.text_colored(str(comp.get('water', 0)), 0.2, 0.6, 1.0)
            imgui.next_column()
            imgui.text_colored(str(comp.get('earth', 0)), 0.6, 0.4, 0.2)
            imgui.next_column()
            imgui.text_colored(str(comp.get('air', 0)), 0.7, 0.7, 1.0)
            imgui.next_column()

        imgui.columns(1)

    def _render_essence_inline(self, comp):
        """Render essence values inline with colors"""
        imgui.text_colored(f"F:{comp.get('fire', 0)}", 1.0, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"W:{comp.get('water', 0)}", 0.2, 0.6, 1.0)
        imgui.same_line()
        imgui.text_colored(f"E:{comp.get('earth', 0)}", 0.6, 0.4, 0.2)
        imgui.same_line()
        imgui.text_colored(f"A:{comp.get('air', 0)}", 0.7, 0.7, 1.0)

    def _can_transmute(self):
        """Check if all selections are complete for simplified 2-step system"""
        return (self._transmute_item is not None and
                self._transmute_pattern is not None)

    def _do_transmute(self):
        """Execute the transmutation for simplified 2-step system"""
        # For simplified system, pass None for solvent/coagulant and let controller handle it
        result = self.game.controller.transmute(
            item=self._transmute_item,
            solvent=None,
            solvent_amount=0,
            coagulant=None,
            coagulant_amount=0,
            pattern=self._transmute_pattern
        )

        self.game.add_message(result.message)
        self.game.transmutation_engine.transmute_mode = False
        self._reset_transmute()

    def _reset_transmute(self):
        """Reset all transmutation state for simplified 2-step system"""
        self._transmute_step = 0
        self._transmute_item = None
        self._transmute_pattern = None

    def reset_selection(self, list_id):
        """Reset selection for a specific list"""
        pass  # Simplified - would need full implementation

    def _render_selectable_list(self, list_id, items, label_fn, on_select):
        """Render a selectable list with ImGui"""
        if not items:
            imgui.text_colored("No items available!", 0.8, 0.3, 0.3)
            return

        # Show all items without arbitrary limits
        for i, item in enumerate(items):
            label = label_fn(item, i)
            if imgui.selectable(label, False)[0]:
                on_select(item)
                break

    def calculate_required_amounts(self, target_pattern):
        """Calculate required essence amounts for target transmutation using weight-based system"""
        if not target_pattern or not self._transmute_item:
            return None, None, None, None, "No source item selected"
        
        # Use the new cost calculation system
        cost, target_weight, solvent, coagulant, error = self.game.calculate_transmute_cost(self._transmute_item, target_pattern)
        
        if error:
            return None, None, None, None, error
        
        # Return cost as essence requirements
        return cost, target_weight, None, None, None