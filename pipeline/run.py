from pipeline.extract import extract_all
from pipeline.load import load_all

def main():
    extract_all()
    load_all()


if __name__ == "__main__":
    main()