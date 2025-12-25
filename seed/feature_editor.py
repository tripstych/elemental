"""
Landscape Features Editor - GUI for managing terrain feature configurations.
Edits data/landscape_features.json for procedural terrain decoration.
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, filedialog, simpledialog
import json
import os
from typing import Dict, Any, Optional, List
from paths import LANDSCAPE_FEATURES

CONFIG_PATH = LANDSCAPE_FEATURES

AVAILABLE_COLORS = [
    "green", "dark_green", "yellow", "gray", "brown", "red", "blue", 
    "cyan", "dark_cyan", "white", "black", "orange", "purple", "pink"
]


class FeatureEditor:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Landscape Features Editor")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
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
        self.current_terrain: Optional[str] = None
        self.current_feature_idx: Optional[int] = None
        self.unsaved_changes = False
        
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
        self.style.configure("TCombobox", fieldbackground="white", foreground="black")
        self.style.map("TCombobox", fieldbackground=[("readonly", "white")], foreground=[("readonly", "black")])
        self.style.configure("TSpinbox", fieldbackground="white", foreground="black")
        self.style.configure("Horizontal.TScale", background=self.colors["bg"], troughcolor=self.colors["bg_tertiary"])
        self.style.configure("TLabelframe", background=self.colors["bg"])
        self.style.configure("TLabelframe.Label", background=self.colors["bg"], foreground=self.colors["accent"], font=("Segoe UI", 11, "bold"))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=self.colors["accent"])
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.colors["fg"])
        self.style.configure("Dim.TLabel", foreground=self.colors["fg_dim"], font=("Segoe UI", 9))
        self.style.configure("TCheckbutton", background=self.colors["bg"], foreground=self.colors["fg"])
        
    def _create_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Terrain list
        left_panel = ttk.Frame(main_frame, width=200)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        ttk.Label(left_panel, text="🏞️ Terrains", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.terrain_listbox = tk.Listbox(
            list_frame, bg=self.colors["bg_secondary"], fg=self.colors["fg"],
            selectbackground=self.colors["accent"], selectforeground="white",
            font=("Segoe UI", 11), borderwidth=0, highlightthickness=2,
            highlightcolor=self.colors["accent"], highlightbackground=self.colors["bg_tertiary"],
            yscrollcommand=scrollbar.set, activestyle="none", exportselection=False
        )
        self.terrain_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.terrain_listbox.yview)
        self.terrain_listbox.bind("<<ListboxSelect>>", self._on_terrain_select)
        
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="+ Add", command=self._add_terrain, style="Accent.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(btn_frame, text="Delete", command=self._delete_terrain).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Center panel - Features list
        center_panel = ttk.Frame(main_frame, width=250)
        center_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        center_panel.pack_propagate(False)
        
        ttk.Label(center_panel, text="🌿 Features", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 10))
        
        feature_list_frame = ttk.Frame(center_panel)
        feature_list_frame.pack(fill=tk.BOTH, expand=True)
        
        feature_scrollbar = ttk.Scrollbar(feature_list_frame)
        feature_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.feature_listbox = tk.Listbox(
            feature_list_frame, bg=self.colors["bg_secondary"], fg=self.colors["fg"],
            selectbackground=self.colors["accent"], selectforeground="white",
            font=("Segoe UI", 11), borderwidth=0, highlightthickness=2,
            highlightcolor=self.colors["accent"], highlightbackground=self.colors["bg_tertiary"],
            yscrollcommand=feature_scrollbar.set, activestyle="none", exportselection=False
        )
        self.feature_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        feature_scrollbar.config(command=self.feature_listbox.yview)
        self.feature_listbox.bind("<<ListboxSelect>>", self._on_feature_select)
        
        feature_btn_frame = ttk.Frame(center_panel)
        feature_btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(feature_btn_frame, text="+ Add", command=self._add_feature, style="Accent.TButton").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(feature_btn_frame, text="Delete", command=self._delete_feature).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Right panel - Editor
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Top bar
        top_bar = ttk.Frame(right_panel)
        top_bar.pack(fill=tk.X, pady=(0, 10))
        
        self.editor_title_var = tk.StringVar(value="Select a terrain")
        ttk.Label(top_bar, textvariable=self.editor_title_var, style="Header.TLabel").pack(side=tk.LEFT)
        
        ttk.Button(top_bar, text="💾 Save", command=self._save_config, style="Success.TButton").pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(top_bar, text="📂 Load", command=self._load_config_dialog).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(top_bar, text="📤 Export", command=self._export_config).pack(side=tk.RIGHT)
        
        # Editor area
        self.editor_frame = ttk.Frame(right_panel)
        self.editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(right_panel, textvariable=self.status_var, style="Dim.TLabel").pack(anchor=tk.W, pady=(10, 0))
        
    def _load_config(self, filepath: str = None):
        path = filepath or CONFIG_PATH
        try:
            with open(path, 'r') as f:
                self.config = json.load(f)
            self._populate_terrain_list()
            self.status_var.set(f"Loaded: {os.path.basename(path)}")
        except FileNotFoundError:
            self.config = {}
            self.status_var.set("No config found - start fresh!")
        except json.JSONDecodeError as e:
            messagebox.showerror("Error", f"Invalid JSON: {e}")
            
    def _populate_terrain_list(self):
        self.terrain_listbox.delete(0, tk.END)
        for terrain_name in sorted(self.config.keys()):
            self.terrain_listbox.insert(tk.END, f"  {terrain_name}")
        if self.config:
            self.terrain_listbox.select_set(0)
            self._on_terrain_select(None)
            
    def _on_terrain_select(self, event):
        selection = self.terrain_listbox.curselection()
        if not selection:
            return
        terrain_name = self.terrain_listbox.get(selection[0]).strip()
        self.current_terrain = terrain_name
        self.current_feature_idx = None
        self.editor_title_var.set(f"✏️ {terrain_name}")
        self._populate_feature_list()
        self._build_terrain_editor()
        
    def _populate_feature_list(self):
        self.feature_listbox.delete(0, tk.END)
        if not self.current_terrain or self.current_terrain not in self.config:
            return
        features = self.config[self.current_terrain].get("features", [])
        for feat in features:
            self.feature_listbox.insert(tk.END, f"  [{feat['char']}] {feat['name']}")
        if features:
            self.feature_listbox.select_set(0)
            self.current_feature_idx = 0
            
    def _on_feature_select(self, event):
        selection = self.feature_listbox.curselection()
        if not selection:
            return
        self.current_feature_idx = selection[0]
        self._build_feature_editor()
        
    def _build_terrain_editor(self):
        for widget in self.editor_frame.winfo_children():
            widget.destroy()
            
        if not self.current_terrain or self.current_terrain not in self.config:
            return
            
        terrain_data = self.config[self.current_terrain]
        
        # Terrain Name
        name_frame = ttk.LabelFrame(self.editor_frame, text="Terrain", padding=10)
        name_frame.pack(fill=tk.X, pady=(0, 10))
        
        row = ttk.Frame(name_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Name:", width=15).pack(side=tk.LEFT)
        self.terrain_name_var = tk.StringVar(value=self.current_terrain)
        name_entry = ttk.Entry(row, textvariable=self.terrain_name_var, width=25)
        name_entry.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row, text="Rename", command=self._rename_terrain).pack(side=tk.LEFT)
        
        # Ground Settings
        ground_frame = ttk.LabelFrame(self.editor_frame, text="Ground Settings", padding=10)
        ground_frame.pack(fill=tk.X, pady=(0, 10))
        
        row = ttk.Frame(ground_frame)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="Ground Char:", width=15).pack(side=tk.LEFT)
        self.ground_char_var = tk.StringVar(value=terrain_data.get("ground_char", "."))
        char_entry = ttk.Entry(row, textvariable=self.ground_char_var, width=5)
        char_entry.pack(side=tk.LEFT, padx=(0, 20))
        char_entry.bind("<KeyRelease>", lambda e: self._update_terrain_param("ground_char", self.ground_char_var.get()[:1]))
        
        ttk.Label(row, text="Ground Color:").pack(side=tk.LEFT)
        self.ground_color_var = tk.StringVar(value=terrain_data.get("ground_color", "green"))
        color_combo = ttk.Combobox(row, textvariable=self.ground_color_var, values=AVAILABLE_COLORS, width=12, state="readonly")
        color_combo.pack(side=tk.LEFT, padx=(5, 0))
        color_combo.bind("<<ComboboxSelected>>", lambda e: self._update_terrain_param("ground_color", self.ground_color_var.get()))
        
        # Feature Editor Area
        self.feature_editor_frame = ttk.LabelFrame(self.editor_frame, text="Feature Editor", padding=10)
        self.feature_editor_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        if self.current_feature_idx is not None:
            self._build_feature_editor()
        else:
            ttk.Label(self.feature_editor_frame, text="Select a feature to edit", style="Dim.TLabel").pack(pady=20)
        
        # Preview
        preview_frame = ttk.LabelFrame(self.editor_frame, text="Preview", padding=10)
        preview_frame.pack(fill=tk.X)
        
        self._build_preview(preview_frame)
        
    def _build_feature_editor(self):
        for widget in self.feature_editor_frame.winfo_children():
            widget.destroy()
            
        if self.current_feature_idx is None or not self.current_terrain:
            ttk.Label(self.feature_editor_frame, text="Select a feature to edit", style="Dim.TLabel").pack(pady=20)
            return
            
        features = self.config[self.current_terrain].get("features", [])
        if self.current_feature_idx >= len(features):
            return
            
        feature = features[self.current_feature_idx]
        
        # Name
        row = ttk.Frame(self.feature_editor_frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Name:", width=15).pack(side=tk.LEFT)
        self.feat_name_var = tk.StringVar(value=feature.get("name", ""))
        name_entry = ttk.Entry(row, textvariable=self.feat_name_var, width=25)
        name_entry.pack(side=tk.LEFT)
        name_entry.bind("<KeyRelease>", lambda e: self._update_feature_param("name", self.feat_name_var.get()))
        
        # Character
        row = ttk.Frame(self.feature_editor_frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Character:", width=15).pack(side=tk.LEFT)
        self.feat_char_var = tk.StringVar(value=feature.get("char", "?"))
        char_entry = ttk.Entry(row, textvariable=self.feat_char_var, width=5)
        char_entry.pack(side=tk.LEFT)
        char_entry.bind("<KeyRelease>", lambda e: self._update_feature_param("char", self.feat_char_var.get()[:1]))
        
        # Color
        row = ttk.Frame(self.feature_editor_frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Color:", width=15).pack(side=tk.LEFT)
        self.feat_color_var = tk.StringVar(value=feature.get("color", "gray"))
        color_combo = ttk.Combobox(row, textvariable=self.feat_color_var, values=AVAILABLE_COLORS, width=12, state="readonly")
        color_combo.pack(side=tk.LEFT)
        color_combo.bind("<<ComboboxSelected>>", lambda e: self._update_feature_param("color", self.feat_color_var.get()))
        
        # Density
        row = ttk.Frame(self.feature_editor_frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Density:", width=15).pack(side=tk.LEFT)
        self.feat_density_var = tk.DoubleVar(value=feature.get("density", 0.1))
        density_slider = ttk.Scale(row, from_=0.0, to=1.0, variable=self.feat_density_var, orient=tk.HORIZONTAL, length=200)
        density_slider.pack(side=tk.LEFT, padx=(0, 10))
        self.density_label = ttk.Label(row, text=f"{self.feat_density_var.get():.2f}", width=6)
        self.density_label.pack(side=tk.LEFT)
        ttk.Label(row, text="(0=rare, 1=everywhere)", style="Dim.TLabel").pack(side=tk.LEFT, padx=(10, 0))
        
        def on_density_change(*args):
            val = round(self.feat_density_var.get(), 2)
            self.density_label.config(text=f"{val:.2f}")
            self._update_feature_param("density", val)
        self.feat_density_var.trace_add("write", on_density_change)
        
        # Cluster
        row = ttk.Frame(self.feature_editor_frame)
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Clusters:", width=15).pack(side=tk.LEFT)
        self.feat_cluster_var = tk.BooleanVar(value=feature.get("cluster", False))
        cluster_check = ttk.Checkbutton(row, text="Enable clustering", variable=self.feat_cluster_var,
                                        command=lambda: self._on_cluster_toggle())
        cluster_check.pack(side=tk.LEFT)
        
        # Cluster size
        self.cluster_size_frame = ttk.Frame(self.feature_editor_frame)
        self.cluster_size_frame.pack(fill=tk.X, pady=4)
        ttk.Label(self.cluster_size_frame, text="Cluster Size:", width=15).pack(side=tk.LEFT)
        self.feat_cluster_size_var = tk.IntVar(value=feature.get("cluster_size", 3))
        cluster_size_spin = ttk.Spinbox(self.cluster_size_frame, from_=1, to=20, textvariable=self.feat_cluster_size_var, width=5)
        cluster_size_spin.pack(side=tk.LEFT)
        cluster_size_spin.bind("<KeyRelease>", lambda e: self._update_feature_param("cluster_size", self.feat_cluster_size_var.get()))
        cluster_size_spin.bind("<<Increment>>", lambda e: self._update_feature_param("cluster_size", self.feat_cluster_size_var.get()))
        cluster_size_spin.bind("<<Decrement>>", lambda e: self._update_feature_param("cluster_size", self.feat_cluster_size_var.get()))
        
        if not self.feat_cluster_var.get():
            self.cluster_size_frame.pack_forget()
            
    def _on_cluster_toggle(self):
        cluster_enabled = self.feat_cluster_var.get()
        self._update_feature_param("cluster", cluster_enabled)
        if cluster_enabled:
            self.cluster_size_frame.pack(fill=tk.X, pady=4)
            self._update_feature_param("cluster_size", self.feat_cluster_size_var.get())
        else:
            self.cluster_size_frame.pack_forget()
            # Remove cluster_size from feature
            if self.current_terrain and self.current_feature_idx is not None:
                features = self.config[self.current_terrain].get("features", [])
                if self.current_feature_idx < len(features):
                    features[self.current_feature_idx].pop("cluster_size", None)
                    
    def _build_preview(self, parent):
        """Build ASCII preview of terrain using RenderFeatures"""
        if not self.current_terrain or self.current_terrain not in self.config:
            return
            
        terrain_data = self.config[self.current_terrain]
        
        preview_text = tk.Text(parent, bg=self.colors["bg_secondary"], fg=self.colors["fg"],
                               font=("Consolas", 10), height=20, width=40, state=tk.NORMAL)
        preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Use RenderFeatures to generate preview
        from render_features import RenderFeatures
        preview_str = RenderFeatures.render_terrain(
            terrain_name=self.current_terrain,
            terrain_def=terrain_data,
            size=35,
            seed=42
        )
        
        preview_text.insert(tk.END, preview_str)
        preview_text.config(state=tk.DISABLED)
        
        # Also print colorized version to console
        RenderFeatures.render_terrain_colored(
            terrain_name=self.current_terrain,
            terrain_def=terrain_data,
            size=35,
            seed=42
        )
        
    def _rename_terrain(self):
        if not self.current_terrain:
            return
        new_name = self.terrain_name_var.get().strip().lower().replace(" ", "_")
        if not new_name:
            return
        if new_name == self.current_terrain:
            return
        if new_name in self.config:
            messagebox.showerror("Error", f"Terrain '{new_name}' already exists!")
            return
        
        self.config[new_name] = self.config.pop(self.current_terrain)
        self.current_terrain = new_name
        self._populate_terrain_list()
        
        for i in range(self.terrain_listbox.size()):
            if self.terrain_listbox.get(i).strip() == new_name:
                self.terrain_listbox.select_set(i)
                break
        self.editor_title_var.set(f"✏️ {new_name}")
        self.status_var.set(f"Renamed to '{new_name}'")
        
    def _update_terrain_param(self, param: str, value):
        if self.current_terrain and self.current_terrain in self.config:
            self.config[self.current_terrain][param] = value
            self.unsaved_changes = True
            self._build_terrain_editor()
            
    def _update_feature_param(self, param: str, value):
        if self.current_terrain and self.current_feature_idx is not None:
            features = self.config[self.current_terrain].get("features", [])
            if self.current_feature_idx < len(features):
                features[self.current_feature_idx][param] = value
                self.unsaved_changes = True
                # Update feature list display
                feat = features[self.current_feature_idx]
                self.feature_listbox.delete(self.current_feature_idx)
                self.feature_listbox.insert(self.current_feature_idx, f"  [{feat['char']}] {feat['name']}")
                self.feature_listbox.select_set(self.current_feature_idx)
                
    def _add_terrain(self):
        # Generate unique name
        base_name = "new_terrain"
        name = base_name
        counter = 1
        while name in self.config:
            name = f"{base_name}_{counter}"
            counter += 1
        
        self.config[name] = {
            "features": [],
            "ground_char": ".",
            "ground_color": "green"
        }
        self._populate_terrain_list()
        
        for i in range(self.terrain_listbox.size()):
            if self.terrain_listbox.get(i).strip() == name:
                self.terrain_listbox.select_set(i)
                self._on_terrain_select(None)
                break
                
    def _delete_terrain(self):
        if not self.current_terrain:
            return
        if messagebox.askyesno("Confirm Delete", f"Delete terrain '{self.current_terrain}'?"):
            del self.config[self.current_terrain]
            self.current_terrain = None
            self.current_feature_idx = None
            self._populate_terrain_list()
            for widget in self.editor_frame.winfo_children():
                widget.destroy()
            self.editor_title_var.set("Select a terrain")
            
    def _add_feature(self):
        if not self.current_terrain:
            messagebox.showwarning("Warning", "Select a terrain first!")
            return
        
        # Create new feature with defaults - user edits in form
        features = self.config[self.current_terrain].get("features", [])
        features.append({
            "char": "?",
            "name": "new_feature",
            "density": 0.1,
            "color": "gray",
            "cluster": False
        })
        self.config[self.current_terrain]["features"] = features
        self._populate_feature_list()
        
        # Select new feature
        self.feature_listbox.select_set(len(features) - 1)
        self.current_feature_idx = len(features) - 1
        self._build_feature_editor()
        
    def _delete_feature(self):
        if not self.current_terrain or self.current_feature_idx is None:
            return
        features = self.config[self.current_terrain].get("features", [])
        if self.current_feature_idx < len(features):
            feat_name = features[self.current_feature_idx].get("name", "feature")
            if messagebox.askyesno("Confirm Delete", f"Delete feature '{feat_name}'?"):
                del features[self.current_feature_idx]
                self.current_feature_idx = None
                self._populate_feature_list()
                self._build_terrain_editor()
                
    def _save_config(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
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
            initialfile="landscape_features_export.json",
            initialdir=os.path.dirname(CONFIG_PATH)
        )
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(self.config, f, indent=2)
                self.status_var.set(f"✅ Exported to {os.path.basename(filepath)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")


def main():
    root = tk.Tk()
    app = FeatureEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
