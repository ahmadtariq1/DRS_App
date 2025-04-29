# Cricket Decision Review System (DRS)

A robust application for cricket Decision Review System (DRS) that processes video footage and overlays ball trajectory and decision data in real-time.

## Features

- Real-time ball trajectory tracking and visualization
- Decision indicators (OUT/NOT OUT) with confidence metrics
- Support for multiple wicket types (LBW, caught, run-out)
- 3D to 2D coordinate mapping for accurate overlay positioning
- Modular animation components for different ball trajectory phases
- Custom graphics support via file path configuration
- High-performance rendering (≤200ms latency, ≥30fps)

## System Requirements

- Python 3.8+
- OpenCV
- NumPy
- Matplotlib
- JSON

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/drs-app.git
   cd drs-app
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run basic overlay example:
   ```bash
   python -m drs.main input_cricket_video.mp4 trajectory_data.json output_drs_video.mp4
   ```

## Module Structure

- `overlay_module.py` - Core rendering and trajectory visualization
- `decision_modules/` - Wicket-specific decision logic (LBW, caught, run-out)
- `animation/` - Animation components for different ball phases
- `utils/` - Coordinate mapping and utility functions
- `calibration/` - Camera calibration tools

## Configuration

Sample trajectory data format:
```json
{
  "label": "OUT",
  "confidence": 0.97,
  "impact_point": { "x": 7.77, "y": 2.16, "z": 0.38, "speed": 125.6 },
  "predicted_trajectory": [
    { "x": 5.44, "y": 1.63, "z": 0.5, "t": 0.68 },
    ...
  ]
}
```

## Integration

The system provides interfaces for integration with video feeds and analysis modules. See `docs/integration.md` for details on connecting with other cricket analysis systems.

## Development

Contributors should follow the development workflow described in `CONTRIBUTING.md`. Each module has specific test cases located in the `tests/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.