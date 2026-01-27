# Embodied Spatial Perception: Body Informs Mind

## Problem
Alice's spatial beliefs (`current_region`, `ntpp`) are **manually hardcoded** in ASL, disconnected from her physical body. This causes:

1. **Belief/body divergence on teleport**: `vesna.teleport(110.3, 4.2, 34.6)` places the body at coordinates, but `start_region(common)` sets beliefs to "common" regardless of actual location.
2. **Belief/body divergence on stuck movement**: `hop_to` updates beliefs even when the agent physically gets stuck (timeout). Mind says "corridor", body is still in "common".
3. **Belief/body divergence on episode reset**: `reset_position` only resets beliefs, not the body. Episode 1 starts with beliefs at `start_region` while body is at the goal from episode 0.

Meanwhile, **Godot already detects the truth** — `_on_area_body_entered` fires every time Alice enters a region's Area3D — but this information is printed to console and thrown away.

## Solution
Make the body inform the mind. When Godot detects Alice entering a region, send a WebSocket signal to Jason. Jason receives it as a perception and updates beliefs automatically.

**Signal flow:**
```
Alice's body enters Area3D (Godot physics)
  → vesna.gd sends: {type: "signal", data: {type: "region_entered", status: "corridor", reason: "body_entered"}}
  → VesnaAgent.handleEvent() creates literal: region_entered(corridor, body_entered)
  → Jason receives +region_entered(corridor, body_entered) perception
  → symbolic_execution_engine.asl trigger updates current_region + ntpp beliefs
```

**Key insight**: `VesnaAgent.handleEvent()` already handles this pattern — NO Java changes needed.

## Files to Modify (3 files)

### 1. `env/office/scripts/vesna.gd` — Send region_entered signal
- Add `signal_region_entered(region_name)` function:
```gdscript
func signal_region_entered(region_name: String) -> void:
    var log: Dictionary = {}
    log['sender'] = 'body'
    log['receiver'] = 'vesna'
    log['type'] = 'signal'
    var msg: Dictionary = {}
    msg['type'] = 'region_entered'
    msg['status'] = region_name
    msg['reason'] = 'body_entered'
    log['data'] = msg
    ws.send_text(JSON.stringify(log))
```

- Separate region vs door callbacks in `_ready()`:
  - Regions: call `signal_region_entered(region_name)` on every body entry
  - Doors: no region_entered signal (doors are not regions)

- Update `_on_area_body_entered` → split into `_on_region_body_entered` and `_on_door_body_entered`:
```gdscript
func _on_region_body_entered(region_name, body):
    if body.name == self.name:
        print("Agent ", self.name, " entered region ", region_name)
        signal_region_entered(region_name)
        if region_name == target_movement:
            signal_end_movement()
            navigator.set_target_position(global_position)

func _on_door_body_entered(door_name, body):
    if body.name == self.name:
        print("Agent ", self.name, " entered door ", door_name)
        if door_name == target_movement:
            signal_end_movement()
            navigator.set_target_position(global_position)
```

- Update teleport functions to send `signal_region_entered` before `signal_end_movement`:
  - `teleport_to_region(target)`: call `signal_region_entered(target)` (we know the region)
  - `teleport_to_position(x,y,z)`: find nearest region node, call `signal_region_entered(nearest)`

### 2. `mind/src/agt/symbolic_execution_engine.asl` — Auto-update beliefs from perception
- Add `+region_entered` trigger:
```prolog
+region_entered(Region, _)
    :   .my_name(Me)
    <-  -current_region(_);
        +current_region(Region);
        -ntpp(Me, _);
        +ntpp(Me, Region).
```

- Remove manual belief updates from `+!hop_to`:
```prolog
// REMOVE these 4 lines from hop_to:
//  -current_region(_);
//  +current_region(TargetRegion);
//  -ntpp(Me, _);
//  +ntpp(Me, TargetRegion).
```
  Beliefs are now updated automatically by the `+region_entered` trigger.

### 3. `mind/src/agt/alice_rl.asl` — Remove manual belief management
- `+!start`: remove manual `+ntpp` and `+current_region`. After teleport + `.wait`, query `?current_region(Region)` to get the detected region:
```prolog
+!start
    :   .my_name(Me) & start_region(StartRegion) & goal_region(GoalRegion)
    <-  vesna.teleport(StartRegion);
        .wait({+movement(completed, destination_reached)});
        // Beliefs auto-set by +region_entered trigger
        ?current_region(ActualRegion);
        .print("Location: ", ActualRegion);
        .print("Goal: ", GoalRegion);
        !run_episodes.
```

- `+!reset_position`: teleport physically instead of just resetting beliefs:
```prolog
+!reset_position
    :   start_region(StartRegion)
    <-  vesna.teleport(StartRegion);
        .wait({+movement(completed, destination_reached)}).
        // Beliefs auto-set by +region_entered trigger
```

## No Changes Needed
- `mind/src/agt/vesna/VesnaAgent.java` — `handleEvent()` already creates the right literal
- `mind/python/dqn_server.py` — unchanged (already updated for 22-dim)
- `mind/src/agt/rl/select_action.java` — domain-agnostic, unchanged
- `mind/src/agt/vesna/via/teleport.java` — unchanged (sends teleport message to Godot)

## Verification
```bash
./start_all.sh
# Jason console should show:
#   Teleported alice to region common at (x, y, z)       ← Godot
#   Agent alice entered region common                     ← Godot
#   Location: common                                     ← Jason (from perception!)
#   Goal: outside
#   Step 0: at common (goal: outside)
#   -> RL selected: corridor
#   Agent alice entered region corridor                   ← Godot
#   Step 1: at corridor (goal: outside)
#   -> RL selected: open_office
#   ...
```

Test coordinate teleport by editing `+!start`:
```prolog
vesna.teleport(110.3, 4.2, 34.6);
// Alice lands, Godot detects region, Jason gets belief automatically
```
