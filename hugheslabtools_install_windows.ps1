# Define Fiji installation directory
$FIJI_DIR = "C:\Program Files\Fiji.app"

# Parse flags
param (
    [switch]$v
)

$VERBOSE = $v

# Function to print debug messages if verbose mode is enabled
function Debug-Print {
    param([string]$message)
    if ($VERBOSE) {
        Write-Host $message
    }
}

# Check if Fiji is installed
if (-not (Test-Path $FIJI_DIR)) {
    Write-Host "Fiji is not installed in $FIJI_DIR."
    Write-Host "Please install Fiji from https://fiji.sc/#download and try again."
    exit 1
}

Write-Host "Fiji is installed. Proceeding with installation..."

# Make necessary directories
New-Item -ItemType Directory -Force -Path "$FIJI_DIR\jars\Lib" | Out-Null
New-Item -ItemType Directory -Force -Path "$FIJI_DIR\scripts\Hughes Lab Tools" | Out-Null

# Get the absolute path to the directory containing this script
$DIR = $PSScriptRoot
Debug-Print "Resolved script directory (DIR): $DIR"

# Choose install type
$options = @(
    "Install Hughes Lab Tools from GitHub (End-user Mode)",
    "SymLink Hughes Lab Tools (Developer Mode)",
    "Uninstall Hughes Lab Tools",
    "Quit"
)

$selection = $options | Out-GridView -Title "Please choose installation type" -PassThru

switch ($selection) {
    "Install Hughes Lab Tools from GitHub (End-user Mode)" {
        Write-Host "Installing Hughes Lab Tools from GitHub ..."
        # Clone the repository
        git clone https://github.com/aforsythe/HughesLabTools.git hugheslabtools_temp
        if (-not (Test-Path "hugheslabtools_temp")) {
            Write-Host "Failed to clone Hughes Lab Tools repository."
            exit 1
        }
        # Remove existing files if they exist
        Remove-Item -Recurse -Force "$FIJI_DIR\jars\Lib\HughesLabTools" -ErrorAction SilentlyContinue
        Remove-Item -Force "$FIJI_DIR\scripts\Hughes Lab Tools\main_.py" -ErrorAction SilentlyContinue
        # Copy HughesLabTools package to Fiji's jars/Lib directory
        Debug-Print "Copying HughesLabTools package to $FIJI_DIR\jars\Lib\HughesLabTools"
        Copy-Item -Recurse "hugheslabtools_temp\src\HughesLabTools" "$FIJI_DIR\jars\Lib\" -Force
        # Copy main_.py to Fiji's scripts directory
        Debug-Print "Copying main_.py to $FIJI_DIR\scripts\Hughes Lab Tools\"
        Copy-Item "hugheslabtools_temp\src\HughesLabTools\main_.py" "$FIJI_DIR\scripts\Hughes Lab Tools\" -Force
        # Remove temporary clone
        Remove-Item -Recurse -Force hugheslabtools_temp
        Write-Host "Installation completed successfully."
    }
    "SymLink Hughes Lab Tools (Developer Mode)" {
        Write-Host "Creating Symbolic Links to Hughes Lab Tools ..."
        # Prompt for the local path to the HughesLabTools repository
        $REPO_PATH = Read-Host "Enter the local path to your HughesLabTools repository (e.g., C:\Users\username\Path\To\HughesLabTools)"
        if (-not (Test-Path $REPO_PATH)) {
            Write-Host "The provided path does not exist. Please ensure the path is correct and try again."
            exit 1
        }
        # Update paths to source directories
        $HLT_PACKAGE_DIR = "$REPO_PATH\src\HughesLabTools"
        $MAIN_SCRIPT_PATH = "$HLT_PACKAGE_DIR\main_.py"

        # Validate source directories
        if (-not (Test-Path $HLT_PACKAGE_DIR)) {
            Write-Host "Error: Source directory '$HLT_PACKAGE_DIR' does not exist."
            exit 1
        }
        if (-not (Test-Path $MAIN_SCRIPT_PATH)) {
            Write-Host "Error: main_.py not found at '$MAIN_SCRIPT_PATH'."
            exit 1
        }

        # Remove existing files if they exist
        Remove-Item -Recurse -Force "$FIJI_DIR\jars\Lib\HughesLabTools" -ErrorAction SilentlyContinue
        Remove-Item -Force "$FIJI_DIR\scripts\Hughes Lab Tools\main_.py" -ErrorAction SilentlyContinue
        # Create symbolic links
        Debug-Print "Creating symlink for HughesLabTools package"
        New-Item -ItemType SymbolicLink -Path "$FIJI_DIR\jars\Lib\HughesLabTools" -Target $HLT_PACKAGE_DIR -Force
        Debug-Print "Creating symlink for main_.py"
        New-Item -ItemType SymbolicLink -Path "$FIJI_DIR\scripts\Hughes Lab Tools\main_.py" -Target $MAIN_SCRIPT_PATH -Force
        Write-Host "Symbolic links created successfully."
    }
    "Uninstall Hughes Lab Tools" {
        Write-Host "Uninstalling Hughes Lab Tools from Fiji ..."
        # Remove files if they exist
        Remove-Item -Recurse -Force "$FIJI_DIR\jars\Lib\HughesLabTools" -ErrorAction SilentlyContinue
        Remove-Item -Force "$FIJI_DIR\scripts\Hughes Lab Tools\main_.py" -ErrorAction SilentlyContinue
        Write-Host "Hughes Lab Tools have been uninstalled."
    }
    "Quit" {
        Write-Host "Quitting ... no changes were made."
        exit 0
    }
}

# Done
Write-Host "Done"