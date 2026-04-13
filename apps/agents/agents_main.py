from workers.celery_app import celery_app


def main():
    celery_app.worker_main(argv=["worker", "--loglevel=info"])


if __name__ == "__main__":
    main()
