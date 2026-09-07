import os
import re
import requests
import paramiko

from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

from core.server_ss_template import render_terminal


PAGE_NAME = "Server 8"

HOST = "192.168.120.8"

CURRENT_DIRECTORY = (
    "ulo_commercial/"
    "be-dashboard-cp-platform-backup/"
    "logs"
)

COMMANDS = [
    "cd ulo_commercial/be-dashboard-cp-platform-backup/logs/",
    'journalctl -u daemon_clean_database.service --since "2 hours ago" --no-pager | grep "trx_id" | tail -n 10',
    "ll",
    "df -h",
    "netstat -tnlp",
    "ps ax | grep clean",
    "date",
]

WIB = timezone(
    timedelta(hours=7)
)


def get_last_transaction(ssh):
    _, stdout, _ = ssh.exec_command(
        'journalctl -u daemon_clean_database.service --since "24 hours ago" --no-pager | grep "trx_id" | tail -n 1'
    )

    output = (
        stdout.read()
        .decode(
            "utf-8",
            errors="replace"
        )
        .strip()
    )

    if not output:
        return None

    match = re.search(
        r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",
        output
    )

    if not match:
        return None

    timestamp = datetime.strptime(
        match.group(0),
        "%b %d %H:%M:%S"
    ).replace(
        year=datetime.now(WIB).year,
        tzinfo=WIB
    )

    return timestamp


def get_cpu_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "top -bn1 | grep 'Cpu(s)'"
    )

    output = (
        stdout.read()
        .decode(
            "utf-8",
            errors="replace"
        )
    )

    match = re.search(
        r"([\d.,]+)\s*id",
        output
    )

    if not match:
        return None

    idle = float(
        match.group(1).replace(
            ",",
            "."
        )
    )

    return round(
        100 - idle,
        1
    )


def get_ram_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "free | awk '/Mem:/ {printf \"%.1f\", ($3/$2)*100}'"
    )

    output = (
        stdout.read()
        .decode(
            "utf-8",
            errors="replace"
        )
        .strip()
    )

    try:
        return float(output)

    except ValueError:
        return None


def get_disk_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "df -P / | awk 'NR==2 {gsub(/%/,\"\",$5); print $5}'"
    )

    output = (
        stdout.read()
        .decode(
            "utf-8",
            errors="replace"
        )
        .strip()
    )

    try:
        return float(output)

    except ValueError:
        return None


def get_root_causes(
    cpu,
    ram,
    disk,
    last_transaction
):
    causes = []

    if cpu is not None and cpu > 80:
        causes.append(
            f"CPU Usage is above 80% ({cpu:.1f}%)"
        )

    if ram is not None and ram > 80:
        causes.append(
            f"RAM Usage is above 80% ({ram:.1f}%)"
        )

    if disk is not None and disk > 80:
        causes.append(
            f"Disk Usage is above 80% ({disk:.1f}%)"
        )

    if last_transaction is None:
        causes.append(
            "Last transaction could not be found"
        )

    else:
        now = datetime.now(WIB)

        transaction_age = (
            now - last_transaction
        )

        if transaction_age > timedelta(
            hours=3
        ):
            total_minutes = int(
                transaction_age.total_seconds()
                / 60
            )

            hours = total_minutes // 60
            minutes = total_minutes % 60

            causes.append(
                "Last transaction is more than "
                f"3 hours old ({hours}h {minutes}m)"
            )

    return causes


def determine_status(
    root_causes
):
    if root_causes:
        return "CRITICAL 🔴"

    return "HEALTHY 🟢"


def format_usage(
    name,
    value
):
    if value is None:
        return f"{name}: N/A"

    if value > 80:
        return (
            f"{name}: {value:.1f}% 🔴"
        )

    return (
        f"{name}: {value:.1f}%"
    )


