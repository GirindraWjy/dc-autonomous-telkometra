import os
import time
import importlib.util
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

WIB = timezone(
    timedelta(hours=7)
)

def load_pages():

    pages = []

    page_directory = "page"

    if not os.path.exists(page_directory):
        raise FileNotFoundError(
            f"Folder '{page_directory}' tidak ditemukan."
        )

    for filename in os.listdir(page_directory):

        if not filename.endswith(".py"):
            continue

        if filename == "__init__.py":
            continue

        path = os.path.join(
            page_directory,
            filename
        )

        module_name = filename[:-3]

        spec = importlib.util.spec_from_file_location(
            module_name,
            path
        )

        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(
            spec
        )

        spec.loader.exec_module(module)

        if hasattr(module, "run"):
            pages.append(module)

    return pages


def now_wib():

    return datetime.now(
        WIB
    )


def get_next_run():

    now = now_wib()

    next_run = now.replace(
        hour=1,
        minute=10,
        second=0,
        microsecond=0
    )

    while next_run <= now:

        next_run += timedelta(
            hours=2
        )

    return next_run



def wait_until_next_run():

    next_run = get_next_run()

    while True:

        now = now_wib()

        remaining = (
            next_run - now
        ).total_seconds()

        if remaining <= 0:
            break

        print(
            f"Next run: "
            f"{next_run.strftime('%d-%m-%Y %H:%M:%S WIB')} | "
            f"Current: "
            f"{now.strftime('%d-%m-%Y %H:%M:%S WIB')} | "
            f"Waiting: "
            f"{int(remaining)} seconds",
            end="\r",
            flush=True
        )

        time.sleep(
            min(remaining, 30)
        )

    print()


def run_pages(pages):

    print("------------------------------------------")
    print(
        f"Starting page execution at "
        f"{now_wib().strftime('%d-%m-%Y %H:%M:%S WIB')}"
    )

    for page in pages:

        page_name = getattr(
            page,
            "PAGE_NAME",
            page.__name__
        )

        print(
            f"Running: {page_name}"
        )

        try:

            page.run()

            print(
                f"[{page_name}] "
                f"Completed"
            )

        except Exception as error:

            print(
                f"[{page_name}] "
                f"ERROR: {error}"
            )

    print("------------------------------------------")
    print("All pages completed.")

# ORCHESTRATOR

def main():

    print("==========================================")
    print("DC Autonomous Telkometra")
    print("==========================================")

    print(
        f"Timezone: GMT+7 / WIB"
    )

    print(
        f"Current time: "
        f"{now_wib().strftime('%d-%m-%Y %H:%M:%S WIB')}"
    )

    pages = load_pages()

    print(
        f"Loaded {len(pages)} page(s)"
    )

    if not pages:

        print(
            "Tidak ada page yang memiliki fungsi run()."
        )

        return

    print(
        "Schedule: "
        "01:10, 03:10, 05:10, ..., 23:10 WIB"
    )

    while True:

        wait_until_next_run()

        current_time = now_wib()

        print(
            "=========================================="
        )

        print(
            f"Scheduled run: "
            f"{current_time.strftime('%d-%m-%Y %H:%M:%S WIB')}"
        )

        print(
            "=========================================="
        )

        run_pages(pages)

if __name__ == "__main__":
    main()

# import os
# import time
# import importlib.util

# from dotenv import load_dotenv

# load_dotenv()

# SCREENSHOT_INTERVAL = int(
#     os.getenv("SCREENSHOT_INTERVAL", "3600")
# )

# # =========================================================
# # LOAD PAGE
# # =========================================================

# def load_pages():

#     pages = []

#     page_directory = "page"

#     for filename in os.listdir(page_directory):

#         if not filename.endswith(".py"):
#             continue

#         if filename == "__init__.py":
#             continue

#         path = os.path.join(
#             page_directory,
#             filename
#         )

#         module_name = filename[:-3]

#         spec = importlib.util.spec_from_file_location(
#             module_name,
#             path
#         )

#         if spec is None or spec.loader is None:
#             continue

#         module = importlib.util.module_from_spec(spec)

#         spec.loader.exec_module(module)

#         if hasattr(module, "run"):
#             pages.append(module)

#     return pages


# # =========================================================
# # ORCHESTRATOR
# # =========================================================

# def main():

#     print("==========================================")
#     print("DC Autonomous Telkometra")
#     print("==========================================")

#     pages = load_pages()

#     print(
#         f"Loaded {len(pages)} page(s)"
#     )

#     while True:

#         print("------------------------------------------")
#         print("Starting page execution...")

#         for page in pages:

#             page_name = getattr(
#                 page,
#                 "PAGE_NAME",
#                 page.__name__
#             )

#             print(
#                 f"Running: {page_name}"
#             )

#             try:

#                 page.run()

#             except Exception as error:

#                 print(
#                     f"[{page_name}] "
#                     f"ERROR: {error}"
#                 )

#         print("------------------------------------------")
#         print(
#             f"All pages completed. "
#             f"Waiting {SCREENSHOT_INTERVAL} seconds..."
#         )

#         time.sleep(
#             SCREENSHOT_INTERVAL
#         )


# if __name__ == "__main__":
#     main()