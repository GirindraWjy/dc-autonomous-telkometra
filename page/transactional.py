from core.ss_template import run_page


PAGE_NAME = "dashboard - Transactional"

URL = "https://cpdashboard.metratv.co.id:8003/#/transactional"


def refresh_transactional(page):

    print(
        f"[{PAGE_NAME}] "
        f"Clicking Refresh..."
    )

    refresh_button = page.get_by_role(
        "button",
        name="Refresh",
        exact=True
    )

    refresh_button.wait_for(
        state="visible",
        timeout=30000
    )

    refresh_button.click()

    print(
        f"[{PAGE_NAME}] "
        f"Refresh clicked"
    )

    # Tunggu data selesai diperbarui
    page.wait_for_timeout(5000)

    print(
        f"[{PAGE_NAME}] "
        f"Transactional data refreshed"
    )


def run():

    run_page(
        page_name=PAGE_NAME,
        url=URL,
        wait_after_load=5000,
        before_screenshot=refresh_transactional
    )