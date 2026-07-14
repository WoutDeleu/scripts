import os

def change_extension(directory, current_ext, new_ext):
    """
    Change the extensions of files in the given directory.
    """
    # Check if the directory exists
    if not os.path.isdir(directory):
        print("Directory doesn't exist.")
        return

    # Iterate through all files in the directory
    for filename in os.listdir(directory):
        # Check if the file has the current extension
        if filename.endswith(current_ext):
            # Generate the new filename with the new extension
            new_filename = os.path.splitext(filename)[0] + new_ext
            # Rename the file
            os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))
            print(f"Changed {filename} to {new_filename}")

def main():
    print("Welcome to the File Extension Changer!")
    print("This script helps you to change the extensions of files in a directory.")
    
    # Prompt user for the directory
    directory = input("Enter the directory path where you want to work: ")

    # Prompt user for the current extension and new extension
    current_ext = input("Enter the current extension to change (e.g., '.txt'): ")
    new_ext = input("Enter the new extension (including the dot, e.g., '.docx'): ")

    # Call function to change extensions
    change_extension(directory, current_ext, new_ext)

if __name__ == "__main__":
    main()
