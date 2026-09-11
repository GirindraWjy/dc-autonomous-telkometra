from datetime import datetime, timedelta


# ============================================================
# SSH COMMAND HELPER
# ============================================================

def _run_diagnostic(
    ssh,
    command,
    timeout=60,
):
    """
    Menjalankan diagnostic command melalui SSH.

    Return:
        {
            "command": str,
            "output": str,
            "stderr": str,
            "exit_code": int,
        }
    """

    try:
        stdin, stdout, stderr = ssh.exec_command(
            command,
            timeout=timeout,
        )

        output = (
            stdout
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
            .strip()
        )

        error = (
            stderr
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
            .strip()
        )

        exit_code = (
            stdout.channel.recv_exit_status()
        )

        return {
            "command": command,
            "output": output,
            "stderr": error,
            "exit_code": exit_code,
        }

    except Exception as exc:
        return {
            "command": command,
            "output": "",
            "stderr": str(exc),
            "exit_code": -1,
        }


# ============================================================
# SAFE SHELL PATH
# ============================================================

def _shell_quote(value):
    """
    Quote path agar aman dimasukkan ke command shell.
    """

    return "'" + value.replace(
        "'",
        "'\\''",
    ) + "'"


# ============================================================
# HUMAN READABLE BYTES
# ============================================================

def _human_bytes(value):
    """
    Convert bytes -> KB/MB/GB/TB.
    """

    try:
        value = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return "Unknown"

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    for unit in units:

        if abs(value) < 1024:
            return f"{value:.1f} {unit}"

        value /= 1024

    return f"{value:.1f} PB"


# ============================================================
# DISK DIAGNOSTIC
# ============================================================

def _find_disk_root_cause(ssh):
    """
    Diagnostic disk:

    1. Cari filesystem yang >= 80%
    2. Cari mount point
    3. Cari directory terbesar
    4. Cari file terbesar
    5. Cari deleted file yang masih dibuka process
    """

    diagnostics = {
        "partitions": [],
        "largest_directories": [],
        "largest_files": [],
        "deleted_open_files": [],
    }

    # ========================================================
    # 1. PARTITIONS
    # ========================================================

    df_result = _run_diagnostic(
        ssh,
        "df -hP",
        timeout=30,
    )

    if df_result["exit_code"] != 0:

        diagnostics["error"] = (
            "Failed to inspect filesystem: "
            + (
                df_result["stderr"]
                or f"exit code {df_result['exit_code']}"
            )
        )

        return diagnostics

    lines = (
        df_result["output"]
        .splitlines()
    )

    # ========================================================
    # Parse df
    # ========================================================

    for line in lines[1:]:

        parts = line.split()

        if len(parts) < 6:
            continue

        filesystem = parts[0]
        size = parts[1]
        used = parts[2]
        available = parts[3]
        usage = parts[4]
        mount = parts[5]

        try:
            usage_percent = int(
                usage.rstrip("%")
            )
        except ValueError:
            continue

        # Pseudo filesystem jangan dianggap root cause
        if filesystem.startswith(
            (
                "tmpfs",
                "devtmpfs",
                "udev",
                "overlay",
            )
        ):
            continue

        if usage_percent >= 80:

            diagnostics["partitions"].append(
                {
                    "filesystem": filesystem,
                    "size": size,
                    "used": used,
                    "available": available,
                    "usage": usage_percent,
                    "mount": mount,
                }
            )

    if not diagnostics["partitions"]:
        return diagnostics

    # ========================================================
    # 2. ANALYZE EACH FULL PARTITION
    # ========================================================

    for partition in diagnostics["partitions"]:

        mount = partition["mount"]
        safe_mount = _shell_quote(mount)

        # ====================================================
        # Largest directories
        # ====================================================

        dir_command = (
            f"du -xhd1 {safe_mount} "
            "2>/dev/null "
            "| sort -hr "
            "| head -n 10"
        )

        dir_result = _run_diagnostic(
            ssh,
            dir_command,
            timeout=120,
        )

        directories = []

        if dir_result["exit_code"] == 0:

            for line in (
                dir_result["output"]
                .splitlines()
            ):

                line = line.strip()

                if not line:
                    continue

                parts = line.split(
                    maxsplit=1
                )

                if len(parts) != 2:
                    continue

                size = parts[0]
                path = parts[1]

                directories.append(
                    {
                        "size": size,
                        "path": path,
                    }
                )

        diagnostics[
            "largest_directories"
        ].append(
            {
                "mount": mount,
                "directories": directories,
            }
        )

        # ====================================================
        # Largest files
        # ====================================================

        file_command = (
            f"find {safe_mount} "
            "-xdev "
            "-type f "
            "-printf '%s %p\\n' "
            "2>/dev/null "
            "| sort -nr "
            "| head -n 10"
        )

        file_result = _run_diagnostic(
            ssh,
            file_command,
            timeout=180,
        )

        files = []

        if file_result["exit_code"] == 0:

            for line in (
                file_result["output"]
                .splitlines()
            ):

                line = line.strip()

                if not line:
                    continue

                parts = line.split(
                    maxsplit=1
                )

                if len(parts) != 2:
                    continue

                try:
                    size_bytes = int(
                        parts[0]
                    )
                except ValueError:
                    continue

                path = parts[1]

                files.append(
                    {
                        "size_bytes": size_bytes,
                        "size": _human_bytes(
                            size_bytes
                        ),
                        "path": path,
                    }
                )

        diagnostics[
            "largest_files"
        ].append(
            {
                "mount": mount,
                "files": files,
            }
        )

        # ====================================================
        # Deleted files still held open
        # ====================================================

        deleted_command = (
            "lsof +L1 "
            "2>/dev/null "
            "| head -n 20"
        )

        deleted_result = _run_diagnostic(
            ssh,
            deleted_command,
            timeout=60,
        )

        if deleted_result["output"]:

            diagnostics[
                "deleted_open_files"
            ].append(
                {
                    "mount": mount,
                    "output": (
                        deleted_result["output"]
                    ),
                }
            )

    return diagnostics


