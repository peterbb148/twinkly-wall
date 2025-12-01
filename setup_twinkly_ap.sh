#!/usr/bin/env bash
set -euo pipefail

### CONFIGURABLE VALUES ###
SSID="TwinklyNet"
PASSPHRASE="twinklypassword"
AP_IP="192.168.50.1"
DHCP_START="192.168.50.10"
DHCP_END="192.168.50.20"
NETMASK="255.255.255.0"

echo ">>> Twinkly AP setup starting..."

if [[ $EUID -ne 0 ]]; then
  echo "Please run as root: sudo $0"
  exit 1
fi

### 1. Ensure required packages exist (hostapd, dnsmasq) ###

need_pkg() {
  if ! dpkg -s "$1" >/dev/null 2>&1; then
    echo "Package $1 not installed."
    echo "Trying to install $1 (this requires internet; if offline, install manually later)."
    apt-get update && apt-get install -y "$1" || {
      echo "WARNING: could not install $1. Continue only if it is already present."
    }
  fi
}

need_pkg hostapd
need_pkg dnsmasq

systemctl stop hostapd || true
systemctl stop dnsmasq || true

### 2. Configure static IP for wlan0 via dhcpcd.conf ###

DHCPCD_CONF="/etc/dhcpcd.conf"

if ! grep -q "# Twinkly AP config" "$DHCPCD_CONF"; then
  echo "Backing up $DHCPCD_CONF to ${DHCPCD_CONF}.twinkly.bak"
  cp "$DHCPCD_CONF" "${DHCPCD_CONF}.twinkly.bak"

  cat <<EOF >> "$DHCPCD_CONF"

# Twinkly AP config
interface wlan0
    static ip_address=${AP_IP}/24
    nohook wpa_supplicant
EOF
else
  echo "$DHCPCD_CONF already contains Twinkly AP config; leaving as is."
fi

echo "Restarting dhcpcd..."
systemctl restart dhcpcd

### 3. Configure dnsmasq (DHCP server) ###

DNSMASQ_CONF="/etc/dnsmasq.conf"
if [ ! -f "${DNSMASQ_CONF}.twinkly.bak" ]; then
  echo "Backing up $DNSMASQ_CONF to ${DNSMASQ_CONF}.twinkly.bak"
  cp "$DNSMASQ_CONF" "${DNSMASQ_CONF}.twinkly.bak"
fi

cat <<EOF > "$DNSMASQ_CONF"
# Twinkly AP config
interface=wlan0
dhcp-range=${DHCP_START},${DHCP_END},${NETMASK},24h
EOF

### 4. Configure hostapd (Wi-Fi AP) ###

HOSTAPD_CONF="/etc/hostapd/hostapd.conf"
mkdir -p "$(dirname "$HOSTAPD_CONF")"

cat <<EOF > "$HOSTAPD_CONF"
interface=wlan0
ssid=${SSID}
hw_mode=g
channel=6
wmm_enabled=0
auth_algs=1
ignore_broadcast_ssid=0

wpa=2
wpa_passphrase=${PASSPHRASE}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

DEFAULT_HOSTAPD="/etc/default/hostapd"
if [ ! -f "${DEFAULT_HOSTAPD}.twinkly.bak" ]; then
  echo "Backing up $DEFAULT_HOSTAPD to ${DEFAULT_HOSTAPD}.twinkly.bak"
  cp "$DEFAULT_HOSTAPD" "${DEFAULT_HOSTAPD}.twinkly.bak"
fi

if grep -q "^DAEMON_CONF=" "$DEFAULT_HOSTAPD"; then
  sed -i "s|^DAEMON_CONF=.*|DAEMON_CONF=\"${HOSTAPD_CONF}\"|" "$DEFAULT_HOSTAPD"
else
  echo "DAEMON_CONF=\"${HOSTAPD_CONF}\"" >> "$DEFAULT_HOSTAPD"
fi

### 5. Enable and start services ###

echo "Enabling and starting hostapd + dnsmasq..."
systemctl unmask hostapd || true
systemctl enable hostapd
systemctl enable dnsmasq

systemctl restart hostapd
systemctl restart dnsmasq

### 6. Summary ###

echo ">>> Twinkly AP setup complete."
echo
echo "Wi-Fi SSID:     ${SSID}"
echo "Wi-Fi password: ${PASSPHRASE}"
echo "AP IP (wlan0):  ${AP_IP}"
echo
echo "Use your phone and Twinkly app to connect the Twinkly:"
echo "  1) Connect phone to ${SSID}"
echo "  2) In Twinkly app, give it the same SSID & password"
echo
echo "You can check wlan0 with: ip a show wlan0"
echo "You can check Twinkly using: arp -a  or  nmap -sn ${AP_IP%.*}.0/24 (if installed)"