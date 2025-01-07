print("running")
import os
from HughesLabTools.DeviceManager import DeviceManager
from HughesLabTools import gui

# Create a DeviceManager instance
device_manager = DeviceManager(verbose=True)

# Run the GUI and configure options
device_manager.configure_with_gui()

# Now you can proceed with further processing if processes are selected
if device_manager:
    device_manager.run_selected_processes()