import os
import shutil
import exifread
from datetime import datetime

# Prompt the user to enter the source folder
source_folder = input("Enter the path to the folder containing unstructured photos/videos: ")

# Prompt the user to enter the destination folder
destination_folder = input("Enter the path to the folder where the organized tree will be created: ")

# Dictionary to keep track of the photo count for each camera on a given day
photo_count = {}

# Count of files that were not moved
files_not_moved = 0

# Recursive function to process files in a directory and its sub-directories
def process_files(directory):
    global files_not_moved

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Check if the file is a photo or video file (you can customize the extensions as per your file types)
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov')):

            # Open the file for reading
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)

            # Extract the capture date from the EXIF metadata
            capture_date = None

            capture_date_tag = 'EXIF DateTimeOriginal' if 'EXIF DateTimeOriginal' in tags else 'EXIF DateTimeDigitized'
            if capture_date_tag in tags:
                capture_date_str = str(tags[capture_date_tag])
                capture_date = datetime.strptime(capture_date_str, '%Y:%m:%d %H:%M:%S')

            # Fallback to modification date if capture date is not available
            if capture_date is None:
                modification_time = os.path.getmtime(file_path)
                capture_date = datetime.fromtimestamp(modification_time)

            # Get the camera model name and brand from the metadata (if available)
            camera_model = str(tags.get('Image Model', 'Unknown'))
            camera_brand = str(tags.get('Image Make', 'Unknown'))

            # Get the city name from the metadata (if available)
            city_name = str(tags.get('Image Software', ''))

            # Generate a new filename based on capture date, camera brand, camera model, city name, and photo count
            file_extension = os.path.splitext(filename)[1]
            new_filename = generate_new_filename(capture_date, camera_brand, camera_model, city_name, file_extension)

            # Extract year and month from the capture date
            year = str(capture_date.year)
            month = str(capture_date.month).zfill(2)  # Zero-padding for single-digit months (e.g., 01, 02)
            day = str(capture_date.day).zfill(2)  # Zero-padding for single-digit days (e.g., 01, 02)

            # Create the destination folder if it doesn't exist
            destination_year_folder = os.path.join(destination_folder, year)
            destination_month_folder = os.path.join(destination_year_folder, month)
            os.makedirs(destination_month_folder, exist_ok=True)

            # Move the file to the new location with the renamed file
            destination_path = os.path.join(destination_month_folder, new_filename)
            shutil.move(file_path, destination_path)

            print(f"Moved {filename} to {destination_path}")

        # Recursively process sub-folders
        elif os.path.isdir(file_path):
            process_files(file_path)

    # Delete empty folders after moving the files
    delete_empty_folders(directory)

# Function to generate the new filename based on capture date, camera brand, camera model, city name, and photo count
def generate_new_filename(capture_date, camera_brand, camera_model, city_name, file_extension):
    # Separate the capture date into year, month, and day
    year = capture_date.strftime('%Y')
    month = capture_date.strftime('%m')
    day = capture_date.strftime('%d')

    # Construct the new filename with the desired format
    new_filename = f"{year}_{month}_{day}_"

    # Add the camera brand to the filename if available
    if camera_brand != 'Unknown':
        new_filename += f"{camera_brand}_"

    # Add the camera model to the filename
    new_filename += f"{camera_model}"

    # Add the city name to the filename if available
    if city_name:
        new_filename += f"_{city_name}"

    # Add the photo count for the camera and capture date
    new_filename += f"_{get_photo_count(camera_model, capture_date)}{file_extension}"

    return new_filename

# Function to get the photo count for a specific camera on a given day
def get_photo_count(camera_model, capture_date):
    global photo_count

    # Check if the camera is already in the dictionary
    if camera_model in photo_count:
        # Check if the capture date is already in the camera's dictionary
        if capture_date.date() in photo_count[camera_model]:
            photo_count[camera_model][capture_date.date()] += 1
        else:
            photo_count[camera_model][capture_date.date()] = 1
    else:
        photo_count[camera_model] = {capture_date.date(): 1}

    # Return the photo count for the camera and capture date
    return str(photo_count[camera_model][capture_date.date()]).zfill(3)

# Function to delete empty folders after moving the files
def delete_empty_folders(directory):
    global files_not_moved

    for root, dirs, files in os.walk(directory, topdown=False):
        for folder in dirs:
            folder_path = os.path.join(root, folder)

            # Check if the folder is empty
            if not os.listdir(folder_path):
                # Delete the empty folder
                os.rmdir(folder_path)
            else:
                files_not_moved += len(os.listdir(folder_path))

# Start processing files in the source folder and its sub-folders
process_files(source_folder)

# Display the count of files that were not moved
print(f"\nNumber of files not moved: {files_not_moved}")
