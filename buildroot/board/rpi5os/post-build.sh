#!/bin/sh
# Правки rootfs перед пакуванням. Аргумент $1 = TARGET_DIR.
# Overlay кладе файли як є; тут те, що треба дописати в згенеровані файли.

set -eu

TARGET="$1"
EXT="${BR2_EXTERNAL_RPI5OS_PATH}"
VERSION="$(cat "${EXT}/VERSION")"

# --- /boot: FAT-розділ SD, звідти беремо userconf.txt і wpa_supplicant.conf ---
# umask=0077: FAT не має прав, без цього файли на ньому читав би будь-хто.
mkdir -p "${TARGET}/boot"
grep -q '[[:space:]]/boot[[:space:]]' "${TARGET}/etc/fstab" || \
	echo '/dev/mmcblk0p1	/boot	vfat	defaults,noatime,umask=0077	0	0' >> "${TARGET}/etc/fstab"

# --- /home: у skeleton Buildroot його немає, а adduser без нього не створить домашню теку ---
mkdir -p "${TARGET}/home"

# --- root без пароля = вхід без пароля. Блокуємо: '*' не збігається з жодним паролем. ---
sed -i 's/^root:[^:]*:/root:*:/' "${TARGET}/etc/shadow"

# --- sshd: наші опції на початку файлу. У sshd_config перше входження виграє. ---
SSHD="${TARGET}/etc/ssh/sshd_config"
if ! grep -q '^# rpi5os:begin' "${SSHD}"; then
	{
		echo '# rpi5os:begin (див. custom_os_raspberry_pi: buildroot/board/rpi5os/post-build.sh)'
		echo 'PermitRootLogin no'
		echo '# Вмикається тільки на перший вхід; sudo ssh-keys-only переключає на "no".'
		echo 'PasswordAuthentication yes'
		echo 'KbdInteractiveAuthentication no'
		echo 'PubkeyAuthentication yes'
		echo '# rpi5os:end'
		echo
		cat "${SSHD}"
	} > "${SSHD}.new"
	mv "${SSHD}.new" "${SSHD}"
fi

# --- sudo для групи wheel (користувач із userconf.txt потрапляє в неї) ---
# sudoers лежить з правами 0440: ">>" не спрацює, а sed -i замінює файл і зберігає права.
grep -q '^%wheel ALL=(ALL:ALL) ALL' "${TARGET}/etc/sudoers" || \
	sed -i '$a %wheel ALL=(ALL:ALL) ALL' "${TARGET}/etc/sudoers"

# --- Версія образу в os-release, щоб на пристрої було видно, що саме запущено ---
OSR="${TARGET}/usr/lib/os-release"
[ -f "${OSR}" ] || OSR="${TARGET}/etc/os-release"
sed -i '/^VARIANT_ID=/d; /^IMAGE_ID=/d; /^IMAGE_VERSION=/d' "${OSR}"
{
	echo 'VARIANT_ID=rpi5os'
	echo 'IMAGE_ID=rpi5os-buildroot'
	echo "IMAGE_VERSION=${VERSION}"
} >> "${OSR}"

# --- Пакет wpa_supplicant кладе свій /etc/wpa_supplicant.conf з network={key_mgmt=NONE}:
#     «підключайся до будь-якої відкритої мережі». Нам такого не треба, а S41wifi
#     за наявністю цього файлу вирішує, що Wi-Fi уже налаштований. Справжній
#     конфіг приходить тільки з boot-розділу (S30bootcfg).
rm -f "${TARGET}/etc/wpa_supplicant.conf"

# --- Секретів в образі бути не може: падаємо, якщо щось просочилося ---
for f in etc/ssh/ssh_host_*key* root/.ssh/authorized_keys etc/wpa_supplicant.conf; do
	for hit in ${TARGET}/${f}; do
		if [ -e "${hit}" ]; then
			echo "post-build: в образі не має бути ${hit#${TARGET}}" >&2
			exit 1
		fi
	done
done
