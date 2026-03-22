import os
import time
import imagehash
from PIL import Image
from mss import mss


class ScreenCapturer:
    def __init__(self, threshold=10, save_path="/tmp/weruh-frame.jpg"):
        self.threshold = threshold
        # Default to a generic tmp directory if /tmp is not available (like Windows)
        if os.name == "nt":
            self.save_path = os.path.join(
                os.environ.get("TEMP", "C:\\temp"), "weruh-frame.jpg"
            )
        else:
            self.save_path = save_path
        self.prev_hash = None
        self.sct = mss()

    def capture(self):
        """Captures the primary monitor and evaluates change."""
        try:
            # monitors[1] is usually the primary monitor
            monitor = self.sct.monitors[1]
            sct_img = self.sct.grab(monitor)

            # Convert mss image to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Compute hash on the full resolution image
            current_hash = imagehash.phash(img)

            has_changed = False
            if self.prev_hash is None:
                has_changed = True
            else:
                delta = self.prev_hash - current_hash
                if delta >= self.threshold:
                    has_changed = True

            if has_changed:
                self.prev_hash = current_hash
                # Ensure directory exists
                os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

                # Resize image to prevent massive base64 JSON payloads (WinError 10054 / PayloadTooLarge)
                # Max dimension 1024 to maintain readability but reduce file size well below the standard 100kb JSON limit
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

                # Convert to RGB to save as JPEG safely (though it's already RGB after frombytes)
                img.save(self.save_path, format="JPEG", quality=65, optimize=True)
                return True, self.save_path

            return False, None

        except Exception as e:
            print(f"[Capture] Error: {e}")
            return False, None

    def close(self):
        self.sct.close()
