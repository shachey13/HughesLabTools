# Hughes Lab Tools for VMT Device Image Processing

## Overview

The Hughes Lab Tools are designed for processing images captured from VMT (Vascular and Tumor) devices using ImageJ/Fiji. This project leverages ImageJ’s powerful image processing capabilities and integrates custom tools for VMT image analysis, providing a tailored interface for operations such as thresholding, segmentation, and measurement.

## Project Structure and Key Classes

### **Device Class**
The `Device` class serves as the base class for managing general device-related operations. This class provides a foundation that other specialized classes can extend for more specific functionality.

### **DeviceManager Class**
The `DeviceManager` class orchestrates the image processing workflow. It handles user input from the GUI, manages options, and executes the appropriate operations on the images. This class acts as the central controller, coordinating between the GUI, `DeviceImage` objects, and user preferences.

### **DeviceImage Class**
The `DeviceImage` class is a subclass of ImageJ's `ImagePlus` class. By extending `ImagePlus`, it inherits all of ImageJ’s core image handling capabilities while adding device-specific processing features, such as saving and loading VMT images.

### **TumorImage Class**
The `TumorImage` class extends `DeviceImage` and provides specialized methods for tumor VMT image analysis, such as segmentation, measuring grey levels, and calculating circularity.

### **VesselImage Class**
The `VesselImage` class extends `DeviceImage` and focuses on vascular VMT image analysis, offering methods for thresholding images, converting them to masks, and measuring vessel diameters.

### **VmoToolsGui Class**
The `VmoToolsGui` class is responsible for creating and displaying the graphical user interface (GUI) that collects user input. It allows users to select various options for image processing, such as the number of image types, color settings, and processing functions (e.g., segmentation or thresholding). These options are then stored in an `options` dictionary.

Users can interact with this GUI to configure their processing tasks. However, the `VmoToolsGui` class also allows for programmatic configuration. Instead of manually inputting all options through the GUI, you can set options directly in code and pass them to the `DeviceManager`, allowing for automation and scripting.

### **ImageTypeChangerGui Class**
The `ImageTypeChangerGui` class handles interactions related to changing the type of image being processed. This includes confirming the image type and switching between image types as needed.

## Option Setting Methods

### Programmatic Option Setting

While the GUI is the primary method for configuring options, options can also be set programmatically and passed directly to the `DeviceManager` for execution. This is useful for automating processes or integrating the tool into larger workflows.

Here’s an example of how you can bypass the GUI and set options programmatically in a script:

```python
import os
from HughesLabTools.DeviceManager import DeviceManager
from HughesLabTools import gui

# Create a DeviceManager instance
device_manager = DeviceManager(verbose=True)

# Set options programmatically
options = {
    'numTypes': 2,
    'typeNames': ['Tumor', 'Vessel'],
    'typeColors': ['Red', 'Green'],
    'segment': True,
    'threshold': False
}

# Configure DeviceManager with these options
device_manager.configure(options)

# Now you can proceed with further processing
device_manager.run_selected_processes()
```

In this example, the options dictionary is populated directly in the code and passed to the `DeviceManager`. This bypasses the need to manually configure the options through the GUI, enabling automation and scripting.

### GUI Option Setting

Alternatively, you can use the GUI to set the options interactively and then pass them to the `DeviceManager` for processing. Here’s an example of how to do this:

```python
import os
from HughesLabTools.DeviceManager import DeviceManager
from HughesLabTools import gui

# Create a DeviceManager instance
device_manager = DeviceManager(verbose=True)

# Run the GUI and configure options
device_manager.configure_with_gui()

# Now you can proceed with further processing if processes are selected
device_manager.run_selected_processes()
```

In this example, the `VmoToolsGui` class is used to display the GUI, collect options from the user, and configure the `DeviceManager`. Once the options are set, the images can be processed as per the user’s selections.

### How It Works

1. **Collecting Options via GUI**:
   - The `VmoToolsGui` class displays the GUI and collects options such as the number of image types, their names, and their colors. Users can select the image processing functions to perform (e.g., segmentation or thresholding).

