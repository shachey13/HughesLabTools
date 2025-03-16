#!/bin/bash

# Define default Fiji installation directory
FIJI_DIR="/Applications/Fiji.app"

# Parse flags
VERBOSE=false
while getopts "v" opt; do
    case $opt in
        v) VERBOSE=true ;;
        *) echo "Usage: $0 [-v]"; exit 1 ;;
    esac
done

# Function to print debug messages if verbose mode is enabled
debug_print() {
    if [ "$VERBOSE" = true ]; then
        echo "$1"
    fi
}

# Function to validate Fiji installation by checking for expected subdirectories
is_valid_fiji() {
    # Check for multiple Fiji-specific directories and files within the .app bundle
    debug_print "Validating Fiji at path: $1"
    if [ -d "$1/jars" ] && [ -d "$1/plugins" ] && [ -f "$1/Contents/MacOS/ImageJ-macosx" ]; then
        debug_print "Fiji validation passed."
        return 0
    else
        debug_print "Fiji validation failed."
        return 1
    fi
}

# Function to check if Fiji is installed
check_fiji_installed() {
    if ! is_valid_fiji "$FIJI_DIR"; then
        echo "Fiji is not installed in the default location: $FIJI_DIR."
        read -p "Would you like to specify an alternative Fiji installation path? (y/n): " alt_choice
        if [[ "$alt_choice" =~ ^[Yy]$ ]]; then
            read -p "Enter the *full path to the Fiji.app bundle* (e.g., /Applications/Fiji.app): " alt_path

            # Robust Tilde Expansion
            if [[ "$alt_path" == ~* ]]; then
                alt_path=$(echo "$alt_path" | sed "s|^~|$HOME|")
            fi

           if [ ! -d "$alt_path" ]; then
                echo "Error: The specified path '$alt_path' does not exist."
                install_fiji_prompt
                return
            fi
            if is_valid_fiji "$alt_path"; then
                FIJI_DIR="$alt_path"
                echo "Fiji found in $FIJI_DIR. Proceeding with installation..."
            else
                echo "The specified path does not appear to be a valid Fiji installation (missing expected 'jars' and 'plugins' directories, and ImageJ-macosx executable in Contents folder)."
                install_fiji_prompt
            fi
        else
            install_fiji_prompt
        fi
    else
        echo "Fiji is installed in $FIJI_DIR. Proceeding with installation..."
    fi
}

# Function to prompt user for Fiji installation using Homebrew
install_fiji_prompt() {
    read -p "Would you like to install Fiji using Homebrew? (y/n): " choice
    if [[ "$choice" =~ ^[Yy]$ ]]; then
        install_fiji
    else
        echo "Fiji is required to proceed. Please install Fiji and try again."
        exit 1
    fi
}

# Function to install Homebrew
install_homebrew() {
    echo "Homebrew is not installed. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if ! command -v brew &> /dev/null; then
        echo "Homebrew installation failed. Please install Homebrew manually and try again."
        exit 1
    fi
    echo "Homebrew has been successfully installed."
}

# Function to install Fiji using Homebrew
install_fiji() {
    if ! command -v brew &> /dev/null; then
        read -p "Homebrew is not installed. Would you like to install Homebrew? (y/n): " brew_choice
        if [[ "$brew_choice" =~ ^[Yy]$ ]]; then
            install_homebrew
        else
            echo "Homebrew is required to install Fiji automatically. Please install Homebrew and try again."
            exit 1
        fi
    fi

    echo "Installing Fiji using Homebrew..."
    brew install --cask fiji

    if is_valid_fiji "$FIJI_DIR"; then
        echo "Fiji has been successfully installed in $FIJI_DIR."
    else
        echo "Fiji installation failed. Please install Fiji manually and try again."
        exit 1
    fi
}

# Check if Fiji is installed
check_fiji_installed

# Prompt user for installation type
PS3='Please choose installation type: '
options=("Copy Hughes Lab Tools to Fiji (End-user Mode)" "SymLink Hughes Lab Tools to Fiji (Developer Mode)" "Uninstall Hughes Lab Tools" "Quit")

