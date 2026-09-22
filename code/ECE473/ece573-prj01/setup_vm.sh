#!/usr/bin/env bash
set -euo pipefail

readonly GO_VERSION="1.26.6"
readonly GO_AMD64_SHA256="708effb774be8237570d0add163225abbdfaf4fca28b2611df167beba4feef89"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run as root: sudo ./setup_vm.sh" >&2
  exit 1
fi

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "This script requires Ubuntu 24.04 LTS; found ${PRETTY_NAME:-unknown OS}." >&2
  exit 1
fi

case "$(dpkg --print-architecture)" in
  amd64)
    go_arch="amd64"
    go_sha256="$GO_AMD64_SHA256"
    ;;
  *)
    echo "This script supports only amd64 VMs." >&2
    exit 1
    ;;
esac

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y ca-certificates curl git

# Remove packages that conflict with Docker Engine from Docker's repository.
apt-get remove -y \
  docker.io docker-compose docker-compose-v2 docker-doc podman-docker \
  containerd runc

install -m 0755 -d /etc/apt/keyrings
rm -f /etc/apt/sources.list.d/docker.list
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin \
  docker-compose-plugin
systemctl enable --now docker

go_archive="/tmp/go${GO_VERSION}.linux-${go_arch}.tar.gz"
curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-${go_arch}.tar.gz" \
  -o "$go_archive"
printf '%s  %s\n' "$go_sha256" "$go_archive" | sha256sum --check --status
rm -rf /usr/local/go
tar -C /usr/local -xzf "$go_archive"
rm -f "$go_archive"
ln -sfn /usr/local/go/bin/go /usr/local/bin/go
ln -sfn /usr/local/go/bin/gofmt /usr/local/bin/gofmt

docker_user="${SUDO_USER:-ubuntu}"
if [[ "$docker_user" != "root" ]] && id -u "$docker_user" >/dev/null 2>&1; then
  usermod -aG docker "$docker_user"
fi

go version
docker --version
docker buildx version
docker compose version
systemctl is-active --quiet docker

echo "Go and Docker installation complete."
if [[ "$docker_user" != "root" ]] && id -u "$docker_user" >/dev/null 2>&1; then
  echo "Log out and back in, or run 'newgrp docker', before using Docker as $docker_user."
fi
