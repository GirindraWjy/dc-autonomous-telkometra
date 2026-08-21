from core.ss_template import run_page

PAGE_NAME = "dashboard - all"

URL = "https://cpdashboard.metratv.co.id:8003/#/dashboard-all"


def run():
    run_page(
        page_name=PAGE_NAME,
        url=URL,
        wait_after_load=5000
    )