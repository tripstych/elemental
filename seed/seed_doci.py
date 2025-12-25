"""
Seed Configuration Editor - GUI for managing procedural terrain seed configurations.
Integrates with seed_world_generator.py for live preview generation.
"""

import traceback
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog, simpledialog
import json
import os
import random
import threading
from typing import Dict, Any, Optional, List
from PIL import Image, ImageTk
from game_object import GameObject

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "seed_config.json")

GROWTH_FUNCTIONS = [
    "radial", "branching", "directional", "clustered", "spiral",
    "river_network", "fractal_forest", "crystal_field_dla", "lsystem_vegetation"
]

COMMON_PARAMS = {
    "growth_rate": {"min": 0.1, "max": 5.0, "step": 0.1, "desc": "Speed of terrain growth"},
    "max_radius": {"min": 5, "max": 150, "step": 1, "desc": "Maximum spread radius"},
    "strength": {"min": 0.0, "max": 1.0, "step": 0.05, "desc": "Influence strength"},
    "elevation": {"min": -1.0, "max": 1.0, "step": 0.05, "desc": "Base elevation"},
    "decay": {"min": 0.5, "max": 1.0, "step": 0.01, "desc": "Decay rate per tile"},
    "spikiness": {"min": 0.0, "max": 1.0, "step": 0.05, "desc": "Terrain roughness"},
}

FUNCTION_PARAMS = {
    "branching": {
        "branches": {"min": 2, "max": 12, "step": 1, "desc": "Number of branches"},
        "branch_width": {"min": 1, "max": 10, "step": 1, "desc": "Branch width"},
    },
    "clustered": {
        "min_clusters": {"min": 1, "max": 20, "step": 1, "desc": "Min clusters"},
        "max_clusters": {"min": 2, "max": 30, "step": 1, "desc": "Max clusters"},
        "min_cluster_size": {"min": 1, "max": 15, "step": 1, "desc": "Min cluster size"},
        "max_cluster_size": {"min": 2, "max": 20, "step": 1, "desc": "Max cluster size"},
    },
    "spiral": {
        "spiral_tightness": {"min": 0.1, "max": 1.0, "step": 0.05, "desc": "Spiral tightness"},
    },
    "river_network": {
        "river_branches": {"min": 1, "max": 10, "step": 1, "desc": "Number of river branches"},
        "min_river_length": {"min": 5, "max": 50, "step": 1, "desc": "Minimum river length"},
        "river_brownian": {"min": 0.0, "max": 1.0, "step": 0.05, "desc": "River meandering factor"},
    },
    "fractal_forest": {
        "num_trees": {"min": 1, "max": 50, "step": 1, "desc": "Number of trees"},
        "tree_size": {"min": 2, "max": 20, "step": 1, "desc": "Initial tree size"},
        "tree_decay": {"min": 0.3, "max": 0.95, "step": 0.05, "desc": "Branch length decay"},
        "tree_angle_var": {"min": 10, "max": 60, "step": 5, "desc": "Angle variation"},
        "tree_depth": {"min": 2, "max": 8, "step": 1, "desc": "Recursion depth"},
        "tree_points": {"min": 20, "max": 200, "step": 10, "desc": "Points for random walk"},
    },
    "crystal_field_dla": {
        "num_clusters": {"min": 1, "max": 15, "step": 1, "desc": "Number of crystal clusters"},
        "particles_per_cluster": {"min": 10, "max": 100, "step": 5, "desc": "Particles per cluster"},
        "stick_prob": {"min": 0.1, "max": 1.0, "step": 0.05, "desc": "Particle stick probability"},
    },
    "lsystem_vegetation": {
        "num_plants": {"min": 1, "max": 50, "step": 1, "desc": "Number of plants"},
        "lsystem_iterations": {"min": 1, "max": 6, "step": 1, "desc": "L-system iterations"},
        "plant_step_size": {"min": 1, "max": 5, "step": 1, "desc": "Growth step size"},
        "plant_angle": {"min": 10, "max": 60, "step": 5, "desc": "Branch angle"},
    },
}


class SeedEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Seed Configuration Editor")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 700)
        
        self.colors = {
            "bg": "#1a1a2e",
            "bg_secondary": "#16213e",
            "bg_tertiary": "#0f3460",
            "fg": "#eaeaea",
            "fg_dim": "#a0a0a0",
            "accent": "#e94560",
            "accent2": "#0f3460",
            "success": "#4ecca3",
            "warning": "#ffc93c",
        }
        
        self.root.configure(bg=self.colors["bg"])
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()
        
        self.config: Dict[str, Any] = {}
        self.current_seed: Optional[str] = None
        self.unsaved_changes = False
        self.param_vars: Dict[str, tk.Variable] = {}
        self.param_widgets: Dict[str, Any] = {}
        self.preview_image = None
        self.generating = False
        self.placed_seeds: List[Dict] = []  # Manual seed placements
        
        self._create_ui()
        self._load_config()
        
    def _configure_styles(self):
        self.style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"])
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 10))
        self.style.configure("TButton", background=self.colors["bg_tertiary"], foreground=self.colors["fg"], font=("Segoe UI", 10), padding=8)
        self.style.map("TButton", background=[("active", self.colors["accent"])])
        self.style.configure("Accent.TButton", background=self.colors["accent"], foreground="white", font=("Segoe UI", 10, "bold"))
        self.style.map("Accent.TButton", background=[("active", "#ff6b6b")])
        self.style.configure("Success.TButton", background=self.colors["success"], foreground="#1a1a2e", font=("Segoe UI", 10, "bold"))
        self.style.configure("TEntry", fieldbackground=self.colors["bg_secondary"], foreground=self.colors["fg"])
        self.style.configure("TCombobox", fieldbackground=self.colors["bg_secondary"], foreground=self.colors["fg"])
        self.style.configure("Horizontal.TScale", background=self.colors["bg"], troughcolor=self.colors["bg_tertiary"])
        self.style.configure("TLabelframe", background=self.colors["bg"])
        self.style.configure("TLabelframe.Label", background=self.colors["bg"], foreground=self.colors["accent"], font=("Segoe UI", 11, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.colors["accent"])
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.colors["fg"])
        self.style.configure("Dim.TLabel", foreground=self.colors["fg_dim"], font=("Segoe UI", 9))
        
    def _create_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Seed list
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        ttk.Label(left_panel, text="🌍 Seed Types", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.seed_listbox = tk.Listbox(
            list_frame, bg=self.colors["bg_secondary"], fg=self.colors["fg"],
            selectbackground=self.colors["accent"], selectforeground="white",
            font=("Segoe UI", 11), borderwidth=0, highlightthickness=2,
            highlightcolor=self.colors["accent"], highlightbackground=self.colors["bg_tertiary"],
            yscrollcommand=scrollbar.set, activestyle="none"
        )
        self.seed_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.seed_listbox.yview)
        self.seed_listbox.bind("<<ListboxSelect>>", self._on_seed_select)
        
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="+ Add", command=self._add_seed, style="Accent.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(btn_frame, text="Duplicate", command=self._duplicate_seed).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        ttk.Button(btn_frame, text="Delete", command=self._delete_seed).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Center panel - Editor
        center_panel = ttk.Frame(main_frame)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Top bar
        top_bar = ttk.Frame(center_panel)
        top_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.seed_name_var = tk.StringVar(value="Select a seed type")
        ttk.Label(top_bar, textvariable=self.seed_name_var, style="Header.TLabel").pack(side=tk.LEFT)
        
        ttk.Button(top_bar, text="💾 Save Config", command=self._save_config, style="Success.TButton").pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(top_bar, text="📂 Load", command=self._load_config_dialog).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(top_bar, text="📤 Export", command=self._export_config).pack(side=tk.RIGHT)
        
        # Scrollable editor area
        editor_canvas = tk.Canvas(center_panel, bg=self.colors["bg"], highlightthickness=0)
        editor_scrollbar = ttk.Scrollbar(center_panel, orient=tk.VERTICAL, command=editor_canvas.yview)
        self.editor_frame = ttk.Frame(editor_canvas)
        
        self.editor_frame.bind("<Configure>", lambda e: editor_canvas.configure(scrollregion=editor_canvas.bbox("all")))
        editor_canvas.create_window((0, 0), window=self.editor_frame, anchor="nw")
        editor_canvas.configure(yscrollcommand=editor_scrollbar.set)
        
        editor_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        editor_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            editor_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        editor_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Right panel - Preview & Seed Placement (40% width)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(right_panel, text="🖼️ Preview & World", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        preview_frame = ttk.Frame(right_panel)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_label = tk.Label(preview_frame, bg=self.colors["bg_secondary"], text="Generate a preview", fg=self.colors["fg_dim"], font=("Segoe UI", 10))
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        preview_controls = ttk.Frame(right_panel)
        preview_controls.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(preview_controls, text="World Seed:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.world_seed_var = tk.StringVar(value="42")
        seed_entry = ttk.Entry(preview_controls, textvariable=self.world_seed_var, width=8)
        seed_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(preview_controls, text="Size:", style="Dim.TLabel").pack(side=tk.LEFT)
        self.preview_size_var = tk.StringVar(value="150")
        size_entry = ttk.Entry(preview_controls, textvariable=self.preview_size_var, width=5)
        size_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Seed Placement Section
        placement_frame = ttk.LabelFrame(right_panel, text="🌱 Seed Placement", padding=8)
        placement_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Place single seed
        single_row = ttk.Frame(placement_frame)
        single_row.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(single_row, text="X:", width=3).pack(side=tk.LEFT)
        self.place_x_var = tk.StringVar(value="100")
        ttk.Entry(single_row, textvariable=self.place_x_var, width=5).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(single_row, text="Y:", width=3).pack(side=tk.LEFT)
        self.place_y_var = tk.StringVar(value="100")
        ttk.Entry(single_row, textvariable=self.place_y_var, width=5).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(single_row, text="Type:").pack(side=tk.LEFT, padx=(5, 0))
        self.place_type_var = tk.StringVar(value="")
        self.place_type_combo = ttk.Combobox(single_row, textvariable=self.place_type_var, width=12, state="readonly")
        self.place_type_combo.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Button(single_row, text="+ Place", command=self._place_single_seed).pack(side=tk.LEFT)
        
        # Place N random seeds
        random_row = ttk.Frame(placement_frame)
        random_row.pack(fill=tk.X, pady=(5, 5))
        
        ttk.Label(random_row, text="Count:", width=6).pack(side=tk.LEFT)
        self.random_count_var = tk.StringVar(value="5")
        ttk.Entry(random_row, textvariable=self.random_count_var, width=4).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(random_row, text="Type:").pack(side=tk.LEFT, padx=(5, 0))
        self.random_type_var = tk.StringVar(value="random")
        self.random_type_combo = ttk.Combobox(random_row, textvariable=self.random_type_var, width=12, state="readonly")
        self.random_type_combo.pack(side=tk.LEFT, padx=(5, 5))
        
        ttk.Button(random_row, text="+ Place Random", command=self._place_random_seeds).pack(side=tk.LEFT)
        
        # Placed seeds list
        list_row = ttk.Frame(placement_frame)
        list_row.pack(fill=tk.X, pady=(5, 0))
        
        self.placed_listbox = tk.Listbox(list_row, bg=self.colors["bg_secondary"], fg=self.colors["fg"],
                                         height=4, font=("Segoe UI", 9), selectbackground=self.colors["accent"])
        self.placed_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        list_btn_frame = ttk.Frame(list_row)
        list_btn_frame.pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(list_btn_frame, text="❌", width=3, command=self._remove_placed_seed).pack(pady=1)
        ttk.Button(list_btn_frame, text="🗑️", width=3, command=self._clear_placed_seeds).pack(pady=1)
        
        # Action buttons
        btn_row = ttk.Frame(right_panel)
        btn_row.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_row, text="🔄 Generate", command=self._generate_preview, style="Accent.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(btn_row, text="🗑️ Clear Map", command=self._clear_map).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(right_panel, textvariable=self.status_var, style="Dim.TLabel").pack(anchor=tk.W, pady=(10, 0))
        
    def _load_config(self, filepath: str = None):
        path = filepath or CONFIG_PATH
        try:
            with open(path, 'r') as f:
                self.config = json.load(f)
            self._populate_seed_list()
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
        except FileNotFoundError:
            self.config = {}
            self.status_var.set("No config found - start fresh!")
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON: {e}")
            
    def _populate_seed_list(self):
        self.seed_listbox.delete(0, tk.END)
        seed_types = sorted(self.config.keys())
        for seed_name in seed_types:
            self.seed_listbox.insert(tk.END, f"  {seed_name}")
        if self.config:
            self.seed_listbox.select_set(0)
            self._on_seed_select(None)
        # Update placement combo boxes
        self.place_type_combo['values'] = seed_types
        self.random_type_combo['values'] = ['random'] + seed_types
        if seed_types:
            self.place_type_var.set(seed_types[0])
            self.random_type_var.set('random')
            
    def _on_seed_select(self, event):
        selection = self.seed_listbox.curselection()
        if not selection:
            return
        seed_name = self.seed_listbox.get(selection[0]).strip()
        self.current_seed = seed_name
        self.seed_name_var.set(f"✏️ {seed_name}")
        self._build_editor()
        
    def _build_editor(self):
        for widget in self.editor_frame.winfo_children():
            widget.destroy()
        self.param_vars.clear()
        self.param_widgets.clear()
        
        if not self.current_seed or self.current_seed not in self.config:
            return
            
        seed_data = self.config[self.current_seed]
        
        # Basic Info Section
        basic_frame = ttk.LabelFrame(self.editor_frame, text="Basic Info", padding=10)
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Name (editable)
        row = ttk.Frame(basic_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Name:", width=15).pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self.current_seed)
        name_entry = ttk.Entry(row, textvariable=self.name_var, width=30)
        name_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row, text="Rename", command=self._rename_seed).pack(side=tk.LEFT)
        
        # Description
        row = ttk.Frame(basic_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Description:", width=15).pack(side=tk.LEFT)
        self.desc_var = tk.StringVar(value=seed_data.get("description", ""))
        desc_entry = ttk.Entry(row, textvariable=self.desc_var, width=50)
        desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        desc_entry.bind("<KeyRelease>", lambda e: self._update_param("description", self.desc_var.get()))
        
        # Color
        row = ttk.Frame(basic_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Color:", width=15).pack(side=tk.LEFT)
        self.color_var = tk.StringVar(value=seed_data.get("color", "#888888"))
        self.color_preview = tk.Label(row, bg=self.color_var.get(), width=4, height=1, relief="solid")
        self.color_preview.pack(side=tk.LEFT)
        color_entry = ttk.Entry(row, textvariable=self.color_var, width=10)
        color_entry.pack(side=tk.LEFT, padx=(5, 5))
        color_entry.bind("<KeyRelease>", self._on_color_change)
        ttk.Button(row, text="Pick", command=self._pick_color).pack(side=tk.LEFT)
        
        # Growth Function
        growth_frame = ttk.LabelFrame(self.editor_frame, text="Growth Function", padding=10)
        growth_frame.pack(fill=tk.X, pady=(0, 10))
        
        row = ttk.Frame(growth_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Function:", width=15).pack(side=tk.LEFT)
        self.growth_func_var = tk.StringVar(value=seed_data.get("growth_function", "radial"))
        growth_combo = ttk.Combobox(row, textvariable=self.growth_func_var, values=GROWTH_FUNCTIONS, state="readonly", width=20)
        growth_combo.pack(side=tk.LEFT)
        growth_combo.bind("<<ComboboxSelected>>", self._on_growth_function_change)
        
        # Common Parameters
        common_frame = ttk.LabelFrame(self.editor_frame, text="Common Parameters", padding=10)
        common_frame.pack(fill=tk.X, pady=(0, 10))
        
        for param_name, param_info in COMMON_PARAMS.items():
            self._create_slider_row(common_frame, param_name, param_info, seed_data.get(param_name, param_info["min"]))
        
        # Function-specific parameters
        growth_func = seed_data.get("growth_function", "radial")
        if growth_func in FUNCTION_PARAMS:
            func_frame = ttk.LabelFrame(self.editor_frame, text=f"{growth_func.title()} Parameters", padding=10)
            func_frame.pack(fill=tk.X, pady=(0, 10))
            self.func_specific_frame = func_frame
            
            for param_name, param_info in FUNCTION_PARAMS[growth_func].items():
                self._create_slider_row(func_frame, param_name, param_info, seed_data.get(param_name, param_info["min"]))
        
        # Resources
        res_frame = ttk.LabelFrame(self.editor_frame, text="Resources", padding=10)
        res_frame.pack(fill=tk.X, pady=(0, 10))
        
        resources = seed_data.get("resources", [])
        
        res_list_frame = ttk.Frame(res_frame)
        res_list_frame.pack(fill=tk.X)
        
        self.resource_listbox = tk.Listbox(res_list_frame, bg=self.colors["bg_secondary"], fg=self.colors["fg"],
                                           height=4, font=("Segoe UI", 10), selectbackground=self.colors["accent"])
        self.resource_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for res in resources:
            self.resource_listbox.insert(tk.END, res)
        
        res_btn_frame = ttk.Frame(res_list_frame)
        res_btn_frame.pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(res_btn_frame, text="+", width=3, command=self._add_resource).pack(pady=2)
        ttk.Button(res_btn_frame, text="-", width=3, command=self._remove_resource).pack(pady=2)
        
    def _create_slider_row(self, parent, param_name, param_info, current_value):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=4)
        
        ttk.Label(row, text=f"{param_name.replace('_', ' ').title()}:", width=18).pack(side=tk.LEFT)
        
        var = tk.DoubleVar(value=current_value)
        self.param_vars[param_name] = var
        
        slider = ttk.Scale(row, from_=param_info["min"], to=param_info["max"], variable=var, orient=tk.HORIZONTAL, length=200)
        slider.pack(side=tk.LEFT, padx=(0, 10))
        
        value_label = ttk.Label(row, text=f"{current_value:.2f}", width=8)
        value_label.pack(side=tk.LEFT)
        
        ttk.Label(row, text=param_info["desc"], style="Dim.TLabel").pack(side=tk.LEFT, padx=(10, 0))
        
        def on_change(*args):
            val = var.get()
            step = param_info["step"]
            snapped = round(val / step) * step
            value_label.config(text=f"{snapped:.2f}")
            self._update_param(param_name, snapped)
        
        var.trace_add("write", on_change)
        self.param_widgets[param_name] = (slider, value_label)
        
    def _update_param(self, param_name, value):
        if self.current_seed and self.current_seed in self.config:
            self.config[self.current_seed][param_name] = value
            self.unsaved_changes = True
            
    def _on_color_change(self, event=None):
        color = self.color_var.get()
        try:
            self.color_preview.config(bg=color)
            self._update_param("color", color)
        except:
            pass
            
    def _pick_color(self):
        color = colorchooser.askcolor(color=self.color_var.get(), title="Choose Color")
        if color[1]:
            self.color_var.set(color[1])
            self.color_preview.config(bg=color[1])
            self._update_param("color", color[1])
            
    def _on_growth_function_change(self, event=None):
        new_func = self.growth_func_var.get()
        self._update_param("growth_function", new_func)
        self._build_editor()
        
    def _add_resource(self):
        resource = simpledialog.askstring("Add Resource", "Enter resource name:")
        if resource:
            self.resource_listbox.insert(tk.END, resource)
            self._update_resources()
            
    def _remove_resource(self):
        selection = self.resource_listbox.curselection()
        if selection:
            self.resource_listbox.delete(selection[0])
            self._update_resources()
            
    def _update_resources(self):
        resources = list(self.resource_listbox.get(0, tk.END))
        self._update_param("resources", resources)
        
    def _rename_seed(self):
        new_name = self.name_var.get().strip().lower().replace(" ", "_")
        if not new_name:
            return
        if new_name == self.current_seed:
            return
        if new_name in self.config:
            messagebox.showerror("Error", f"Seed '{new_name}' already exists!")
            return
        
        self.config[new_name] = self.config.pop(self.current_seed)
        self.current_seed = new_name
        self._populate_seed_list()
        
        for i in range(self.seed_listbox.size()):
            if self.seed_listbox.get(i).strip() == new_name:
                self.seed_listbox.select_set(i)
                break
        self.seed_name_var.set(f"✏️ {new_name}")
        
    def _add_seed(self):
        name = simpledialog.askstring("New Seed Type", "Enter seed type name:")
        if not name:
            return
        name = name.strip().lower().replace(" ", "_")
        if name in self.config:
            messagebox.showerror("Error", f"Seed '{name}' already exists!")
            return
        
        self.config[name] = {
            "growth_function": "radial",
            "growth_rate": 1.0,
            "max_radius": 30,
            "strength": 0.5,
            "elevation": 0.2,
            "color": "#888888",
            "resources": [],
            "decay": 0.85,
            "spikiness": 0.5,
            "description": f"New {name} terrain"
        }
        self._populate_seed_list()
        
        for i in range(self.seed_listbox.size()):
            if self.seed_listbox.get(i).strip() == name:
                self.seed_listbox.select_set(i)
                self._on_seed_select(None)
                break
                
    def _duplicate_seed(self):
        if not self.current_seed:
            return
        name = simpledialog.askstring("Duplicate Seed", "Enter new name:", initialvalue=f"{self.current_seed}_copy")
        if not name:
            return
        name = name.strip().lower().replace(" ", "_")
        if name in self.config:
            messagebox.showerror("Error", f"Seed '{name}' already exists!")
            return
        
        import copy
        self.config[name] = copy.deepcopy(self.config[self.current_seed])
        self._populate_seed_list()
        
    def _delete_seed(self):
        if not self.current_seed:
            return
        if messagebox.askyesno("Confirm Delete", f"Delete '{self.current_seed}'?"):
            del self.config[self.current_seed]
            self.current_seed = None
            self._populate_seed_list()
            for widget in self.editor_frame.winfo_children():
                widget.destroy()
            self.seed_name_var.set("Select a seed type")
            
    def _save_config(self):
        try:
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.unsaved_changes = False
            self.status_var.set("✅ Saved successfully!")
            messagebox.showinfo("Saved", f"Configuration saved to:\n{CONFIG_PATH}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
            
    def _load_config_dialog(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(CONFIG_PATH)
        )
        if filepath:
            self._load_config(filepath)
            
    def _export_config(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="seed_config_export.json",
            initialdir=os.path.dirname(CONFIG_PATH)
        )
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(self.config, f, indent=2)
                self.status_var.set(f"✅ Exported to {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")
    
    def _place_single_seed(self):
        """Place a single seed at specified coordinates"""
        try:
            x = int(self.place_x_var.get())
            y = int(self.place_y_var.get())
            seed_type = self.place_type_var.get()
            if not seed_type:
                messagebox.showwarning("Warning", "Select a seed type first!")
                return
            self.placed_seeds.append({'x': x, 'y': y, 'type': seed_type})
            self.placed_listbox.insert(tk.END, f"{seed_type} @ ({x}, {y})")
            self.status_var.set(f"✅ Placed {seed_type} at ({x}, {y})")
        except ValueError:
            messagebox.showerror("Error", "X and Y must be valid integers!")
    
    def _place_random_seeds(self):
        """Place N random seeds"""
        try:
            count = int(self.random_count_var.get())
            size = int(self.preview_size_var.get())
            seed_type = self.random_type_var.get()
            seed_types = list(self.config.keys())
            
            if not seed_types:
                messagebox.showwarning("Warning", "No seed types defined!")
                return
            
            for _ in range(count):
                x = random.randint(0, size - 1)
                y = random.randint(0, size - 1)
                if seed_type == 'random':
                    chosen_type = random.choice(seed_types)
                else:
                    chosen_type = seed_type
                self.placed_seeds.append({'x': x, 'y': y, 'type': chosen_type})
                self.placed_listbox.insert(tk.END, f"{chosen_type} @ ({x}, {y})")
            
            self.status_var.set(f"✅ Placed {count} random seeds")
        except ValueError:
            messagebox.showerror("Error", "Count must be a valid integer!")
    
    def _remove_placed_seed(self):
        """Remove selected seed from placement list"""
        selection = self.placed_listbox.curselection()
        if selection:
            idx = selection[0]
            self.placed_listbox.delete(idx)
            del self.placed_seeds[idx]
            self.status_var.set("Removed seed from list")
    
    def _clear_placed_seeds(self):
        """Clear all placed seeds"""
        self.placed_seeds.clear()
        self.placed_listbox.delete(0, tk.END)
        self.status_var.set("Cleared all placed seeds")
    
    def _clear_map(self):
        """Clear the map and all placed seeds"""
        self.placed_seeds.clear()
        self.placed_listbox.delete(0, tk.END)
        self.preview_label.config(text="Map cleared - Generate a new preview", image="")
        self.preview_image = None
        self.status_var.set("🗑️ Map cleared")
                
    def _generate_preview(self):
        if self.generating:
            return
        self.generating = True
        self.status_var.set("⏳ Generating preview...")
        self.preview_label.config(text="Generating...", image="")
        
        # Capture placed seeds for thread
        placed_seeds_copy = self.placed_seeds.copy()
        
        def generate():
            try:
                from seed_world_generator import SeedWorldGenerator
                from growth_patterns import GrowthPatterns
                
                # Map function names to actual functions
                func_map = {
                    "radial": GrowthPatterns.radial,
                    "branching": GrowthPatterns.branching,
                    "directional": GrowthPatterns.directional,
                    "clustered": GrowthPatterns.clustered,
                    "spiral": GrowthPatterns.spiral,
                    "river_network": GrowthPatterns.river_network,
                    "fractal_forest": GrowthPatterns.fractal_forest,
                    "crystal_field_dla": GrowthPatterns.crystal_field_dla,
                    "lsystem_vegetation": GrowthPatterns.lsystem_vegetation,
                }
                
                # Build definitions with function references
                definitions = {}
                for name, cfg in self.config.items():
                    cfg_copy = cfg.copy()
                    func_name = cfg_copy.get("growth_function", "radial")
                    cfg_copy["growth_function"] = func_map.get(func_name, GrowthPatterns.radial)
                    definitions[name] = cfg_copy
                
                size = int(self.preview_size_var.get())
                world_seed = int(self.world_seed_var.get())
                
                world = SeedWorldGenerator(width=size, height=size, seed_definitions=definitions, world_seed=world_seed)
                
                # Use placed seeds if any, otherwise use random
                if placed_seeds_copy:
                    for seed in placed_seeds_copy:
                        world.add_seed(x=seed['x'], y=seed['y'], seed_type=seed['type'])
                else:
                    world.random_seeds()
                
                world.grow_seeds(iterations=60)
                
                preview_path = os.path.join(os.path.dirname(__file__), "preview_temp.png")
                world.visualize(preview_path)
                
                self.root.after(0, lambda p=preview_path: self._show_preview(p))
                
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda err=error_msg: self._preview_error(err))
                traceback.print_exc()
            finally:
                self.generating = False
        
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
        
    def _show_preview(self, path):
        try:
            img = Image.open(path)
            # Larger preview for 40% width panel
            img.thumbnail((600, 800), Image.Resampling.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self.preview_image, text="")
            self.status_var.set("✅ Preview generated!")
        except Exception as e:
            self._preview_error(str(e))
            
    def _preview_error(self, error):
        self.status_var.set(f"❌ Error: {error}")
        self.preview_label.config(text=f"Error:\n{error}", image="")


def main():
    root = tk.Tk()
    app = SeedEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
