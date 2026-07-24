# Route Selector Kit v01

Reusable art assets for the active-command route-selection overlay.

- `command_header_frame`: top command context frame.
- `command_point_badge`: blank badge for dynamic command-point cost.
- `target_mode_badge`: blank badge for a dynamic target-mode label.
- `lane_panel_base`: reusable lane container. Instantiate once per top, middle, or bottom lane.
- `lane_panel_selected_outline`: overlay for the selected lane.
- `lane_panel_disabled_wash`: overlay for a lane without a legal target.
- `squad_row_bg`: repeat up to three times inside one lane.
- `squad_portrait_frame`, `troop_chip_frame`, `hp_bar_track`, `hp_bar_fill_neutral`: squad-row components.
- `final_target_reticle`, `final_target_ribbon`: automatic-lock feedback.
- `target_mode_auto_lock_icon`, `target_mode_lane_all_icon`: target-mode icons.
- `troop_icon_melee`, `troop_icon_ranged`: current troop-type icons.
- `lane_connector_triplet`, `lane_invalid_reason_strip`, `release_hint_divider`: supporting layout elements.

All text, values, portraits, troop counts, and gameplay state are rendered by the game. Final transparent PNGs are in `transparent/`; `source/` contains the approved chroma-key source sheets.
