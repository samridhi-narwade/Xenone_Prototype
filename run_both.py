import subprocess, sys, time

procs = [
    subprocess.Popen([sys.executable, "xenone_discord_bot.py"]),
    subprocess.Popen([sys.executable, "xenone_slack_bot.py"]),
]

# Keep alive + restart if either crashes
while True:
    for i, p in enumerate(procs):
        if p.poll() is not None:  # process died
            name = "discord" if i == 0 else "slack"
            print(f"⚠️ {name} bot crashed — restarting...")
            procs[i] = subprocess.Popen([sys.executable,
                f"xenone_{name}_bot.py"])
    time.sleep(10)
