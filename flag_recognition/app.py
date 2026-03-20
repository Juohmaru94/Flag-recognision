from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from flag_recognition.capture import RegionSelector, ScreenCapturer
from flag_recognition.config import AppConfig, FixedRegion
from flag_recognition.hotkeys import GlobalHotkeyManager, HotkeyRegistrationError
from flag_recognition.recognition import FlagRecognizer
from flag_recognition.typing_utils import Typer

logger = logging.getLogger("flag_recognition")


class FlagRecognitionApp:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.recognizer = FlagRecognizer(config.dataset_dir)
        self.capturer = ScreenCapturer(debug=config.debug, debug_dir=config.debug_dir)
        self.selector = RegionSelector(min_region_size=config.min_region_size)
        self.typer = Typer(delay_ms=config.type_delay_ms, press_enter=config.press_enter)

    def run_once_for_region(self, region: FixedRegion) -> None:
        logger.info("capture triggered")
        capture = self.capturer.capture_region(region)
        logger.info("image size: %sx%s", capture.image.width, capture.image.height)
        match = self.recognizer.recognize(capture.image, top_k=3)
        logger.info("top 3 candidate matches: %s", match.top_k)
        logger.info("selected result: %s", match.country)
        logger.info("confidence: %.3f", match.confidence)

        if match.confidence < self.config.confidence_threshold:
            logger.info("skipped output: low confidence")
            return

        self.typer.type_text(match.country)
        logger.info("typed output: %s", match.country)

    def run_hotkey_mode(self) -> None:
        hotkeys = GlobalHotkeyManager()

        def on_hotkey() -> None:
            selection = self.selector.select_region()
            if selection is None:
                logger.info("skipped output: selection cancelled or too small")
                return
            self.run_once_for_region(selection)

        try:
            hotkeys.register(self.config.hotkey, on_hotkey)
        except HotkeyRegistrationError:
            logger.exception("Hotkey registration failed")
            raise

        logger.info("Listening for hotkey '%s'. Press Ctrl+C to exit.", self.config.hotkey)
        try:
            hotkeys.wait()
        finally:
            hotkeys.cleanup()

    def run_fixed_mode(self, loop: bool = False) -> None:
        region = self.config.fixed_region
        if not region.is_valid():
            raise ValueError("fixed_region is not configured. Run the calibrate command or edit config.json.")

        if not loop:
            self.run_once_for_region(region)
            return

        logger.info("Watch mode enabled with interval %sms", self.config.loop_interval_ms)
        try:
            while True:
                self.run_once_for_region(region)
                time.sleep(self.config.loop_interval_ms / 1000.0)
        except KeyboardInterrupt:
            logger.info("Watch mode stopped by user")

    def calibrate_fixed_region(self, save: bool, config_path: Path) -> None:
        selection = self.selector.select_region()
        if selection is None:
            logger.info("Calibration cancelled")
            return

        logger.info(
            "Fixed region: left=%s top=%s width=%s height=%s",
            selection.left,
            selection.top,
            selection.width,
            selection.height,
        )
        if save:
            self.config.fixed_region = selection
            self.config.save(config_path)
            logger.info("Saved fixed region to %s", config_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recognize country flags from the screen and type the result.")
    parser.add_argument("--config", default="config.json", help="Path to JSON config file.")
    parser.add_argument("--mode", choices=["hotkey", "fixed"], default="hotkey")
    parser.add_argument("--loop", action="store_true", help="Repeat fixed-region captures until interrupted.")
    parser.add_argument("--calibrate", action="store_true", help="Select a region and print coordinates for fixed mode.")
    parser.add_argument("--save-region", action="store_true", help="Persist calibration into the config file.")
    return parser


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config_path = Path(args.config)
    config = AppConfig.load(config_path)
    configure_logging(config.debug)

    app = FlagRecognitionApp(config)

    if args.calibrate:
        app.calibrate_fixed_region(save=args.save_region, config_path=config_path)
        return

    if args.mode == "hotkey":
        app.run_hotkey_mode()
    else:
        app.run_fixed_mode(loop=args.loop)


if __name__ == "__main__":
    main()
