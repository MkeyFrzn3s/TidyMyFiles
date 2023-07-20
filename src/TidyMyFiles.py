import os
import shutil
import exifread
from datetime import datetime

# Prompt the user to enter the source folder
source_folder = input("Enter the path to the folder containing unstructured photos/videos: ")

# Prompt the user to enter the destination folder
destination_folder = input("Enter the path to the folder where the organized tree will be created: ")

# Set to keep track of file hashes
file_hashes = set()

# List to store the reasons why files were not moved
files_not_moved = []

# Recursive function to process files in a directory and its sub-directories
def process_files(directory):
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Check if the file is a photo or video file (you can customize the extensions as per your file types)
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov')):

            # Calculate the hash of the file content
            file_hash = hash_file(file_path)

            # Check if the file is a duplicate based on content
            if file_hash in file_hashes:
                # Remove the duplicate file
                os.remove(file_path)
                print(f"Removed duplicate file: {file_path}")
            else:
                # Add the file hash to the set
                file_hashes.add(file_hash)

                # Continue processing the file
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

                # Determine the destination path and handle duplicate files
                destination_path = os.path.join(destination_month_folder, new_filename)
                if os.path.exists(destination_path):
                    new_filename = resolve_duplicate_filename(destination_month_folder, new_filename)
                    destination_path = os.path.join(destination_month_folder, new_filename)

                # Move the file to the new location with the renamed file
                try:
                    shutil.move(file_path, destination_path)
                    print(f"Moved {filename} to {destination_path}")
                except shutil.Error as e:
                    reason = str(e)
                    files_not_moved.append((filename, reason))

        # Recursively process sub-folders
        elif os.path.isdir(file_path):
            process_files(file_path)

# Function to generate the new filename based on capture date, camera brand, camera model, city name, and photo count
def generate_new_filename(capture_date, camera_brand, camera_model, city_name, file_extension):
    # ...

# Function to calculate the hash of a file
def hash_file(file_path):
    BLOCK_SIZE = 65536
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(BLOCK_SIZE), b''):
            hasher.update(block)
    return hasher.hexdigest()

# Function to resolve duplicate filenames by appending a suffix
def resolve_duplicate_filename(destination_folder, filename):
    file_name, file_extension = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join(destination_folder, filename)):
        new_filename = f"{file_name}_{counter}{file_extension}"
        counter += 1
    return new_filename

# Start processing files in the source folder and its sub-folders
process_files(source_folder)

# Print the report of files not moved with their reasons
print("Files not moved:")
for file_name, reason in files_not_moved:
    print(f"{file_name}: {reason}")

# Display the count of files that were not moved
print(f"\nNumber of files not moved: {len(files_not_moved)}")