# Create necessary directories in Fiji
mkdir -p "$FIJI_DIR/jars/Lib"
mkdir -p "$FIJI_DIR/scripts/Hughes_Lab_Tools"

# Get the absolute path to the directory containing this script
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
DIR="$(pwd)"
debug_print "Resolved script directory (DIR): $DIR"

# Define source directory (installer is included in the repo)
HUGHESTOOL_DIR="$DIR/src/HughesLabTools"
if [ ! -d "$HUGHESTOOL_DIR" ]; then
    echo "Error: Source directory '$HUGHESTOOL_DIR' does not exist."
    exit 1
fi

# Determine the main script file that defines the menu item
MAIN_SCRIPT="$HUGHESTOOL_DIR/main_.py"
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Warning: main_.py not found in $HUGHESTOOL_DIR. Fiji menu item may not be created."
fi

# Set cp and ln flags based on verbosity (for directories)
CP_FLAGS="-R"
LN_FLAGS="-sfn"
if [ "$VERBOSE" = true ]; then
    CP_FLAGS="-Rv"
    LN_FLAGS="-sfnv"
fi

# Choose install type
select opt in "${options[@]}"
do
    case $opt in
        "Copy Hughes Lab Tools to Fiji (End-user Mode)")
            echo "Copying Hughes Lab Tools to Fiji ..."
            rm -rf "$FIJI_DIR/jars/Lib/HughesLabTools"
            rm -rf "$FIJI_DIR/plugins/Hughes_Lab_Tools"
            debug_print "Copying HughesLabTools from '$HUGHESTOOL_DIR' to '$FIJI_DIR/jars/Lib/HughesLabTools'"
            cp $CP_FLAGS "$HUGHESTOOL_DIR" "$FIJI_DIR/jars/Lib/HughesLabTools"
            if [ -f "$MAIN_SCRIPT" ]; then
                mkdir -p "$FIJI_DIR/scripts/Hughes_Lab_Tools"
                debug_print "Creating symbolic link to main_.py as 'All VMO Tools.py' in $FIJI_DIR/scripts/Hughes_Lab_Tools/"
                ln $LN_FLAGS "$FIJI_DIR/jars/Lib/HughesLabTools/main_.py" "$FIJI_DIR/scripts/Hughes_Lab_Tools/All_VMO_Tools.py"
            fi
            break
            ;;
        "SymLink Hughes Lab Tools to Fiji (Developer Mode)")
            echo "Creating Symbolic Links to Hughes Lab Tools in Fiji ..."
            rm -rf "$FIJI_DIR/jars/Lib/HughesLabTools"
            rm -rf "$FIJI_DIR/plugins/Hughes_Lab_Tools"
            debug_print "Linking HughesLabTools from '$HUGHESTOOL_DIR' to '$FIJI_DIR/jars/Lib/HughesLabTools'"
            ln $LN_FLAGS "$HUGHESTOOL_DIR" "$FIJI_DIR/jars/Lib/HughesLabTools"
            if [ -f "$MAIN_SCRIPT" ]; then
                mkdir -p "$FIJI_DIR/scripts/Hughes_Lab_Tools"
                debug_print "Creating symbolic link to main_.py as 'All VMO Tools.py' in $FIJI_DIR/scripts/Hughes_Lab_Tools/"
                ln $LN_FLAGS "$HUGHESTOOL_DIR/main_.py" "$FIJI_DIR/scripts/Hughes_Lab_Tools/All_VMO_Tools.py"
            fi
            break
            ;;
        "Uninstall Hughes Lab Tools")
            echo "Uninstalling Hughes Lab Tools from Fiji ..."
            rm -rf "$FIJI_DIR/jars/Lib/HughesLabTools"
            rm -rf "$FIJI_DIR/scripts/Hughes_Lab_Tools"
            break
            ;;
        "Quit")
            echo "Quitting ... no changes were made"
            break
            ;;
        *) echo "Invalid option $REPLY";;
    esac
done

echo "Done"
