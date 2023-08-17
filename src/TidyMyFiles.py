#1 Import Statements ------------------------------

import os
import shutil
import exifread
import piexif
import hashlib
import string
import cv2
from datetime import datetime
from opencage.geocoder import OpenCageGeocode

#2 Constants and Global Variables -----------------

# Prompt the user to enter the source folder
source_folder = input("Enter the path to the folder containing unstructured photos/videos: ")
# source_folder = "xyz" # set a fixed source folder if convenient

# Prompt the user to enter the destination folder
destination_folder = input("Enter the path to the folder where the organized tree will be created: ")
# destination_folder = "xyz" # set a fixed destination folder if convenient

# Dictionary to keep track of the photo count for each camera on a given day
photo_count = {}

# Initialize files_not_moved as an empty list
files_not_moved = []

# Count of files that were not moved
files_not_moved_count = 0

# Create a dictionary of file hashes that will be used to handle file duplications
file_hashes = {}

# OpenCage Geocoder API key
opencage_api_key = input("Enter your OpenCage API Key. Or visit https://opencagedata.com/")
# opencage_api_key = 'xyz' # set a fixed opencage API if convinient

# Create a dictionary to store city names for non-JPEG/TIFF files
city_names_temp = {}

#3 Function Definitions ------------------------------

