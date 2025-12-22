# Qt6 Built-in Styles

## Available Styles in PyQt6

PMU-30 Configurator supports switching between different styles via the **View → Application Style** menu.

### 1. Fluent Design (Custom) - **Default**

Our custom theme based on Microsoft Fluent Design for Windows 11:
- **Base**: Qt Fusion style
- **Color Scheme**: Dark theme (#202020 background, #0078d4 accent)
- **Features**:
  - Acrylic Material effects
  - Rounded corners (4px controls, 8px cards)
  - Reveal Highlight on hover
  - Professional Windows 11 appearance
  - Optimized for dark theme

### 2. Fusion

Modern cross-platform Qt style:
- **Platform**: All platforms
- **Appearance**: Modern, flat design
- **Features**:
  - Looks the same on all platforms
  - Good dark theme support
  - Recommended for cross-platform applications
- **Usage**: Base style for our Fluent Design theme

### 3. Windows

Native Windows style:
- **Platform**: Windows
- **Appearance**: Classic Windows style
- **Features**:
  - Integrates with Windows system theme
  - Automatically adapts to OS settings
  - Lightweight and fast

### 4. WindowsVista

Windows Vista/7 style:
- **Platform**: Windows
- **Appearance**: Aero Glass style
- **Features**:
  - More modern than basic Windows
  - Gradient buttons and controls
  - Transparency support

### 5. Windows11 (if available)

Native Windows 11 style:
- **Platform**: Windows 11
- **Appearance**: Modern WinUI 3
- **Features**:
  - Rounded corners
  - Mica material
  - Modern color palette
- **Note**: Only available on Windows 11

## How to Switch Styles

### Via Menu:
1. Open **View** → **Application Style**
2. Select desired style from list
3. Style applies immediately

### Available Options:
- **Fluent Design (Custom)** - Recommended
- Fusion
- Windows
- WindowsVista
- Windows11 (on Windows 11)
- macOS (on macOS)

## Recommendations

### For Development:
**Fluent Design (Custom)** - best choice for:
- Professional appearance
- Consistency across all platforms
- Optimized dark theme
- Modern UI/UX

### For Debugging:
**Fusion** or native styles (Windows/Windows11) may be useful for:
- Compatibility checking
- Testing on different styles
- Performance comparison

### For OS Integration:
**Windows** or **Windows11** for:
- Maximum system integration
- Automatic adaptation to system theme
- Minimal resource consumption

## Programmatic Switching

Styles can also be switched programmatically:

```python
from PyQt6.QtWidgets import QApplication, QStyleFactory

# Get list of available styles
available_styles = QStyleFactory.keys()
print(f"Available styles: {available_styles}")

# Apply style
app = QApplication.instance()
app.setStyle("Fusion")

# Apply custom theme
from utils.theme import ThemeManager
ThemeManager.toggle_theme(app, dark_mode=True)
```

## Dark Mode

**Dark Mode** works only with **Fluent Design (Custom)** style:
- Toggle via **View** → **Dark Mode**
- Enabled by default
- Optimized for extended use

**Note**: Native Qt styles (Windows, Fusion, etc.) use their own color schemes and don't support our theme toggle.

## Known Features

### Fluent Design (Custom):
- Full support for all controls
- Optimized colors for dark theme
- Consistent appearance
- May look different on non-Windows platforms

### Qt Native Styles:
- Fast and lightweight
- Native OS integration
- May ignore custom colors
- Different appearance on different platforms

## Performance

All styles are optimized and don't noticeably affect performance:
- **Fluent Design**: ~10-15ms to apply stylesheet
- **Fusion**: ~5ms native rendering
- **Windows**: ~3ms native rendering

Switching between styles happens instantly without restarting the application.
