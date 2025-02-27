#!/bin/bash

# Define Fiji installation directory
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

# Check if Fiji is installed
if [ ! -d "$FIJI_DIR" ]; then
    echo "Fiji is not installed in $FIJI_DIR."
    echo "Please install Fiji from https://fiji.sc/#download and try again."
    exit 1
fi

echo "Fiji is installed. Proceeding with installation..."

# Prompt user for installation type
PS3='Please choose installation type: '
options=("Install Hughes Lab Tools from GitHub (End-user Mode)" "SymLink Hughes Lab Tools (Developer Mode)" "Uninstall Hughes Lab Tools" "Quit")

# Make necessary directories
mkdir -p "$FIJI_DIR/jars/Lib"
mkdir -p "$FIJI_DIR/scripts/Hughes Lab Tools"

# Get the absolute path to the directory containing this script
cd "$(dirname "${BASH_SOURCE[0]}")" || exit
DIR="$(pwd)"
debug_print "Resolved script directory (DIR): $DIR"

# Set cp and ln flags based on verbosity
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
        "Install Hughes Lab Tools from GitHub (End-user Mode)")
            echo "Installing Hughes Lab Tools from GitHub ..."
            # Clone the repository
            git clone https://github.com/aforsythe/HughesLabTools.git hugheslabtools_temp
            if [ ! -d "hugheslabtools_temp" ]; then
                echo "Failed to clone Hughes Lab Tools repository."
                exit 1
            fi
            # Remove existing files if they exist
            rm -rf "$FIJI_DIR/jars/Lib/HughesLabTools"
            rm -f "$FIJI_DIR/scripts/Hughes Lab Tools/main_.py"
            # Copy HughesLabTools package to Fiji's jars/Lib directory
            debug_print "Copying HughesLabTools package to $FIJI_DIR/jars/Lib/HughesLabTools"
            cp $CP_FLAGS "hugheslabtools_temp/src/HughesLabTools" "$FIJI_DIR/jars/Lib/"
            # Copy main_.py to Fiji's scripts directory
            debug_print "Copying main_.py to $FIJI_DIR/scripts/Hughes Lab Tools/"
            cp $CP_FLAGS "hugheslabtools_temp/src/HughesLabTools/main_.py" "$FIJI_DIR/scripts/Hughes Lab Tools/"
            # Remove temporary clone
            rm -rf hugheslabtools_temp
            echo "Installation completed successfully."
            break
            ;;
        "SymLink Hughes Lab Tools (Developer Mode)")
            echo "Creating Symbolic Links to Hughes Lab Tools ..."
            # Prompt for the local path to the HughesLabTools repository
            read -p "Enter the local path to your HughesLabTools repository (e.g., /Users/username/Path/To/HughesLabTools): " REPO_PATH
            if [ ! -d "$REPO_PATH" ]; then
                echo "The provided path does not exist. Please ensure the path is correct and try again."
                exit 1
            fi
            # Update paths to source directories
            HLT_PACKAGE_DIR="$REPO_PATH/src/HughesLabTools"
            MAIN_SCRIPT_PATH="$HLT_PACKAGE_DIR/main_.py"

            # Validate source directories
            if [ ! -d "$HLT_PACKAGE_DIR" ]; then
                echo "Error: Source directory '$HLT_PACKAGE_DIR' does not exist."
                exit 1
            fi
            if [ ! -f "$MAIN_SCRIPT_PATH" ]; then
                echo "Error: main_.py not found at '$MAIN_SCRIPT_PATH'."
                exit 1
            fi

            # Remove existing files if they exist
            rm -rf "$FIJI_DIR/jars/Lib/HughesLabTools"
            rm -f "$FIJI_DIR/scripts/Hughes Lab Tools/main_.py"
            # Create symbolic links
            debug_print "Creating symlink for HughesLabTools package"
            ln $LN_FLAGS "$HLT_PACKAGE_DIR" "$FIJI_DIR/jars/Lib/HughesLabTools"
            debug_print "Creating symlink for main_.py"
            ln $LN_FLAGS "$MAIN_SCRIPT_PATH" "$FIJI_DIR/scripts/Hughes Lab Tools/"
            echo "Symbolic links created successfully."
            break
            ;;
        "Uninstall Hughes Lab Tools")
            echo "Uninstalling Hughes Lab Tools from Fiji ..."
            # Remove files if they exist
            rm -rf "$FIJI_DIR/jars/Lib/HughesLabTools"
            rm -f "$FIJI_DIR/scripts/Hughes Lab Tools/main_.py"
            echo "Hughes Lab Tools have been uninstalled."
            break
            ;;
        "Quit")
            echo "Quitting ... no changes were made."
            exit 0
            ;;
        *) echo "Invalid option $REPLY";;
    esac
done

# Done
echo "Done"