# Recursive function to process files in a directory and its sub-directories
def process_files(directory):
    global files_not_moved_count
    global files_not_moved

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Check if the file is a photo or video file (you can customize the extensions as per your file types)
        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4', '.avi', '.mov','.tiff', '.tif')):

            # Calculate the hash of the file content
            file_hash = hash_file(file_path)

            # Check if the file is a duplicate based on content
            if file_hash in file_hashes:
                # Remove the duplicate file
                try:
                    os.remove(file_path)
                    print(f"Removed duplicate file: {file_path}")
                    # Log the deleted file in the files_not_moved list
                    files_not_moved.append((filename, "Duplicate - Removed"))
                except FileNotFoundError:
                    # If the file was already deleted (e.g., by a previous iteration), just continue to the next file
                    pass                
            else:
                # Add the file to the dictionary with its hash as the key
                if file_hash in file_hashes:
                    file_hashes[file_hash].append(file_path)
                else:
                    file_hashes[file_hash] = [file_path]
                
                # Assess image quality and remove low-quality images
                if filename.lower().endswith(('.jpg', '.jpeg', '.tiff', '.tif')):                                                      
                    if is_low_quality_image(file_path):
                        try:
                            reason = "Low Quality"
                            files_not_moved.append((filename, reason))
                            files_not_moved_count += 1    
                            continue  # Skip further processing for this image
                        except FileNotFoundError:
                            pass

                # Read EXIF data using either piexif or exifread
                if filename.lower().endswith(('.jpg', '.jpeg', '.tiff', '.tif')):
                    exif_dict = piexif.load(file_path)
                else:                    
                    with open(file_path, 'rb') as f:
                        tags = exifread.process_file(f)

                # Extract the capture date from the EXIF metadata with either piexif or exifread
                if filename.lower().endswith(('.jpg', '.jpeg', '.tiff', '.tif')):
                    capture_date_tag = '0th' if '0th' in exif_dict else 'Exif'
                    if capture_date_tag in exif_dict:
                        capture_date_str = exif_dict[capture_date_tag].get(piexif.ExifIFD.DateTimeOriginal, b'').decode('utf-8')
                        if capture_date_str:
                            capture_date = datetime.strptime(capture_date_str, '%Y:%m:%d %H:%M:%S')
                        else:
                            capture_date = None
                    else:
                        capture_date = None
                else:
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
                if filename.lower().endswith(('.jpg', '.jpeg', '.tiff', '.tif')):
                    if '0th' in exif_dict:
                        camera_model = exif_dict['0th'].get(piexif.ImageIFD.Model, b'').decode('utf-8')
                        camera_brand = exif_dict['0th'].get(piexif.ImageIFD.Make, b'').decode('utf-8')
                    else:
                        camera_model = 'Unknown'
                        camera_brand = 'Unknown'
                else:
                    # Get the camera model name and brand from the metadata (if available)
                    camera_model = str(tags.get('Image Model', 'Unknown'))
                    camera_brand = str(tags.get('Image Make', 'Unknown'))

                # Get GPS coordinates from the image
                lat, lon = get_gps_coordinates(file_path)

                if lat is not None and lon is not None:
                    # Reverse geocode the coordinates to get the city name
                    city_name = reverse_geocode(lat, lon)

                    if city_name:
                        # Write the city name to the XMP metadata for JPEG files
                        if filename.lower().endswith(('.jpg', '.jpeg','.tiff', '.tif')):
                            write_city_to_metadata(file_path, city_name)
                            print(f"City name '{city_name}' added to XMP metadata.")
                        else:
                            # For non-JPEG files, store city names in the temporary dictionary
                            write_city_to_temp(file_path, city_name)
                            print(f"City name '{city_name}' added to temporary dictionary.")
                    else:
                        print("City name not found.")
                        city_name = None
                else:
                    print("GPS coordinates not found in the image metadata.")
                    city_name = None

                # Generate a new filename based on capture date, camera brand, camera model, city name, and photo count
                file_extension = os.path.splitext(filename)[1]
                new_filename = generate_new_filename(capture_date, camera_brand, camera_model, city_name, file_extension)
                # Remove any invalid characters from the new filename
                valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
                new_filename = ''.join(c for c in new_filename if c in valid_chars)

                # Extract year and month from the capture date
                year = str(capture_date.year)
                month = str(capture_date.month).zfill(2)  # Zero-padding for single-digit months (e.g., 01, 02)
                day = str(capture_date.day).zfill(2)  # Zero-padding for single-digit days (e.g., 01, 02)

                # Create the destination folder if it doesn't exist
                destination_year_folder = os.path.join(destination_folder, year)
                destination_month_folder = os.path.join(destination_year_folder, month)
                os.makedirs(destination_month_folder, exist_ok=True)

                # Determine the destination path and handle duplication of file names at the destination folder
                destination_path = os.path.join(destination_month_folder, new_filename)
                if os.path.exists(destination_path):
                    new_filename = resolve_duplicate_filename(destination_month_folder, new_filename)
                    destination_path = os.path.join(destination_month_folder, new_filename)
                
                # Skip if the destination path is invalid
                if '\x00' in destination_path:
                    print(f"Skipping file '{filename}' due to an invalid destination path.")
                    continue

                # Move the file to the new location with the renamed file, or count and log as not moved
                try:
                    shutil.move(file_path, destination_path)
                    print(f"Moved {filename} to {destination_path}")
                except shutil.Error as e:
                        reason = str(e)
                        files_not_moved.append((filename, reason))
                        files_not_moved_count += 1
          
        # If path is a folder, recursively process sub-folders. If the file doesn't have the specified extensions, log and count it as not moved.
        else:
            if os.path.isdir(file_path):
                process_files(file_path)
            else:
                reason = "Not a media file-extension"
                files_not_moved.append((filename, reason))
                files_not_moved_count += 1            
    
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

    # Remove any invalid characters from the filename
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    new_filename = ''.join(c for c in new_filename if c in valid_chars)
    
    return new_filename

# Function to get GPS coordinates from the metadata of the file
def get_gps_coordinates(image_path):
    if image_path.lower().endswith(('.jpg', '.jpeg', '.tiff', '.tif')):
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            latitude_ref = tags.get('GPS GPSLatitudeRef')
            latitude = tags.get('GPS GPSLatitude')
            longitude_ref = tags.get('GPS GPSLongitudeRef')
            longitude = tags.get('GPS GPSLongitude')

            if latitude and longitude and latitude_ref and longitude_ref:
                lat_value = [float(x.num) / float(x.den) for x in latitude.values]
                lon_value = [float(x.num) / float(x.den) for x in longitude.values]

                lat = lat_value[0] + lat_value[1] / 60 + lat_value[2] / 3600
                lon = lon_value[0] + lon_value[1] / 60 + lon_value[2] / 3600

                return lat, lon
    return None, None

# Function to get city name based on lat and lon data from GPS
def reverse_geocode(lat, lon):
    geocoder = OpenCageGeocode(opencage_api_key)
    results = geocoder.reverse_geocode(lat, lon, language='en')
    
    if results and len(results) > 0:
        components = results[0].get('components', {})
        city_name = components.get('city', None)
        if city_name:
            return city_name

    return None

