from core.ss_template import run_page


PAGE_NAME = "dashboard - Shortmax"

URL = "https://cpdashboard.metratv.co.id:8003/#/dashboard-all"


def select_shortmax(page):

    print(
        f"[{PAGE_NAME}] "
        f"Opening ShortMax selector..."
    )

    select_trigger = page.locator(
        "#hope-select-cl-2-trigger"
    )

    select_trigger.wait_for(
        state="visible",
        timeout=30000
    )

    select_trigger.click()

    print(
        f"[{PAGE_NAME}] "
        f"Selector opened"
    )

    print(
        f"[{PAGE_NAME}] "
        f"Selecting ShortMax..."
    )

    shortmax_option = page.locator(
        "#hope-select-cl-2-option-3"
    )

    shortmax_option.wait_for(
        state="visible",
        timeout=30000
    )

    shortmax_option.click()

    page.wait_for_timeout(
        1000
    )

    selected_value = page.locator(
        "#hope-select-cl-2-trigger .hope-select__value"
    )

    selected_text = (
        selected_value
        .inner_text()
        .strip()
    )

    print(
        f"[{PAGE_NAME}] "
        f"Selected value: {selected_text}"
    )

    if selected_text != "ShortMax":
        raise Exception(
            f"ShortMax gagal dipilih. "
            f"Current value: {selected_text}"
        )

    print(
        f"[{PAGE_NAME}] "
        f"ShortMax selected successfully"
    )

    print(
        f"[{PAGE_NAME}] "
        f"Waiting for dashboard update..."
    )

    page.wait_for_timeout(
        10000
    )


def run():

    run_page(
        page_name=PAGE_NAME,
        url=URL,
        wait_after_load=5000,
        before_screenshot=select_shortmax,
    )


if __name__ == "__main__":
    run()