# ============================================================
# CPU DIAGNOSTIC
# ============================================================

def _find_cpu_root_cause(ssh):
    """
    Cari process dengan CPU consumption tertinggi.
    """

    result = _run_diagnostic(
        ssh,
        (
            "ps -eo "
            "pid,ppid,user,%cpu,%mem,etime,args "
            "--sort=-%cpu "
            "| head -n 11"
        ),
        timeout=30,
    )

    if result["exit_code"] != 0:

        return {
            "error": (
                "Failed to inspect CPU processes: "
                + (
                    result["stderr"]
                    or f"exit code {result['exit_code']}"
                )
            )
        }

    return {
        "processes": result["output"],
    }


# ============================================================
# RAM DIAGNOSTIC
# ============================================================

def _find_ram_root_cause(ssh):
    """
    Cari process dengan RAM consumption tertinggi.
    """

    result = _run_diagnostic(
        ssh,
        (
            "ps -eo "
            "pid,ppid,user,%cpu,%mem,etime,args "
            "--sort=-%mem "
            "| head -n 11"
        ),
        timeout=30,
    )

    if result["exit_code"] != 0:

        return {
            "error": (
                "Failed to inspect RAM processes: "
                + (
                    result["stderr"]
                    or f"exit code {result['exit_code']}"
                )
            )
        }

    return {
        "processes": result["output"],
    }


# ============================================================
# MAIN ANALYZER
# ============================================================

def analyze(
    cpu=None,
    ram=None,
    disk=None,
    last_transaction=None,
    command_results=None,
    check_transaction=True,
    ssh=None,
):
    """
    Shared infrastructure root cause analyzer.

    ssh diberikan agar analyzer dapat melakukan
    diagnostic lebih dalam ketika metric abnormal.
    """

    root_causes = []
    diagnostics = {}

    if command_results is None:
        command_results = []

    # ========================================================
    # CPU
    # ========================================================

    if cpu is not None and cpu > 80:

        root_causes.append(
            f"CPU Usage is above 80% ({cpu:.1f}%)"
        )

        if ssh is not None:

            diagnostics["cpu"] = (
                _find_cpu_root_cause(ssh)
            )

    # ========================================================
    # RAM
    # ========================================================

    if ram is not None and ram > 80:

        root_causes.append(
            f"RAM Usage is above 80% ({ram:.1f}%)"
        )

        if ssh is not None:

            diagnostics["ram"] = (
                _find_ram_root_cause(ssh)
            )

    # ========================================================
    # DISK
    # ========================================================

    if disk is not None and disk > 80:

        root_causes.append(
            f"Disk Usage is above 80% ({disk:.1f}%)"
        )

        if ssh is not None:

            diagnostics["disk"] = (
                _find_disk_root_cause(ssh)
            )

    # ========================================================
    # LAST TRANSACTION
    # ========================================================

    if check_transaction:

        if last_transaction is None:

            root_causes.append(
                "Last transaction could not be found"
            )

        else:

            now = datetime.now(
                last_transaction.tzinfo
            )

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

                hours = (
                    total_minutes // 60
                )

                minutes = (
                    total_minutes % 60
                )

                root_causes.append(
                    "Last transaction is more than "
                    f"3 hours old ({hours}h {minutes}m)"
                )

    # ========================================================
    # COMMAND ERRORS
    # ========================================================

    for result in command_results:

        command = result.get(
            "command",
            "Unknown command",
        )

        exit_code = result.get(
            "exit_code",
            0,
        )

        stderr = result.get(
            "stderr",
            "",
        ).strip()

        if exit_code != 0:

            if stderr:

                root_causes.append(
                    f"Command failed: {command} "
                    f"({stderr[:200]})"
                )

            else:

                root_causes.append(
                    f"Command failed: {command} "
                    f"(exit code {exit_code})"
                )

    # ========================================================
    # STATUS
    # ========================================================

    if root_causes:
        status = "CRITICAL 🔴"
    else:
        status = "HEALTHY 🟢"

    return {
        "status": status,
        "root_causes": root_causes,
        "diagnostics": diagnostics,
    }


