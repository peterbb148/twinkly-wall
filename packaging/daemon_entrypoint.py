"""Entry point for the self-contained twinklywall executable."""

from twinkly_wall.daemon import main

if __name__ == "__main__":
    raise SystemExit(main())
