import pandas as pd
import numpy as np
import random
import datetime
import csv


def generate_ball_trajectory(delivery_id, match_id, bowler_id, batsman_id):
    """Generate a realistic cricket ball trajectory"""
    # Starting position (z=0 is bowler's end, z increases toward batsman)
    # x=0 is middle of pitch, negative x is off side for right-handed batsman
    # y is height above ground

    # Number of data points for this trajectory
    num_points = 50

    # Starting time
    start_time = datetime.datetime.now()

    # Lists to store trajectory data
    timestamps = []
    x_coords = []
    y_coords = []
    z_coords = []

    # Initial position (from bowler's hand)
    x_start = random.uniform(-0.5, 0.5)  # Slight variation in horizontal start position
    y_start = 2.0  # Roughly shoulder/head height for release
    z_start = 0.0  # Starting at bowler's end

    # Ending position
    # Determine if ball will hit stumps or be played by batsman
    hitting_stumps = random.random() < 0.3  # 30% chance of hitting stumps

    if hitting_stumps:
        x_end = random.uniform(-0.15, 0.15)  # Within stumps width
        y_end = random.uniform(0.0, 0.7)  # Stump height range
    else:
        x_end = random.uniform(-1.5, 1.5)  # Wider range for batsman playing
        y_end = random.uniform(0.0, 1.2)  # Height range for bat

    z_end = 20.12  # Length of pitch in meters

    # Generate points along trajectory
    for i in range(num_points):
        # Calculate progress (0 to 1)
        progress = i / (num_points - 1)

        # Calculate position at this point
        # Using quadratic path for y to simulate gravity
        z = z_start + (z_end - z_start) * progress

        # Add some swing/seam movement
        swing_factor = random.uniform(-0.5, 0.5)
        swing_point = random.uniform(0.4, 0.7)  # When the ball swings most
        swing_effect = swing_factor * (1 - (progress - swing_point) ** 2) if progress <= swing_point else 0

        # Linear interpolation for x with swing effect
        x = x_start + (x_end - x_start) * progress + swing_effect

        # Quadratic path for y (height) to simulate gravity
        # Ball rises slightly then falls
        peak_height = max(y_start, y_end) + random.uniform(0.1, 0.5)
        if progress < 0.4:  # Rise until 40% of trajectory
            y = y_start + (peak_height - y_start) * (progress / 0.4)
        else:  # Fall after 40%
            y = peak_height - (peak_height - y_end) * ((progress - 0.4) / 0.6)

        # Add some small random variations
        x += random.uniform(-0.03, 0.03)
        y += random.uniform(-0.03, 0.03)
        z += random.uniform(-0.03, 0.03)

        # Calculate timestamp (20ms intervals is 50fps)
        timestamp = start_time + datetime.timedelta(milliseconds=i * 20)

        # Append to lists
        timestamps.append(timestamp)
        x_coords.append(round(x, 3))
        y_coords.append(round(y, 3))
        z_coords.append(round(z, 3))

    # Create a dictionary for this trajectory
    trajectory_data = {
        'delivery_id': [delivery_id] * num_points,
        'match_id': [match_id] * num_points,
        'bowler_id': [bowler_id] * num_points,
        'batsman_id': [batsman_id] * num_points,
        'timestamp': timestamps,
        'x': x_coords,
        'y': y_coords,
        'z': z_coords,
        'frame_number': list(range(1, num_points + 1)),
        'is_hawkeye_prediction': [i > 30 for i in range(1, num_points + 1)]
        # Assuming frames after impact are predictions
    }

    return trajectory_data


def generate_dummy_drs_data(num_deliveries=10, output_file='drs_dummy_data.csv'):
    """Generate dummy DRS data for multiple deliveries and save to CSV"""
    all_data = {
        'delivery_id': [],
        'match_id': [],
        'bowler_id': [],
        'batsman_id': [],
        'timestamp': [],
        'x': [],
        'y': [],
        'z': [],
        'frame_number': [],
        'is_hawkeye_prediction': []
    }

    match_id = 12345  # Sample match ID

    # Generate several trajectories
    for i in range(1, num_deliveries + 1):
        delivery_id = f"D{i}"
        bowler_id = f"B{random.randint(1, 5)}"
        batsman_id = f"BT{random.randint(1, 11)}"

        trajectory = generate_ball_trajectory(delivery_id, match_id, bowler_id, batsman_id)

        # Append to the complete dataset
        for key in all_data.keys():
            all_data[key].extend(trajectory[key])

    # Convert to DataFrame
    df = pd.DataFrame(all_data)

    # Save to CSV
    df.to_csv(output_file, index=False)
    print(f"Generated dummy DRS data with {num_deliveries} deliveries saved to {output_file}")

    # Display a sample of the data
    print("\nSample data (first 5 rows):")
    print(df.head(5))

    # Calculate some statistics for verification
    print("\nData statistics:")
    print(f"Total rows: {len(df)}")
    print(f"Unique deliveries: {df['delivery_id'].nunique()}")
    print(f"X coordinate range: {df['x'].min()} to {df['x'].max()}")
    print(f"Y coordinate range: {df['y'].min()} to {df['y'].max()}")
    print(f"Z coordinate range: {df['z'].min()} to {df['z'].max()}")


# Generate 10 deliveries of dummy data
if __name__ == "__main__":
    generate_dummy_drs_data(num_deliveries=10)