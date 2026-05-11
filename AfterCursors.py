import sys
import time
import struct
import ctypes
import tkinter as tk
from tkinter import colorchooser

try:
    import win32gui
    import win32api
    import win32con
except ImportError:
    print("Install pywin32: pip install pywin32")
    sys.exit(1)

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print("Install Pillow: pip install pillow")
    sys.exit(1)


# Window procedure for the transparent overlay window
# It handles basic messages to keep the window alive and skip painting
def overlay_wnd_proc(hwnd, msg, wparam, lparam):
    if msg == win32con.WM_DESTROY:
        win32gui.PostQuitMessage(0)
        return 0
    if msg == win32con.WM_PAINT:
        win32gui.ValidateRect(hwnd, None)
        return 0
    return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)


# Main application class that creates both the settings menu and the overlay
class AfterCursorsApp:
    def __init__(self):
        # Make the app DPI aware so cursor coordinates match screen pixels
        # This prevents offset issues on high DPI displays
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass

        self.root = tk.Tk()
        self.root.title("AfterCursors")
        self.root.configure(bg='black')
        self.root.resizable(False, False)

        # Default values for all the effect parameters
        self.fade_in = tk.DoubleVar(value=0.2)
        self.fade_out = tk.DoubleVar(value=0.5)
        self.lifetime = tk.DoubleVar(value=2.0)
        self.delay = tk.DoubleVar(value=0.1)
        self.color = (255, 0, 255)
        self.contour_color = (0, 0, 0)

        # State variables for the effect loop
        self.running = False
        self.overlay_hwnd = None
        self.afterimages = []          # Stores (x, y, spawn_time) tuples
        self.last_spawn_time = 0
        self.update_id = None

        self.create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.create_overlay()

        self.root.mainloop()

    # Build the settings menu with all sliders and buttons
    def create_widgets(self):
        pad = {'padx': 10, 'pady': 5}
        tk.Label(self.root, text="AfterCursors", fg='white', bg='black',
                 font=('Arial', 14, 'bold')).pack(**pad)

        self._make_scale('Fade In (sec)',  self.fade_in,  0.0, 3.0, 0.1)
        self._make_scale('Fade Out (sec)', self.fade_out, 0.0, 3.0, 0.1)
        self._make_scale('Lifetime (sec)', self.lifetime, 0.5, 10.0, 0.1)
        self._make_scale('Delay (sec)',    self.delay,    0.01, 1.0, 0.01)

        btn_frame = tk.Frame(self.root, bg='black')
        btn_frame.pack(fill='x', **pad)
        self.color_btn = tk.Button(btn_frame, text='Color', bg=self._to_hex(self.color),
                                   fg='white', command=self.choose_color)
        self.color_btn.pack(side='left', padx=5)
        self.contour_btn = tk.Button(btn_frame, text='Contour', bg=self._to_hex(self.contour_color),
                                     fg='white', command=self.choose_contour)
        self.contour_btn.pack(side='left', padx=5)

        self.toggle_btn = tk.Button(self.root, text='Start', bg='#222', fg='white',
                                    command=self.toggle)
        self.toggle_btn.pack(pady=10)

    # Helper to create a labeled slider quickly
    def _make_scale(self, label, variable, from_, to, resolution):
        frame = tk.Frame(self.root, bg='black')
        frame.pack(fill='x', padx=10, pady=2)
        tk.Label(frame, text=label, fg='white', bg='black', width=18, anchor='w').pack(side='left')
        scale = tk.Scale(frame, from_=from_, to=to, resolution=resolution,
                         orient='horizontal', variable=variable,
                         bg='#333', fg='white', highlightbackground='black',
                         troughcolor='#555', length=200)
        scale.pack(side='right', padx=5)

    # Convert RGB tuple to hex string for button colors
    def _to_hex(self, rgb):
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    # Open color picker for the fill color
    def choose_color(self):
        col = colorchooser.askcolor(color=self._to_hex(self.color), title="Shadow color")
        if col[0]:
            self.color = tuple(int(c) for c in col[0])
            self.color_btn.configure(bg=self._to_hex(self.color))

    # Open color picker for the contour color
    def choose_contour(self):
        col = colorchooser.askcolor(color=self._to_hex(self.contour_color), title="Contour color")
        if col[0]:
            self.contour_color = tuple(int(c) for c in col[0])
            self.contour_btn.configure(bg=self._to_hex(self.contour_color))

    # Start or stop the afterimage effect
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    # Begin the effect loop and show the overlay
    def start(self):
        if self.running:
            return
        self.running = True
        self.afterimages.clear()
        self.last_spawn_time = time.perf_counter()
        win32gui.ShowWindow(self.overlay_hwnd, win32con.SW_SHOWNA)
        self.toggle_btn.configure(text='Stop')
        self.update()

    # Stop the effect loop and hide everything
    def stop(self):
        self.running = False
        if self.update_id:
            self.root.after_cancel(self.update_id)
            self.update_id = None
        win32gui.ShowWindow(self.overlay_hwnd, win32con.SW_HIDE)
        self.afterimages.clear()
        self.toggle_btn.configure(text='Start')

    # Clean up when the window is closed
    def on_closing(self):
        self.stop()
        if self.overlay_hwnd:
            win32gui.DestroyWindow(self.overlay_hwnd)
        self.root.destroy()

    # Create a fullscreen transparent overlay window that covers all monitors
    # This is where the afterimages will be drawn
    def create_overlay(self):
        self.x_origin = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        self.y_origin = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        self.screen_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        self.screen_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = overlay_wnd_proc
        wc.hInstance = win32gui.GetModuleHandle(None)
        wc.lpszClassName = "AfterCursorsOverlay"
        try:
            win32gui.RegisterClass(wc)
        except:
            pass

        ex_style = (win32con.WS_EX_LAYERED |
                    win32con.WS_EX_TRANSPARENT |
                    win32con.WS_EX_TOPMOST |
                    win32con.WS_EX_NOACTIVATE)

        self.overlay_hwnd = win32gui.CreateWindowEx(
            ex_style,
            wc.lpszClassName,
            "AfterCursorsOverlay",
            win32con.WS_POPUP,
            self.x_origin, self.y_origin,
            self.screen_width, self.screen_height,
            None, None, wc.hInstance, None
        )
        win32gui.ShowWindow(self.overlay_hwnd, win32con.SW_HIDE)

    # Capture the current cursor as an RGBA image using GDI
    # Returns the PIL image and the hotspot coordinates
    def get_cursor_rgba(self):
        hcursor = win32gui.GetCursor()
        if not hcursor:
            return None, (0, 0)

        try:
            icon_info = win32gui.GetIconInfo(hcursor)
        except:
            return None, (0, 0)

        fIcon, xHot, yHot, hbmMask, hbmColor = icon_info

        # Determine cursor dimensions from either the color or mask bitmap
        if hbmColor:
            bmp = win32gui.GetObject(hbmColor)
            width, height = bmp.bmWidth, bmp.bmHeight
            has_color = True
        elif hbmMask:
            bmp = win32gui.GetObject(hbmMask)
            width = bmp.bmWidth
            height = bmp.bmHeight // 2
            has_color = False
        else:
            return None, (0, 0)

        # Create a 32-bit DIB section to draw the cursor into
        bmi = ctypes.create_string_buffer(44)
        struct.pack_into('I', bmi, 0, 40)
        struct.pack_into('i', bmi, 4, width)
        struct.pack_into('i', bmi, 8, -height)
        struct.pack_into('H', bmi, 12, 1)
        struct.pack_into('H', bmi, 14, 32)
        struct.pack_into('I', bmi, 16, 0)

        gdi32 = ctypes.windll.gdi32
        ppvBits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(0, bmi, 0, ctypes.byref(ppvBits), 0, 0)
        if not hbmp:
            if hbmColor: win32gui.DeleteObject(hbmColor)
            if hbmMask:  win32gui.DeleteObject(hbmMask)
            return None, (0, 0)

        hdc = win32gui.CreateCompatibleDC(0)
        old_bmp = win32gui.SelectObject(hdc, hbmp)
        win32gui.PatBlt(hdc, 0, 0, width, height, win32con.BLACKNESS)

        # Draw the actual cursor onto our DIB
        if has_color:
            win32gui.DrawIconEx(hdc, 0, 0, hcursor, width, height, 0, 0, win32con.DI_NORMAL)
        else:
            # For monochrome cursors, just fill with white as a fallback
            white_brush = win32gui.GetStockObject(win32con.WHITE_BRUSH)
            win32gui.FillRect(hdc, (0, 0, width, height), white_brush)

        # Read the pixel data back into a buffer
        buf = (ctypes.c_ubyte * (width * height * 4))()
        gdi32.GetDIBits(hdc, hbmp, 0, height, buf, bmi, 0)

        # Clean up GDI objects
        win32gui.SelectObject(hdc, old_bmp)
        win32gui.DeleteDC(hdc)
        win32gui.DeleteObject(hbmp)
        if hbmColor: win32gui.DeleteObject(hbmColor)
        if hbmMask:  win32gui.DeleteObject(hbmMask)

        # Convert raw BGRA bytes to a PIL RGBA image
        image = Image.frombuffer('RGBA', (width, height), bytes(buf), 'raw', 'BGRA', 0, 1)
        return image, (xHot, yHot)

    # Apply fill and contour colors to a cursor image
    # All opaque pixels get replaced with fill_color, and an outline is added using contour_color
    def tint_image(self, src_rgba, fill_color, contour_color):
        src_alpha = src_rgba.getchannel('A')
        
        # Create a solid color layer using the alpha channel as a mask
        colored = Image.new('RGBA', src_rgba.size, (0, 0, 0, 0))
        colored.paste(fill_color + (255,), (0, 0), src_alpha)

        # Build the contour by dilating the alpha mask and subtracting the original
        mask = src_alpha.copy()
        dilated = mask.filter(ImageFilter.MaxFilter(3))
        contour_mask = Image.new('L', src_rgba.size, 0)
        contour_mask.paste(255, (0, 0), dilated)
        contour_mask.paste(0, (0, 0), mask)

        # Create the contour layer with the contour color
        contour_layer = Image.new('RGBA', src_rgba.size, (0, 0, 0, 0))
        contour_layer.paste(contour_color + (255,), (0, 0), contour_mask)

        # Combine fill and contour into one image
        result = Image.alpha_composite(colored, contour_layer)
        return result

    # Main render loop, runs about 60 times per second
    # Draws all active afterimages to the transparent overlay
    def update(self):
        if not self.running:
            return
        try:
            win32gui.PumpWaitingMessages()

            now = time.perf_counter()
            cursor_pos = win32api.GetCursorPos()
            x = cursor_pos[0] - self.x_origin
            y = cursor_pos[1] - self.y_origin

            # Spawn a new afterimage if enough time has passed
            if now - self.last_spawn_time >= self.delay.get():
                self.last_spawn_time = now
                self.afterimages.append((x, y, now))

            # Remove afterimages that have exceeded their lifetime
            lifetime = self.lifetime.get()
            self.afterimages = [img for img in self.afterimages if now - img[2] < lifetime]

            # Get the current cursor image to use as the shape
            cursor_img, (hot_x, hot_y) = self.get_cursor_rgba()
            if cursor_img is None:
                self.update_id = self.root.after(16, self.update)
                return

            width, height = self.screen_width, self.screen_height
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))

            fi = self.fade_in.get()
            fo = self.fade_out.get()

            # Draw each afterimage with the correct alpha based on its age
            for ix, iy, spawn_t in self.afterimages:
                age = now - spawn_t
                
                # Calculate alpha factor using fade in and fade out curves
                if age < fi:
                    alpha_factor = age / fi if fi > 0 else 1.0
                elif age > (lifetime - fo):
                    alpha_factor = (lifetime - age) / fo if fo > 0 else 1.0
                else:
                    alpha_factor = 1.0
                alpha_factor = max(0.0, min(1.0, alpha_factor))
                if alpha_factor <= 0:
                    continue

                # Tint the cursor with chosen colors and apply overall transparency
                tinted = self.tint_image(cursor_img, self.color, self.contour_color)
                final = tinted.copy()
                alpha = final.getchannel('A')
                scaled = alpha.point(lambda p: int(p * alpha_factor))
                final.putalpha(scaled)

                # Position the cursor so the hotspot aligns with where it was captured
                pos_x = ix - hot_x
                pos_y = iy - hot_y
                overlay.paste(final, (pos_x, pos_y), final)

            # Convert the overlay image to raw bytes for UpdateLayeredWindow
            bitmap = overlay.tobytes('raw', 'BGRA')
            hdc_screen = win32gui.GetDC(0)
            hdc_mem = win32gui.CreateCompatibleDC(hdc_screen)

            # Set up the bitmap info header for a 32-bit BGRA image
            bmi = ctypes.create_string_buffer(44)
            struct.pack_into('I', bmi, 0, 40)
            struct.pack_into('i', bmi, 4, width)
            struct.pack_into('i', bmi, 8, -height)
            struct.pack_into('H', bmi, 12, 1)
            struct.pack_into('H', bmi, 14, 32)
            struct.pack_into('I', bmi, 16, 0)

            # Create a DIB bitmap from the raw pixel data
            gdi32 = ctypes.windll.gdi32
            gdi32.CreateDIBitmap.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                                             ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
            gdi32.CreateDIBitmap.restype = ctypes.c_void_p

            bitmap_array = (ctypes.c_ubyte * len(bitmap)).from_buffer_copy(bitmap)
            p_bits = ctypes.cast(bitmap_array, ctypes.c_void_p)
            h_bitmap = gdi32.CreateDIBitmap(hdc_screen, bmi, 4, p_bits, bmi, 0)

            # Update the layered window with per-pixel alpha blending
            win32gui.SelectObject(hdc_mem, int(h_bitmap))
            blend = (0, 0, 255, win32con.AC_SRC_ALPHA)
            win32gui.UpdateLayeredWindow(
                self.overlay_hwnd, hdc_screen, None,
                (width, height), hdc_mem, (0, 0), 0,
                blend, win32con.ULW_ALPHA
            )

            # Clean up GDI resources to avoid memory leaks
            win32gui.DeleteObject(int(h_bitmap))
            win32gui.DeleteDC(hdc_mem)
            win32gui.ReleaseDC(0, hdc_screen)

        except Exception as e:
            print("Error in update:", e)

        # Schedule the next frame
        self.update_id = self.root.after(16, self.update)


if __name__ == '__main__':
    AfterCursorsApp()