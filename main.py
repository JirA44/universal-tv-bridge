"""Universal TV Bridge — entry point."""
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    try:
        from ui.main_window import MainWindow
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Run:  pip install -r requirements.txt")
        sys.exit(1)

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