2. **Programmatic Configuration**:
   - Instead of manually selecting options through the GUI, options can be set directly in the script. The `DeviceManager` class can then be configured with these options, allowing for automated workflows.

3. **Running Processes**:
   - Once options are configured (either via the GUI or programmatically), the `DeviceManager` can execute the selected processes using the `run_selected_processes()` method.

## Extending the Project

### **Adding New Image Types**
1. **Create a New Image Class**:
   - Define a new class that extends `DeviceImage`. Implement specific methods for processing the new image type.
   - Example:
   ```python
   from DeviceImage import DeviceImage

   class NewImageType(DeviceImage):
       def process_specific_feature(self):
           # Implement processing logic here
           pass
   ```

2. **Integrate with GUI**:
   - Update `VmoToolsGui` to include options for the new image type, allowing users to select it from the interface.

3. **Update DeviceManager**:
   - Extend `DeviceManager` to handle the new image type and its associated operations.

### **Adding New Image Processing Functions**
1. **Define New Functions**:
   - Add new methods in the relevant image class (e.g., `TumorImage` or `VesselImage`).
   - Ensure the new methods are integrated into the image processing workflow.

2. **Update GUI**:
   - Modify `VmoToolsGui` to include new options for these additional functions.

3. **Testing**:
   - Test the new functionality across various images to ensure correctness.

## Leveraging ImageJ/Fiji

This project integrates tightly with ImageJ/Fiji, utilizing the `ImagePlus` class and all its associated capabilities. Since the `DeviceImage` class subclasses `ImagePlus`, you can apply any ImageJ functionality directly within the project. This allows for extending the toolset by incorporating ImageJ plugins and further customizing the image processing pipeline.

## Issues, Feature Requests, and Todos

If you encounter any problems, have feature requests, or want to track todos, please use the GitHub Issues page for this project. This helps us keep track of everything and ensures that contributions and fixes are handled efficiently.

## Contribution

Fork the repository, implement your features or fixes, and submit a pull request. Ensure that your code is well-documented and thoroughly tested.

## Dependencies

1. **Shape Smoothing Plugin** for ImageJ/Fiji:
   - Add new methods in the relevant image class (e.g., `TumorImage` or `VesselImage`).
   - Ensure the new methods are integrated into the image processing workflow.
   - **Download Link:** [Shape Smoothing Plugin](https://imagej.net/plugins/shape-smoothing)
   - **Description:** The Shape Smoothing plugin performs Fourier smoothing on binary images to reduce the number of vertices and smooth object boundaries.

## Installation

### Shape Smoothing Plugin

The **Shape Smoothing** plugin is required for the shape smoothing functionality in this project. Please follow the steps below to download and install the plugin:

1. **Download the Shape Smoothing Plugin:**

   - Visit the [Shape Smoothing plugin page](https://imagej.net/plugins/shape-smoothing).
   - Download the latest version of the plugin, typically provided as a `.jar` or `.class` file.

2. **Install the Plugin in ImageJ/Fiji:**

   - Locate your ImageJ or Fiji installation directory.
   - Find the `plugins` folder within the installation directory.
     - For **ImageJ**: This may be in `C:\ImageJ\plugins` (Windows) or `/Applications/ImageJ/plugins` (macOS).
     - For **Fiji**: This may be in `C:\Fiji.app\plugins` (Windows) or `/Applications/Fiji.app/plugins` (macOS).
   - Copy the downloaded plugin file (`Shape_Smoothing.jar` or `Shape_Smoothing.class`) into the `plugins` folder.
   - **Optional:** You can create a subfolder within `plugins` (e.g., `plugins/ShapeTools`) and place the plugin there for better organization.

3. **Restart ImageJ/Fiji:**

   - Close any running instances of ImageJ or Fiji.
   - Launch ImageJ or Fiji again to load the new plugin.

4. **Verify the Plugin Installation:**

   - In ImageJ/Fiji, go to `Plugins` in the menu bar.
   - Look for `Shape Smoothing` in the list. If it's in a subfolder, navigate to the appropriate submenu.
   - If the plugin appears in the menu, it's installed correctly.

**Note:** Ensure you have the latest version of ImageJ or Fiji for compatibility.

## License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.
