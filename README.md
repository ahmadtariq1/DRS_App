# Group Members

- Mujtaba Ahmed
- Ahmad Abdul Rehman
- Hassaan Raza
- Burhan Bhatti
- Ibrahim Sohail
- M.Fahad

# Stream Analysis and Display Module

Processes trajectory data from ball tracking inputs to render real-time overlays for cricket Decision Review System (DRS).

## Features

- Real-time ball trajectory visualization
- Distinct rendering for actual and predicted paths
- Decision indicators (OUT/NOT OUT) with confidence metrics
- Support for multiple wicket types (LBW, caught)
- Custom graphics support via file path configuration

## Input Schema

Receives trajectory analysis data:

```json
{
  "predicted_path": [
    {"x": 2.0, "y": 0.8, "z": 0.3, "t": 0.1},
    {"x": 1.8, "y": 0.6, "z": 0.2, "t": 0.1}
  ],
  "impact_location": {"x": 1.6, "y": 0.4, "z": 0.1},
  "bounce_point": {"x": 2.2, "y": 1.0, "z": 0.0},
}
```

## Output

Produces video with overlaid graphics showing:
- Color-coded trajectory segments (pre/post-bounce)
- Semi-transparent predicted path
- Impact point markers
- Decision indicators with confidence percentages

## Core Components

- **Interface Layer** - Standardized APIs for module integration
- **Decision Modules** - Separate logic for each wicket type
- **Animation Components** - Modular rendering for different ball phases
- **Coordinate Mapper** - 3D world to 2D video frame conversion
- **Graphics Engine** - Customizable overlay rendering system



