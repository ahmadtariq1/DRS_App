import cv2
import numpy as np
import json
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import math
import os
from datetime import datetime


class CricketDRSOverlay:
    def __init__(self, video_path, trajectory_data, output_path=None):
        """
        Initialize the Cricket DRS Overlay system

        Args:
            video_path (str): Path to the input video file
            trajectory_data (dict): Dictionary containing trajectory analysis results
            output_path (str, optional): Path for the output video file
        """
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
            "bat": (255, 165, 0),  # Blue
            "out": (0, 165, 255),  # Orange (for "OUT" text)
            "not_out": (0, 255, 0),  # Green
            "text": (255, 255, 255),  # White
            "background": (0, 0, 0),  # Black
        }

        # Load video and get properties
        self.cap = cv2.VideoCapture(self.video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Set common video constants
        self.PITCH_LENGTH_M = 20.12  # meters (length of pitch between creases)
        self.PITCH_WIDTH_M = 3.05  # meters (approx. width of pitch)

        # Calculate meter to pixel scales as in the second file
        self.scale_x_meter_to_pixel = self.width / self.PITCH_LENGTH_M
        self.scale_y_meter_to_pixel = self.height / self.PITCH_WIDTH_M

        # Prepare output video writer
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(self.output_path, self.fourcc, self.fps, (self.width, self.height))

        # Convert trajectory points from real-world to pixel coordinates
        self.trajectory_pixels = self._convert_trajectory_to_pixels()

        print(f"Loaded {len(self.predicted_trajectory)} trajectory points")
        print(f"Converted to {len(self.trajectory_pixels)} pixel coordinates")

    def _convert_trajectory_to_pixels(self):
        """
        Convert trajectory points from real-world coordinates to pixel coordinates

        Returns:
            list: List of (frame_idx, x, y, r) tuples for detected ball positions
        """
        pixel_trajectory = []
        if not self.predicted_trajectory:
            print("Warning: No trajectory data found!")
            return pixel_trajectory

        # Get the time span of trajectory data
        start_time = self.predicted_trajectory[0].get("t", 0)

        # In case there are multiple points with the same timestamp
        # we'll create a mapping of unique timestamps
        unique_timestamps = []
        for point in self.predicted_trajectory:
            t = point.get("t", 0)
            if t not in unique_timestamps:
                unique_timestamps.append(t)

        # Sort timestamps to ensure proper ordering
        unique_timestamps.sort()

        # Calculate total time span
        if len(unique_timestamps) > 1:
            total_time = unique_timestamps[-1] - unique_timestamps[0]
        else:
            # Default if only one timestamp
            total_time = 1.0

        # Map each trajectory point to a frame number
        for i, point in enumerate(self.predicted_trajectory):
            x_m = point.get("x", 0)
            y_m = point.get("y", 0)
            z_m = point.get("z", 0)
            t = point.get("t", 0)

            # Calculate relative position in video
            time_fraction = (t - start_time) / total_time if total_time > 0 else 0.5

            # Map time to frame number, ensuring we cover most of the video
            # but leave space at start and end
            frame_idx = int(max(0, min(self.frame_count - 1,
                                       self.frame_count * 0.2 + time_fraction * self.frame_count * 0.6)))

            # Convert world coordinates to pixel coordinates
            # Here we invert Y as in the second file because image coordinates have y=0 at top
            x_px = int(x_m * self.scale_x_meter_to_pixel)
            y_px = int(self.height - (y_m * self.scale_y_meter_to_pixel))

            # Ball radius based on z coordinate (higher = larger)
            radius = max(3, min(12, int(3 + z_m * 10)))

            pixel_trajectory.append((frame_idx, x_px, y_px, radius))

        # Sort trajectory by frame_idx to ensure proper rendering order
        pixel_trajectory.sort(key=lambda x: x[0])

        return pixel_trajectory

    def _draw_trajectory_on_frame(self, frame, frame_idx):
        """
        Draw the trajectory on a video frame similar to the second file

        Args:
            frame (numpy.ndarray): The video frame
            frame_idx (int): Index of the current frame

        Returns:
            numpy.ndarray: Frame with trajectory overlay
        """
        # Create a copy of the frame to avoid modifying the original
        overlay = frame.copy()

        # Track points to display for this frame
        points_drawn = 0

        # Draw trajectory points up to current frame
        for i, (pos_frame, x, y, r) in enumerate(self.trajectory_pixels):
            if pos_frame <= frame_idx:
                points_drawn += 1

                # Draw the ball position with circle
                cv2.circle(overlay, (x, y), r, self.COLORS["impact"], 2)

                # Draw a dot at the center
                cv2.circle(overlay, (x, y), 2, self.COLORS["trajectory_dot"], -1)

                # Connect with previous point if available
                if i > 0:
                    prev_frame, prev_x, prev_y, _ = self.trajectory_pixels[i - 1]
                    cv2.line(overlay, (prev_x, prev_y), (x, y), self.COLORS["trajectory"], 2)

        # Draw bat coordinates if they exist
        if self.bat_coordinates:
            for i, coord in enumerate(self.bat_coordinates):
                # Convert to pixel coordinates
                x_m, y_m, z_m = coord.get("x", 0), coord.get("y", 0), coord.get("z", 0)
                x_px = int(x_m * self.scale_x_meter_to_pixel)
                y_px = int(self.height - (y_m * self.scale_y_meter_to_pixel))

                # Draw a small rectangle to represent bat
                cv2.rectangle(overlay, (x_px - 5, y_px - 5), (x_px + 5, y_px + 5),
                              self.COLORS["bat"], -1)

        # Draw stump coordinates if they exist
        if self.stump_coordinates:
            for i, coord in enumerate(self.stump_coordinates):
                # Convert to pixel coordinates
                x_m, y_m, z_m = coord.get("x", 0), coord.get("y", 0), coord.get("z", 0)
                x_px = int(x_m * self.scale_x_meter_to_pixel)
                y_px = int(self.height - (y_m * self.scale_y_meter_to_pixel))

                # Draw a small circle to represent stump
                radius = 3
                cv2.circle(overlay, (x_px, y_px), radius, self.COLORS["stumps"], -1)

        # Add frame and time info
        cv2.putText(overlay, f"Frame: {frame_idx}, Time: {frame_idx / self.fps:.2f}s",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["text"], 2)

        # Add trajectory info
        cv2.putText(overlay, f"Tracked points: {points_drawn}/{len(self.trajectory_pixels)}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["text"], 2)

        return overlay

    def _add_decision_graphics(self, frame, frame_idx):
        """
        Add decision graphics and stats to the frame similar to the second file

        Args:
            frame (numpy.ndarray): The video frame
            frame_idx (int): Index of the current frame

        Returns:
            numpy.ndarray: Frame with decision graphics
        """
        # Show decision after certain point in the video
        show_decision = frame_idx > self.frame_count // 4

        if show_decision:
            # Decision text and confidence - positioned in the top right like in second file
            decision_color = self.COLORS["out"] if self.decision == "OUT" else self.COLORS["not_out"]

            cv2.putText(frame, self.decision, (self.width - 150, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, decision_color, 3)

            confidence_text = f"Confidence: {self.confidence * 100:.1f}%"
            cv2.putText(frame, confidence_text, (self.width - 250, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["text"], 2)

            # Add speed if available
            if self.impact_point and "speed" in self.impact_point:
                speed_text = f"Speed: {self.impact_point['speed']:.1f} km/h"
                cv2.putText(frame, speed_text, (self.width - 250, 140),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLORS["text"], 2)

        return frame

    def process_video(self):
        """
        Process the entire video and add overlays
        """
        frame_idx = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            # Apply overlays in sequence
            frame = self._draw_trajectory_on_frame(frame, frame_idx)
            frame = self._add_decision_graphics(frame, frame_idx)

            # Write the frame to output video
            self.out.write(frame)
            frame_idx += 1

            # Show progress
            if frame_idx % 100 == 0:
                print(
                    f"Processed {frame_idx} frames out of {self.frame_count} ({frame_idx / self.frame_count * 100:.1f}%)")

        # Release resources
        self.cap.release()
        self.out.release()
        print(f"Video processing complete. Output saved to: {self.output_path}")
        return self.output_path


def process_from_json_file(video_path, json_path, output_path=None):
    """
    Process video with trajectory data from a JSON file

    Args:
        video_path (str): Path to the input video file
        json_path (str): Path to the JSON file containing trajectory data
        output_path (str, optional): Path for the output video file

    Returns:
        str: Path to the output video file
    """
    # Load trajectory data from JSON file
    with open(json_path, 'r') as f:
        trajectory_data = json.load(f)

    # Print summary of loaded data
    print(f"Loaded JSON data:")
    print(f"- Decision: {trajectory_data.get('label', 'UNKNOWN')}")
    print(f"- Confidence: {trajectory_data.get('confidence', 0.0) * 100:.1f}%")
    print(f"- Trajectory points: {len(trajectory_data.get('predicted_trajectory', []))}")
    print(f"- Bat coordinates: {len(trajectory_data.get('bat_coordinates', []))}")
    print(f"- Stump coordinates: {len(trajectory_data.get('stump_coordinates', []))}")

    # Process the video
    drs = CricketDRSOverlay(video_path, trajectory_data, output_path)
    output_path = drs.process_video()

    return output_path


if __name__ == "__main__":
    process_from_json_file("input_cricket_video.mp4", "trajectory_data.json", "output_drs_video.mp4")