# Function to write the cityname to the metadata of the file (XMP City)
def write_city_to_metadata(image_path, city_name):
    # Load the EXIF data using piexif
    exif_dict = piexif.load(image_path)
    
    # Convert city_name to bytes for proper XMP encoding
    city_name_bytes = city_name.encode('utf-8')
    # Check if XMP data exists in the EXIF dictionary
    
    if exif_dict.get('Exif', {}).get(piexif.ExifIFD.UserComment):
        # XMP data exists, update the city name
        xmp_bytes = exif_dict['Exif'][piexif.ExifIFD.UserComment] + city_name_bytes
    else:
        # XMP data doesn't exist, create new XMP metadata
        xmp_bytes = city_name_bytes
    
    # Update the EXIF data with the new/updated XMP metadata
    exif_dict['Exif'][piexif.ExifIFD.UserComment] = xmp_bytes
    
    # Save the updated EXIF data back to the image
    piexif.insert(piexif.dump(exif_dict), image_path)

# Function to store the Metadata for the City name if the file type does not support XMP
def write_city_to_temp(image_path, city_name):
    city_names_temp[image_path] = city_name

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
    for root, dirs, files in os.walk(directory, topdown=False):
        for folder in dirs:
            folder_path = os.path.join(root, folder)

            # Check if the folder is empty
            if not os.listdir(folder_path):
                # Delete the empty folder
                os.rmdir(folder_path)

# Function to resolve duplicate filenames by appending a suffix
def resolve_duplicate_filename(destination_folder, filename):
    file_name, file_extension = os.path.splitext(filename)
    counter = 1

    # Check if there are existing files with similar naming pattern
    existing_files = [f for f in os.listdir(destination_folder) if f.startswith(f"{file_name}_")]
    existing_counters = [int(f.split('_')[-1].split('.')[0]) for f in existing_files if f.split('_')[-1].split('.')[0].isdigit()]

    if existing_counters:
        # If there are existing counters, find the highest one and start the counter from the next number
        counter = max(existing_counters) + 1

    while os.path.exists(os.path.join(destination_folder, f"{file_name}_{counter}{file_extension}")):
        counter += 1

    new_filename = f"{file_name}_{counter}{file_extension}"
    return new_filename

# Function to calculate the hash of a file
def hash_file(file_to_hash):
    BLOCK_SIZE = 65536
    hasher = hashlib.sha256()
    with open(file_to_hash, 'rb') as f:
        for block in iter(lambda: f.read(BLOCK_SIZE), b''):
            hasher.update(block)
    return hasher.hexdigest()

# Function to caputure low quality files
def is_low_quality_image(image_path):
    # Load the image using OpenCV
    image = cv2.imread(image_path)

    # Assess image brightness (lower value indicates darker image)
    brightness = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).mean()

    # Assess image sharpness (lower value indicates blurrier image)
    # sharpness = cv2.Laplacian(image, cv2.CV_64F).var()

    # Assess image stability (higher value indicates more stable image)
    # stability = cv2.Laplacian(image, cv2.CV_64F).mean()

    # You can define specific thresholds for brightness, sharpness, and stability
    brightness_threshold = 25  # Adjust this value according to your preference
    # sharpness_threshold = 50  # Adjust this value according to your preference
    # stability_threshold = 20  # Adjust this value according to your preference

    # Return True if the image is considered low quality based on the thresholds
    return brightness < brightness_threshold # or sharpness < sharpness_threshold

#4 Script Execution ------------------------------

# Start processing files in the source folder and its sub-folders
process_files(source_folder)

# Delete empty folders after moving the files
delete_empty_folders(source_folder)

# After moving files, remove the temporary dictionary for city names
def delete_temp_data():
    global city_names_temp
    city_names_temp = {}

# Print the list of files that were not moved and the reasons for the failure
print("Files that were not moved:")
for filename, reason in files_not_moved:
    print(f"File: {filename}, Reason: {reason}")

# Print the total count of files that were not moved
print(f"Total files not moved: {files_not_moved_count}")

# The End!!!