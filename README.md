# AfterCursors

A fun little desktop toy I made for the vibes.

You know that scene in Jujutsu Kaisen where Naobito Zen'in uses **Projection Sorcery** and leaves those ghostly afterimages trailing behind him? Yeah, that look. I wanted something similar but for the mouse cursor. So I built this.

Yes, I know Windows already has a built-in mouse trail feature. But I wanted to take that idea a little further. Proper fade in and fade out curves, and a settings panel where you can tweak everything to your liking.

## Features

- Fade in and fade out with adjustable timing
- Customizable fill color and contour outline color
- Adjustable lifetime for each shadow
- Configurable delay between spawns
- Clean dark themed settings panel
- Covers all monitors 

## How It Works

Every few milliseconds the app captures your current cursor, tints it with your chosen colors, and places it on a transparent overlay that sits on top of everything. As you move your mouse, these copies accumulate and fade out over time, creating that smooth trailing effect.

## Requirements

- Windows
- Python 3.7+
- pywin32
- Pillow

## Installation

- Install Python x3.7
- Pip install pywin32
- Pip install Pillow
- Download .exe or .py file and launch it


## Usage

1. Run the script
2. Adjust the sliders to your liking
3. Pick your colors for fill and contour
4. Click **Start**
5. Move your mouse around and enjoy

Click **Stop** to hide the effect, or just close the window.

## Settings

| Setting | What It Does |
|---|---|
| **Fade In** | How long each shadow takes to fully appear |
| **Fade Out** | How long each shadow takes to disappear at the end |
| **Lifetime** | Total time a shadow stays visible |
| **Delay** | Time between spawning new shadows |
| **Color** | Fill color of the afterimages |
| **Contour** | Outline color around each afterimage | 

## Inspiration

Partially inspired by the **Projection Sorcery** technique from Jujutsu Kaisen. Also takes some DNA from the old Windows XP mouse trails, but with more style and actual settings to play with. Mostly just a "what if cursor go woosh" kind of project.
