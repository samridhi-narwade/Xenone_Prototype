# run.py
import subprocess, sys, time

print("🚀 Starting Xenone — Discord + Slack")

discord = subprocess.Popen([sys.executable, "xenone_discord_bot.py"])
slack   = subprocess.Popen([sys.executable, "xenone_slack_bot.py"])

# Keep alive + restart if either crashes
while True:
    if discord.poll() is not None:
        print("⚠️ Discord bot crashed — restarting")
        discord = subprocess.Popen([sys.executable, "xenone_discord_bot.py"])
    if slack.poll() is not None:
        print("⚠️ Slack bot crashed — restarting")
        slack = subprocess.Popen([sys.executable, "xenone_slack_bot.py"])
    time.sleep(10)
