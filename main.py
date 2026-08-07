from app.bootstrap import create_application


def main():

    pipeline = create_application()

    result = pipeline.run(
        "crear proyecto Laravel llamado demo",
    )

    print(
        result,
    )


if __name__ == "__main__":
    main()
