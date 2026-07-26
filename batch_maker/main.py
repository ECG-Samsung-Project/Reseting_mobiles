try:
    from .frontend import run_app
except ImportError:
    from frontend import run_app


if __name__ == "__main__":
    run_app()