# ============================================================
# FORMAT DIAGNOSTIC FOR DISCORD / SCREENSHOT
# ============================================================

def format_diagnostics(
    diagnostics,
    max_lines=20,
):
    """
    Convert diagnostics dictionary menjadi text.
    """

    if not diagnostics:
        return ""

    lines = []

    # ========================================================
    # CPU
    # ========================================================

    cpu = diagnostics.get(
        "cpu"
    )

    if cpu:

        lines.append(
            "CPU DIAGNOSTIC"
        )

        if cpu.get("error"):

            lines.append(
                f"ERROR: {cpu['error']}"
            )

        else:

            processes = cpu.get(
                "processes",
                "",
            )

            if processes:

                lines.extend(
                    processes.splitlines()
                )

        lines.append("")

    # ========================================================
    # RAM
    # ========================================================

    ram = diagnostics.get(
        "ram"
    )

    if ram:

        lines.append(
            "RAM DIAGNOSTIC"
        )

        if ram.get("error"):

            lines.append(
                f"ERROR: {ram['error']}"
            )

        else:

            processes = ram.get(
                "processes",
                "",
            )

            if processes:

                lines.extend(
                    processes.splitlines()
                )

        lines.append("")

    # ========================================================
    # DISK
    # ========================================================

    disk = diagnostics.get(
        "disk"
    )

    if disk:

        lines.append(
            "DISK DIAGNOSTIC"
        )

        # ----------------------------------------------------
        # Partitions
        # ----------------------------------------------------

        for partition in disk.get(
            "partitions",
            [],
        ):

            lines.append(
                "Partition: "
                f"{partition['filesystem']}"
            )

            lines.append(
                "Mount: "
                f"{partition['mount']}"
            )

            lines.append(
                "Usage: "
                f"{partition['usage']}%"
            )

            lines.append(
                "Size: "
                f"{partition['size']} | "
                f"Used: {partition['used']} | "
                f"Available: "
                f"{partition['available']}"
            )

        # ----------------------------------------------------
        # Directories
        # ----------------------------------------------------

        for item in disk.get(
            "largest_directories",
            [],
        ):

            mount = item.get(
                "mount",
                "/",
            )

            lines.append(
                f"Largest directories ({mount}):"
            )

            for directory in item.get(
                "directories",
                [],
            )[:5]:

                lines.append(
                    f"- {directory['size']} "
                    f"{directory['path']}"
                )

        # ----------------------------------------------------
        # Files
        # ----------------------------------------------------

        for item in disk.get(
            "largest_files",
            [],
        ):

            mount = item.get(
                "mount",
                "/",
            )

            lines.append(
                f"Largest files ({mount}):"
            )

            for file_info in item.get(
                "files",
                [],
            )[:5]:

                lines.append(
                    f"- {file_info['size']} "
                    f"{file_info['path']}"
                )

        # ----------------------------------------------------
        # Deleted open files
        # ----------------------------------------------------

        deleted = disk.get(
            "deleted_open_files",
            [],
        )

        if deleted:

            lines.append(
                "Deleted files still held open:"
            )

            for item in deleted:

                output = item.get(
                    "output",
                    "",
                )

                if output:

                    lines.extend(
                        output.splitlines()[:8]
                    )

        lines.append("")

    # ========================================================
    # ERROR
    # ========================================================

    if diagnostics.get("error"):

        lines.append(
            f"ERROR: {diagnostics['error']}"
        )

    # ========================================================
    # LIMIT
    # ========================================================

    if len(lines) > max_lines:

        lines = (
            lines[:max_lines]
            + [
                "... diagnostic output truncated ..."
            ]
        )

    return "\n".join(lines).strip()