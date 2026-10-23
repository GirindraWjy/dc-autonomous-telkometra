
import os
import time
import importlib.util
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

WIB = timezone(timedelta(hours=7))

RETRY_INTERVAL = timedelta(minutes=10)
CHECK_INTERVAL = 5  


def now_wib():
    return datetime.now(WIB)


def load_modules():
    modules = []

    for directory in ["page", "server"]:
        if not os.path.exists(directory):
            continue

        for filename in sorted(os.listdir(directory)):
            if not filename.endswith(".py"):
                continue

            if filename == "__init__.py":
                continue

            path = os.path.join(directory, filename)
            module_name = f"{directory}_{filename[:-3]}"

            spec = importlib.util.spec_from_file_location(
                module_name, path
            )

            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if callable(getattr(module, "run", None)):
                modules.append(module)

    return modules


def get_next_run():
    now = now_wib()

    next_run = now.replace(
        hour=1,
        minute=10,
        second=0,
        microsecond=0
    )

    while next_run <= now:
        next_run += timedelta(hours=2)

    return next_run


def get_page_name(page):
    return getattr(page, "PAGE_NAME", page.__name__)


def run_pages(pages, report_time, is_retry=False):
    failed_pages = []

    label = "RETRY" if is_retry else "SCHEDULED"

    print("-" * 50)
    print(f"[{label}] Report: {report_time:%d-%m-%Y %H:%M WIB}")

    for page in pages:
        name = get_page_name(page)

        print(f"Running: {name}")

        try:
            result = page.run()

            if result is False:
                raise RuntimeError(
                    "Page mengembalikan status gagal (False)"
                )

            print(f"[{name}] SUCCESS")

        except Exception as error:
            print(f"[{name}] FAILED: {error}")
            failed_pages.append(page)

    if failed_pages:
        print(
            f"{len(failed_pages)} page(s) gagal. "
            f"Akan dicoba ulang dalam {RETRY_INTERVAL}."
        )
    else:
        print(
            f"Semua page berhasil untuk laporan "
            f"{report_time:%H:%M WIB}."
        )

    print("-" * 50)

    return failed_pages


def main():
    print("=" * 50)
    print("DC Autonomous Telkometra")
    print(f"Timezone: WIB (UTC+7)")
    print(f"Current time: {now_wib():%d-%m-%Y %H:%M:%S WIB}")
    print("=" * 50)

    pages = load_modules()
    print(f"Loaded {len(pages)} page(s)")

    if not pages:
        print("Tidak ada module dengan fungsi run().")
        return

    print("Schedule: 01:10, 03:10, ..., 23:10 WIB")
    print("Retry interval: setiap 10 menit jika gagal")

    next_run = get_next_run()

    pending_retries = []

    while True:
        now = now_wib()

        due_retries = [
            item for item in pending_retries
            if item["retry_at"] <= now
        ]

        pending_retries = [
            item for item in pending_retries
            if item["retry_at"] > now
        ]

        for item in due_retries:
            failed_pages = run_pages(
                item["pages"],
                item["report_time"],
                is_retry=True
            )

            if failed_pages:
                pending_retries.append({
                    "report_time": item["report_time"],
                    "pages": failed_pages,
                    "retry_at": now_wib() + RETRY_INTERVAL
                })
            else:
                print(
                    f"[RECOVERED] Laporan "
                    f"{item['report_time']:%H:%M WIB} berhasil."
                )

        now = now_wib()

        if now >= next_run:
            scheduled_time = next_run

            next_run += timedelta(hours=2)

            while next_run <= now:
                next_run += timedelta(hours=2)

            failed_pages = run_pages(
                pages,
                scheduled_time
            )

            if failed_pages:
                pending_retries.append({
                    "report_time": scheduled_time,
                    "pages": failed_pages,
                    "retry_at": now_wib() + RETRY_INTERVAL
                })

        now = now_wib()

        print(
            f"\rNext scheduled: {next_run:%d-%m %H:%M WIB} | "
            f"Pending retry: {len(pending_retries)}",
            end="",
            flush=True
        )

        time.sleep(CHECK_INTERVAL)


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

# def load_modules():

#     modules = []

#     directories = [
#         "page",
#         "server"
#     ]

#     for directory in directories:

#         if not os.path.exists(directory):
#             continue

#         for filename in os.listdir(directory):

#             if not filename.endswith(".py"):
#                 continue

#             if filename == "__init__.py":
#                 continue

#             path = os.path.join(
#                 directory,
#                 filename
#             )

#             module_name = (
#                 f"{directory}_{filename[:-3]}"
#             )

#             spec = importlib.util.spec_from_file_location(
#                 module_name,
#                 path
#             )

#             if spec is None or spec.loader is None:
#                 continue

#             module = importlib.util.module_from_spec(
#                 spec
#             )

#             spec.loader.exec_module(module)

#             if hasattr(module, "run"):

#                 modules.append(module)

#     return modules


# # =========================================================
# # ORCHESTRATOR
# # =========================================================

# def main():

#     print("==========================================")
#     print("DC Autonomous Telkometra")
#     print("==========================================")

#     pages = load_modules()

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