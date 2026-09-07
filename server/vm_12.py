import os
import re
import requests
import paramiko

from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from core.server_ss_template import render_terminal


PAGE_NAME = "Server 12"

HOST = "192.168.120.12"

COMMANDS = [
    'mysql -e "SHOW REPLICA STATUS\\G"',
    "ps -efww | grep report",
    "df -h",
    "date",
]

WIB = timezone(
    timedelta(hours=7)
)


def get_cpu_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "top -bn1 | grep 'Cpu(s)'"
    )

    output = (
        stdout.read()
        .decode("utf-8", errors="replace")
    )

    match = re.search(
        r"([\d.,]+)\s*id",
        output
    )

    if not match:
        return None

    idle = float(
        match.group(1).replace(",", ".")
    )

    return round(100 - idle, 1)


def get_ram_usage(ssh):
    _, stdout, _ = ssh.exec_command(
        "free | awk '/Mem:/ {printf \"%.1f\", ($3/$2)*100}'"
    )

    output = (
        stdout.read()
        .decode("utf-8", errors="replace")
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
        .decode("utf-8", errors="replace")
        .strip()
    )

    try:
        return float(output)
    except ValueError:
        return None

def get_root_causes(cpu, ram, disk):
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

    if not causes:
        causes.append(
            "No critical resource detected"
        )

    return causes


def determine_status(cpu, ram, disk):
    usages = [cpu, ram, disk]

    if any(
        value is not None and value > 80
        for value in usages
    ):
        return "CRITICAL 🔴"

    return "HEALTHY 🟢"


def format_usage(name, value):
    if value is None:
        return f"{name}: N/A"

    return f"{name}: {value:.1f}%"


def run():
    load_dotenv()

    username = os.getenv(
        "USN_SERVER_12"
    )

    password = os.getenv(
        "PW_SERVER_12"
    )

    webhook_url = os.getenv(
        "DISCORD_WEBHOOK_URL"
    )

    if not username:
        raise ValueError(
            "USN_SERVER_12 belum ditemukan di .env"
        )

    if not password:
        raise ValueError(
            "PW_SERVER_12 belum ditemukan di .env"
        )

    if not webhook_url:
        raise ValueError(
            "DISCORD_WEBHOOK_URL belum ditemukan di .env"
        )

    screenshot_path = "server12.png"

    ssh = paramiko.SSHClient()

    ssh.set_missing_host_key_policy(
        paramiko.AutoAddPolicy()
    )

    output_sections = []

    try:
        print(
            f"[{PAGE_NAME}] Connecting to {HOST}..."
        )

        ssh.connect(
            hostname=HOST,
            username=username,
            password=password,
            timeout=15,
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

            stdin, stdout, stderr = (
                ssh.exec_command(
                    command,
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
                stdout.channel
                .recv_exit_status()
            )

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

        cpu_usage = get_cpu_usage(ssh)
        ram_usage = get_ram_usage(ssh)
        disk_usage = get_disk_usage(ssh)

        print(
            f"[{PAGE_NAME}] CPU: {cpu_usage}%"
        )

        print(
            f"[{PAGE_NAME}] RAM: {ram_usage}%"
        )

        print(
            f"[{PAGE_NAME}] Disk: {disk_usage}%"
        )

        status = determine_status(
            cpu=cpu_usage,
            ram=ram_usage,
            disk=disk_usage
        )

        root_causes = get_root_causes(
            cpu=cpu_usage,
            ram=ram_usage,
            disk=disk_usage
        )

        checked_at = datetime.now(
            WIB
        ).strftime(
            "%d %b %Y %H:%M WIB"
        )

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
            f"Status: {status}"
        )

        if status == "CRITICAL":
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

        discord_content = (
            f"🖥️ **{PAGE_NAME}**\n"
            f"Status: **{status}**\n"
            f"{format_usage('CPU Usage', cpu_usage)}\n"
            f"{format_usage('RAM Usage', ram_usage)}\n"
            f"{format_usage('Disk Usage', disk_usage)}\n"
        )

        if status == "CRITICAL 🔴":
            discord_content += (
                f"Root Cause: **{'; '.join(root_causes)}**\n"
            )

        discord_content += (
            f"Checked: {checked_at}"
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