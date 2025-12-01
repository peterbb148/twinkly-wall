#!/usr/bin/env bash
set -euo pipefail

echo ">>> Reverting Twinkly AP setup..."

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

restore_file() {
  local target="$1"
  local backup="${target}.twinkly.bak"

  if [ -f "$backup" ]; then
    echo "Restoring $target from $backup"
    cp "$backup" "$target"
  else
    echo "No backup found for $target (expected $backup), skipping."
  fi
}

# 1) Stop services first
echo "Stopping hostapd and dnsmasq..."
systemctl stop hostapd || true
systemctl stop dnsmasq || true

# 2) Restore config files
restore_file "/etc/dhcpcd.conf"
restore_file "/etc/dnsmasq.conf"
restore_file "/etc/default/hostapd"

# Optionally remove hostapd.conf if you only used it for Twinkly.
# Comment this out if you want to keep it.
if [ -f "/etc/hostapd/hostapd.conf" ]; then
  echo "Removing /etc/hostapd/hostapd.conf (Twinkly AP config)"
  rm /etc/hostapd/hostapd.conf
fi

# 3) Disable services so they don't start on boot
echo "Disabling hostapd and dnsmasq..."
systemctl disable hostapd || true
systemctl disable dnsmasq || true

# 4) Restart networking (dhcpcd) so wlan0 returns to normal behaviour
echo "Restarting dhcpcd..."
systemctl restart dhcpcd || true

echo ">>> Revert complete."
echo "If you had wlan0 on a normal Wi-Fi network before, you may need to:"
echo "  - Reboot the Pi: sudo reboot"
echo "  - Or reconfigure Wi-Fi via raspi-config / GUI as needed."