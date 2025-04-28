import cv2
import numpy as np
import json
import logging
import os
from datetime import datetime

# Colab-specific import
try:
    from google.colab.patches import cv2_imshow
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

class CricketDRSOverlay:
    def __init__(self, video_path, trajectory_data, output_path=None, pitch_bbox=None, config=None, codec='mp4v'):
        """
        Initialize the Cricket DRS Overlay system

        Args:
            video_path (str): Path to the input video file
            trajectory_data (dict): Dictionary containing trajectory analysis results
            output_path (str, optional): Path for the output video file
            pitch_bbox (tuple, optional): (x_min, y_min, x_max, y_max) for pitch in video
            config (dict, optional): Configuration for rendering
            codec (str): Video codec (default: 'mp4v')
        """
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.video_path = video_path
        self.trajectory_data = trajectory_data

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_path = f"drs_overlay_{timestamp}.mp4"
        else:
            self.output_path = output_path

        # Extract important data
        self.decision = trajectory_data.get("label", "UNKNOWN")
        self.confidence = trajectory_data.get("confidence", 0.0)
        self.predicted_trajectory = trajectory_data.get("predicted_trajectory", [])
        self.impact_point = trajectory_data.get("impact_point", {})
        self.bat_coordinates = trajectory_data.get("bat_coordinates", [])
        self.stump_coordinates = trajectory_data.get("stump_coordinates", [])

        # Colors (BGR format for OpenCV)
        self.COLORS = {
            "trajectory": (0, 255, 0),  # Green
            "trajectory_dot": (0, 255, 255),  # Yellow
            "impact": (0, 0, 255),  # Red
            "stumps": (255, 255, 255),  # White
            "bat": (255, 165, 0),  # Orange
            "out": (0, 165, 255),  # Orange (for "OUT" text)
            "not_out": (0, 255, 0),  # Green
            "text": (255, 255, 255),  # White
            "background": (0, 0, 0),  # Black
        }

        # Configuration
        default_config = {
            "trajectory_frame_start": 0.2,
            "trajectory_frame_duration": 0.6,
            "decision_text_pos": (0.8, 0.05),
            "confidence_text_pos": (0.75, 0.08),
            "speed_text_pos": (0.75, 0.1),
            "text_scale": 1.0,
            "decision_frame_fraction": 0.25,
            "slow_factor": 2.0,  # Slow motion: 2.0 means 1/2 speed
            "preview_frequency": 10  # Show every 10th frame in preview
        }
        self.config = {**default_config, **(config or {})}

        # Load video and get properties
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Adjust FPS for slow motion
        self.output_fps = self.fps / self.config["slow_factor"]

        # Set common video constants
        self.PITCH_LENGTH_M = 20.12  # meters
        self.PITCH_WIDTH_M = 3.05  # meters

        # Calculate meter to pixel scales
        if pitch_bbox:
            pitch_width_px = pitch_bbox[2] - pitch_bbox[0]
            pitch_height_px = pitch_bbox[3] - pitch_bbox[1]
            self.scale_x_meter_to_pixel = pitch_width_px / self.PITCH_LENGTH_M
            self.scale_y_meter_to_pixel = pitch_height_px / self.PITCH_WIDTH_M
            self.offset_x = pitch_bbox[0]
            self.offset_y = pitch_bbox[1]
        else:
            self.scale_x_meter_to_pixel = self.width / self.PITCH_LENGTH_M
            self.scale_y_meter_to_pixel = self.height / self.PITCH_WIDTH_M
            self.offset_x = 0
            self.offset_y = 0

        # Prepare output video writer
        self.fourcc = cv2.VideoWriter_fourcc(*codec)
        self.out = cv2.VideoWriter(self.output_path, self.fourcc, self.output_fps, (self.width, self.height))
        if not self.out.isOpened():
            self.logger.warning(f"Codec {codec} failed. Trying 'H264'...")
            self.fourcc = cv2.VideoWriter_fourcc(*'H264')
            self.out = cv2.VideoWriter(self.output_path, self.fourcc, self.output_fps, (self.width, self.height))
            if not self.out.isOpened():
                raise RuntimeError("Failed to initialize video writer with any codec")

        # Precompute pixel coordinates
        self.trajectory_pixels = self._convert_trajectory_to_pixels()
        self.bat_pixels = [(int(coord.get("x", 0) * self.scale_x_meter_to_pixel + self.offset_x),
                            int(self.height - (coord.get("y", 0) * self.scale_y_meter_to_pixel) + self.offset_y))
                           for coord in self.bat_coordinates]
        self.stump_pixels = [(int(coord.get("x", 0) * self.scale_x_meter_to_pixel + self.offset_x),
                              int(self.height - (coord.get("y", 0) * self.scale_y_meter_to_pixel) + self.offset_y))
                             for coord in self.stump_coordinates]

        self.logger.info(f"Loaded {len(self.predicted_trajectory)} trajectory points")
        self.logger.info(f"Converted to {len(self.trajectory_pixels)} pixel coordinates")
        self.logger.info(f"Input FPS: {self.fps}, Output FPS: {self.output_fps}")

    def _convert_trajectory_to_pixels(self):
        """
        Convert trajectory points to pixel coordinates with interpolation
        """
        pixel_trajectory = []
        if not self.predicted_trajectory:
            self.logger.warning("No trajectory data found!")
            return pixel_trajectory

        start_time = self.predicted_trajectory[0].get("t", 0)
        end_time = self.predicted_trajectory[-1].get("t", 0)
        total_time = end_time - start_time if end_time > start_time else 1.0

        # Interpolate trajectory for smoothness
        interpolated_points = []
        for i in range(len(self.predicted_trajectory) - 1):
            p1 = self.predicted_trajectory[i]
            p2 = self.predicted_trajectory[i + 1]
            t1, t2 = p1.get("t", 0), p2.get("t", 0)
            steps = max(1, int((t2 - t1) * self.fps * 10))
            for j in range(steps + 1):
                frac = j / steps
                x = p1["x"] + (p2["x"] - p1["x"]) * frac
                y = p1["y"] + (p2["y"] - p1["y"]) * frac
                z = p1["z"] + (p2["z"] - p1["z"]) * frac
                t = t1 + (t2 - t1) * frac
                interpolated_points.append({"x": x, "y": y, "z": z, "t": t})

        for point in interpolated_points:
            x_m = point.get("x", 0)
            y_m = point.get("y", 0)
            z_m = point.get("z", 0)
            t = point.get("t", 0)
            time_fraction = (t - start_time) / total_time if total_time > 0 else 0.5
            frame_idx = int(max(0, min(self.frame_count - 1,
                                       self.frame_count * self.config["trajectory_frame_start"] +
                                       time_fraction * self.frame_count * self.config["trajectory_frame_duration"])))
            x_px = int(x_m * self.scale_x_meter_to_pixel + self.offset_x)
            y_px = int(self.height - (y_m * self.scale_y_meter_to_pixel) + self.offset_y)
            radius = max(3, min(12, int(3 + z_m * 10)))
            pixel_trajectory.append((frame_idx, x_px, y_px, radius))

        pixel_trajectory.sort(key=lambda x: x[0])
        return pixel_trajectory

    def _draw_trajectory_on_frame(self, frame, frame_idx):
        """
        Draw trajectory, bat, and stumps on the frame
        """
        overlay = frame.copy()
        points_drawn = 0

        for i, (pos_frame, x, y, r) in enumerate(self.trajectory_pixels):
            if pos_frame <= frame_idx:
                points_drawn += 1
                cv2.circle(overlay, (x, y), r, self.COLORS["impact"], 2)
                cv2.circle(overlay, (x, y), 2, self.COLORS["trajectory_dot"], -1)
                if i > 0:
                    _, prev_x, prev_y, _ = self.trajectory_pixels[i - 1]
                    cv2.line(overlay, (prev_x, prev_y), (x, y), self.COLORS["trajectory"], 2)

        if len(self.bat_pixels) >= 2:
            for i in range(len(self.bat_pixels) - 1):
                pt1 = self.bat_pixels[i]
                pt2 = self.bat_pixels[i + 1]
                cv2.line(overlay, pt1, pt2, self.COLORS["bat"], 3)
        elif self.bat_pixels:
            for x_px, y_px in self.bat_pixels:
                cv2.rectangle(overlay, (x_px - 5, y_px - 5), (x_px + 5, y_px + 5), self.COLORS["bat"], -1)

        for x_px, y_px in self.stump_pixels:
            cv2.circle(overlay, (x_px, y_px), 3, self.COLORS["stumps"], -1)

        cv2.putText(overlay, f"Frame: {frame_idx}, Time: {frame_idx / self.fps:.2f}s",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["text"], 2)
        cv2.putText(overlay, f"Tracked points: {points_drawn}/{len(self.trajectory_pixels)}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["text"], 2)
        return overlay

    def _add_decision_graphics(self, frame, frame_idx):
        """
        Add decision text and stats to the frame
        """
        show_decision = frame_idx > self.frame_count * self.config["decision_frame_fraction"]
        if show_decision:
            decision_color = self.COLORS["out"] if self.decision == "OUT" else self.COLORS["not_out"]
            text_scale = self.config["text_scale"]
            cv2.putText(frame, self.decision,
                        (int(self.width * self.config["decision_text_pos"][0]), int(self.height * self.config["decision_text_pos"][1])),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5 * text_scale, decision_color, int(3 * text_scale))
            cv2.putText(frame, f"Confidence: {self.confidence * 100:.1f}%",
                        (int(self.width * self.config["confidence_text_pos"][0]), int(self.height * self.config["confidence_text_pos"][1])),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7 * text_scale, self.COLORS["text"], int(2 * text_scale))
            if self.impact_point and "speed" in self.impact_point:
                cv2.putText(frame, f"Speed: {self.impact_point['speed']:.1f} km/h",
                            (int(self.width * self.config["speed_text_pos"][0]), int(self.height * self.config["speed_text_pos"][1])),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7 * text_scale, self.COLORS["text"], int(2 * text_scale))
        return frame

    def process_video(self, preview=False):
        """
        Process the video and add overlays
        """
        frame_idx = 0
        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    break
                frame = self._draw_trajectory_on_frame(frame, frame_idx)
                frame = self._add_decision_graphics(frame, frame_idx)
                self.out.write(frame)
                if preview and (IN_COLAB or preview):
                    if frame_idx % self.config["preview_frequency"] == 0:
                        if IN_COLAB:
                            cv2_imshow(frame)
                        else:
                            cv2.imshow('DRS Overlay', frame)
                            if cv2.waitKey(1) & 0xFF == ord('q'):
                                break
                frame_idx += 1
                if frame_idx % 100 == 0:
                    self.logger.info(f"Processed {frame_idx} frames out of {self.frame_count} ({frame_idx / self.frame_count * 100:.1f}%)")
        except Exception as e:
            self.logger.error(f"Error during video processing: {e}")
        finally:
            self.cap.release()
            self.out.release()
            if preview and not IN_COLAB:
                cv2.destroyAllWindows()
            self.logger.info(f"Video processing complete. Output saved to: {self.output_path}")
        return self.output_path

def process_from_json_file(video_path, json_path, output_path=None, preview=False, pitch_bbox=None, config=None):
    """
    Process video with trajectory data from a JSON file

    Args:
        video_path (str): Path to the input video file
        json_path (str): Path to the JSON file containing trajectory data
        output_path (str, optional): Path for the output video file
        preview (bool): Show preview during processing
        pitch_bbox (tuple, optional): (x_min, y_min, x_max, y_max) for pitch
        config (dict, optional): Configuration for rendering

    Returns:
        str: Path to the output video file
    """
    try:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r') as f:
            trajectory_data = json.load(f)
        
        required_keys = ["label", "confidence", "predicted_trajectory", "impact_point"]
        for key in required_keys:
            if key not in trajectory_data:
                raise ValueError(f"Missing required key in JSON: {key}")
        
        if not trajectory_data["predicted_trajectory"]:
            raise ValueError("Predicted trajectory is empty")
        
        for point in trajectory_data["predicted_trajectory"]:
            if not all(k in point for k in ["x", "y", "z", "t"]):
                raise ValueError(f"Invalid trajectory point format: {point}")
        
        logging.info(f"Loaded JSON data:")
        logging.info(f"- Decision: {trajectory_data.get('label', 'UNKNOWN')}")
        logging.info(f"- Confidence: {trajectory_data.get('confidence', 0.0) * 100:.1f}%")
        logging.info(f"- Trajectory points: {len(trajectory_data.get('predicted_trajectory', []))}")
        logging.info(f"- Bat coordinates: {len(trajectory_data.get('bat_coordinates', []))}")
        logging.info(f"- Stump coordinates: {len(trajectory_data.get('stump_coordinates', []))}")

        drs = CricketDRSOverlay(video_path, trajectory_data, output_path, pitch_bbox, config)
        return drs.process_video(preview=preview)
    except Exception as e:
        logging.error(f"Failed to process: {e}")
        raise

if __name__ == "__main__":
    config = {
        "text_scale": 1.2,
        "decision_text_pos": (0.85, 0.05),
        "slow_factor": 2.0,  # 1/2 speed
        "preview_frequency": 10
    }
    process_from_json_file(
        "input_cricket_video.mp4",
        "trajectory_data.json",
        "output_drs_video.mp4",
        preview=True,
        config=config
    )
