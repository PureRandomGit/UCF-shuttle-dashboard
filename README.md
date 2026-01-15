# Dashboard and backend for UCF Transloc Shuttles
# Install
1. Add bus.py within the config directory
2. Add to configuration.yaml
```
command_line:
  - sensor:
      name: "UCF Bus Tracker"
      unique_id: ucf_bus_tracker_main
      scan_interval: 60
      command: "python3 /config/bus.py"
      value_template: "{{ value_json.next_minutes if value_json.next_minutes is not none else 'Unknown' }}"
      json_attributes:
        - stops
        - stop
        - error
```
3. Restart Home Assistant

# Dashboard Widgets
## Markdown Card

## Mushroom Template Card