def run():
    load_dotenv()

    username = os.getenv(
        "USN_SERVER_8"
    )

    password = os.getenv(
        "PW_SERVER_8"
    )

    webhook_url = os.getenv(
        "DISCORD_WEBHOOK_URL"
    )

    if not username:
        raise ValueError(
            "USN_SERVER_8 belum ditemukan di .env"
        )

    if not password:
        raise ValueError(
            "PW_SERVER_8 belum ditemukan di .env"
        )

    if not webhook_url:
        raise ValueError(
            "DISCORD_WEBHOOK_URL belum ditemukan di .env"
        )

    screenshot_path = "server8.png"

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    output_sections = []

    journal_output = ""

    try:
        print(
            f"[{PAGE_NAME}] "
            f"Connecting to {HOST}..."
        )

        ssh.connect(
            hostname=HOST,
            username=username,
            password=password,
            timeout=15
        )

        print(
            f"[{PAGE_NAME}] Connected"
        )

        for index, command in enumerate(
            COMMANDS,
            start=1
        ):
            print(
                f"[{PAGE_NAME}] "
                f"Running command {index}: "
                f"{command}"
            )

            if command.startswith(
                "cd "
            ):
                full_command = (
                    f"cd {command[3:]} && pwd"
                )

            else:
                full_command = (
                    f"cd {CURRENT_DIRECTORY} "
                    f"&& {command}"
                )

            stdin, stdout, stderr = (
                ssh.exec_command(
                    full_command,
                    timeout=60
                )
            )

            stdout_text = (
                stdout.read()
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )

            stderr_text = (
                stderr.read()
                .decode(
                    "utf-8",
                    errors="replace"
                )
            )

            exit_code = (
                stdout.channel.recv_exit_status()
            )

            if "journalctl" in command:
                journal_output = stdout_text

            output_sections.append(
                f"$ {command}"
            )

            if stdout_text.strip():
                output_sections.append(
                    stdout_text.rstrip()
                )

            if stderr_text.strip():
                output_sections.append(
                    "[stderr]"
                )

                output_sections.append(
                    stderr_text.rstrip()
                )

            output_sections.append(
                f"[exit code: {exit_code}]"
            )

            output_sections.append("")

            print(
                f"[{PAGE_NAME}] "
                f"Command {index} completed "
                f"(exit code: {exit_code})"
            )

        print(
            f"[{PAGE_NAME}] "
            f"Checking server resources..."
        )

        cpu_usage = get_cpu_usage(
            ssh
        )

        ram_usage = get_ram_usage(
            ssh
        )

        disk_usage = get_disk_usage(
            ssh
        )

        last_transaction_dt = (
            get_last_transaction(
                ssh
            )
        )

        if last_transaction_dt:
            last_transaction = (
                last_transaction_dt.strftime(
                    "%b %d %H:%M:%S"
                )
            )

        else:
            last_transaction = (
                "No transaction found"
            )

        print(
            f"[{PAGE_NAME}] "
            f"CPU: {cpu_usage}%"
        )

        print(
            f"[{PAGE_NAME}] "
            f"RAM: {ram_usage}%"
        )

        print(
            f"[{PAGE_NAME}] "
            f"Disk: {disk_usage}%"
        )

        print(
            f"[{PAGE_NAME}] "
            f"Last transaction: "
            f"{last_transaction}"
        )

        root_causes = get_root_causes(
            cpu=cpu_usage,
            ram=ram_usage,
            disk=disk_usage,
            last_transaction=last_transaction_dt
        )

        status = determine_status(
            root_causes
        )

        print(
            f"[{PAGE_NAME}] "
            f"Status: {status}"
        )

        if root_causes:
            print(
                f"[{PAGE_NAME}] "
                f"Root causes:"
            )

            for cause in root_causes:
                print(
                    f"  - {cause}"
                )

        checked_at = datetime.now(
            WIB
        ).strftime(
            "%d %b %Y %H:%M WIB"
        )

        output_sections.append("")

        output_sections.append(
            "----------------------------------------"
        )

        output_sections.append(
            "SERVER HEALTH"
        )

        output_sections.append(
            format_usage(
                "CPU Usage",
                cpu_usage
            )
        )

        output_sections.append(
            format_usage(
                "RAM Usage",
                ram_usage
            )
        )

        output_sections.append(
            format_usage(
                "Disk Usage",
                disk_usage
            )
        )

        output_sections.append(
            f"Last Transaction: "
            f"{last_transaction}"
        )

        output_sections.append(
            f"Status: {status}"
        )

        if status.startswith(
            "CRITICAL"
        ):
            output_sections.append(
                "CRITICAL ROOT CAUSE"
            )

            for cause in root_causes:
                output_sections.append(
                    f"- {cause}"
                )

        output_sections.append(
            f"Checked: {checked_at}"
        )

        terminal_output = "\n".join(
            output_sections
        )

        render_terminal(
            title=PAGE_NAME,
            host=HOST,
            output=terminal_output,
            output_path=screenshot_path
        )

        print(
            f"[{PAGE_NAME}] "
            f"Screenshot created"
        )

        discord_content = (
            f"🖥️ **{PAGE_NAME}**\n"
            f"Status: **{status}**\n"
            f"Last Transaction: **{last_transaction}**\n"
            f"{format_usage('CPU Usage', cpu_usage)}\n"
            f"{format_usage('RAM Usage', ram_usage)}\n"
            f"{format_usage('Disk Usage', disk_usage)}\n"
        )

        if status.startswith(
            "CRITICAL"
        ):
            discord_content += (
                f"Critical Root Cause: **"
                f"{'; '.join(root_causes)}**\n"
            )

        discord_content += (
            f"Checked: {checked_at}"
        )

        print(
            f"[{PAGE_NAME}] "
            f"Sending screenshot to Discord..."
        )

        with open(
            screenshot_path,
            "rb"
        ) as image:

            response = requests.post(
                webhook_url,
                data={
                    "content": discord_content
                },
                files={
                    "file": (
                        screenshot_path,
                        image,
                        "image/png"
                    )
                },
                timeout=120
            )

        if response.status_code not in (
            200,
            204
        ):
            raise Exception(
                f"Discord error: "
                f"{response.status_code} "
                f"{response.text}"
            )

        print(
            f"[{PAGE_NAME}] "
            f"Screenshot sent to Discord"
        )

    except Exception as error:

        print(
            f"[{PAGE_NAME}] ERROR: "
            f"{error}"
        )

        raise

    finally:

        try:
            ssh.close()

        except Exception:
            pass

        if os.path.exists(
            screenshot_path
        ):
            os.remove(
                screenshot_path
            )

        print(
            f"[{PAGE_NAME}] "
            f"SSH connection closed"
        )


if __name__ == "__main__":
    run()