# rpi5os: власна ОС для Raspberry Pi 5 на Buildroot

Власний образ Linux для Raspberry Pi 5, зібраний через Buildroot: SSH,
Wi-Fi, запис на плату і віддалений вхід. Ітерація 2 (поруч, у `yocto/`) — та сама
задача через Yocto.

Головна думка: перейти від «Linux, який ми налаштували руками» до
«Linux, який можна гарантовано зібрати ще раз». Тому в репо лежить не образ,
а **рецепт**: версія Buildroot прибита тегом, наші зміни — у `BR2_EXTERNAL`,
одна команда дає той самий `sdcard.img`. Готовий образ — у GitHub Releases.

Дизайн і всі рішення з обґрунтуванням: [`docs/specs/2026-10-01-buildroot-design.md`](docs/specs/2026-10-01-buildroot-design.md).

## Що всередині образу

| Шар | Що | Навіщо |
| --- | --- | --- |
| Kernel | `bcm2712` з форку raspberrypi/linux, фіксований коміт | Pi 5 (BCM2712 + RP1) |
| Init | BusyBox init, eudev | мінімально; eudev сам вантажить `brcmfmac` |
| Wi-Fi | firmware CYW43455, `wpa_supplicant`, `wireless-regdb`, `iw` | у стенду тільки Wi-Fi, 5 ГГц, `country=UA` |
| SSH | OpenSSH (`sshd` + `sftp-server`) | `scp`/`sftp` з Windows працюють |
| mDNS | Avahi, hostname `rpi5os` | `ssh user@rpi5os.local` без пошуку IP |
| Адмін | `sudo` для групи `wheel` | |

Чого в образі **немає навмисно**: SSH-ключів, паролів (root заблокований),
Wi-Fi PSK, host keys (генеруються на першому старті, тож вони свої на кожному
пристрої). Образ публічний, і це перевіряє `post-build.sh`: збірка падає, якщо
щось із цього потрапило в rootfs.

## Встановити готовий образ на microSD

Для нового користувача: нічого не збираємо, беремо образ із
[Releases](https://github.com/dfaliush/custom_os_raspberry_pi/releases).
Потрібні microSD від 1 ГБ, кард-рідер і ПК. Команди нижче для Windows:
[Git Bash](https://git-scm.com/download/win) і
[Raspberry Pi Imager](https://www.raspberrypi.com/software/). На Linux і
macOS ті самі команди виконуються у звичайному терміналі.

**1. Завантажити й перевірити образ** (Git Bash):

```bash
mkdir -p ~/rpi5os && cd ~/rpi5os
curl -LO https://github.com/dfaliush/custom_os_raspberry_pi/releases/download/buildroot-v1.0.0/rpi5os-buildroot-v1.0.0-sdcard.img.xz
curl -LO https://github.com/dfaliush/custom_os_raspberry_pi/releases/download/buildroot-v1.0.0/SHA256SUMS
sha256sum -c SHA256SUMS --ignore-missing    # має бути: rpi5os-buildroot-v1.0.0-sdcard.img.xz: OK
```

**2. Записати на картку.** Raspberry Pi Imager → *Choose Device*: Raspberry
Pi 5 → *Choose OS*: *Use Custom* → `rpi5os-buildroot-v1.0.0-sdcard.img.xz`
(розпаковувати не треба) → *Choose Storage*: картка → *Next*. На питання про
*OS customisation* відповісти **No**: ці налаштування для Raspberry Pi OS,
rpi5os їх не розуміє.

Те саме в терміналі: **PowerShell від імені адміністратора** (без цього
Imager не пише на диски). Imager у режимі `--cli` нічого не питає, сам
розпаковує `.xz`, звіряє записане і відмовляється писати на системний диск.

```powershell
winget install --id RaspberryPiFoundation.RaspberryPiImager -e     # якщо Imager ще не встановлений
Get-Disk | Where-Object BusType -in 'USB','SD','MMC' | Format-Table Number,FriendlyName,BusType,@{n='GB';e={[math]::Round($_.Size/1GB,1)}}
$n = 2                                      # Number картки з таблиці вище
$imager = (Get-Item 'C:\Program Files*\Raspberry Pi Imager\rpi-imager.exe' | Select-Object -First 1).FullName
& $imager --cli "$HOME\rpi5os\rpi5os-buildroot-v1.0.0-sdcard.img.xz" "\\.\PhysicalDrive$n"
```

Якщо таблиця порожня, картку не видно як знімний диск: витягни й встав її ще
раз або спробуй інший кард-рідер. Номер `$n` перевір двічі: якщо помилишся,
Imager повністю затре вибраний диск.

На Linux замість Imager можна використати `dd`. **Перевір пристрій**: `dd`
затре його повністю.

```bash
lsblk -d -o NAME,SIZE,TRAN,MODEL            # картка: sdX або mmcblk0
xz -dc rpi5os-buildroot-v1.0.0-sdcard.img.xz | sudo dd of=/dev/sdX bs=4M conv=fsync status=progress
```

**3. Відкрити boot-розділ.** Imager після запису витягує картку програмно,
тож вийми її й встав знову. Windows покаже диск `RPI5OS-BOOT` і, можливо,
запропонує відформатувати другий розділ: **Скасувати**, бо це rootfs у ext4,
якого Windows не читає. У Git Bash знайди літеру диска за міткою:

```bash
L=$(powershell.exe -NoProfile -Command "(Get-Volume -FileSystemLabel RPI5OS-BOOT -ErrorAction SilentlyContinue | Select-Object -First 1).DriveLetter" | tr -d '\r' | tr 'A-Z' 'a-z')
if [ -n "$L" ]; then B=/$L; ls "$B"; else unset B; echo "RPI5OS-BOOT не знайдено: встав картку ще раз"; fi
```

Має бути `config.txt`, `Image`, `*.example` тощо. На Linux:
`sudo mount /dev/sdX1 /mnt && B=/mnt`, а файли в кроках 4–5 писати через
`sudo tee` замість `>`.

**4. Користувач і пароль.** Ім'я може складатися з малих латинських літер,
цифр, `_` і `-`. Пароль не зберігається: у файл іде тільки sha512-crypt hash.

```bash
read -rsp 'Пароль: ' P; echo
printf 'user:%s\n' "$(printf '%s' "$P" | openssl passwd -6 -stdin)" > "$B/userconf.txt"; unset P
cat "$B/userconf.txt"                       # user:$6$...
```

**5. Wi-Fi.** Ethernet rpi5os не налаштовує, мережа тільки через Wi-Fi.
Країна потрібна для 5 ГГц: без неї частина каналів закрита. Пароль Wi-Fi
вводиться через `read -s`, тож він не потрапляє ні на екран, ні в історію bash.

```bash
read -rp 'SSID: ' SSID; read -rsp 'Пароль Wi-Fi: ' PSK; echo; read -rp 'Країна (UA, PL, DE, ...): ' CC
printf 'ctrl_interface=/var/run/wpa_supplicant\nupdate_config=0\ncountry=%s\n\nnetwork={\n\tssid="%s"\n\tpsk="%s"\n\tkey_mgmt=WPA-PSK\n}\n' \
	"$CC" "$SSID" "$PSK" > "$B/wpa_supplicant.conf"; unset PSK
grep -v psk "$B/wpa_supplicant.conf"        # перевірка без пароля
```

Для мережі тільки з WPA3 заміни у файлі `key_mgmt=WPA-PSK` на `key_mgmt=SAE`.
Без терміналу те саме робиться так: скопіювати `wpa_supplicant.conf.example`
у `wpa_supplicant.conf`, відредагувати в Блокноті і зберегти як **UTF-8**, не
«UTF-8 with BOM».

На першому старті rpi5os перенесе обидва файли в rootfs і видалить їх з
картки: на FAT немає прав доступу, і пароль Wi-Fi там лишатися не повинен.

**6. Запуск.** Безпечно вийняти картку (Провідник → *Eject*, або з Git Bash
командою нижче), вставити в Pi 5 і ввімкнути живлення.

```bash
powershell.exe -NoProfile -Command "(New-Object -ComObject Shell.Application).Namespace(17).ParseName('${B#/}:').InvokeVerb('Eject')"
```

Pi 5 із завода стартує з SD першою. Якщо на твоїй Pi уже стоїть ОС на SSD,
спершу прочитай розділ нижче. Через ~1 хв:

```bash
ssh user@rpi5os.local                       # пароль з кроку 4
```

Далі розділ «Перший вхід»: додати ключ і вимкнути вхід за паролем. Якщо
`rpi5os.local` не знаходиться, шукай у списку DHCP роутера пристрій з ім'ям
`rpi5os`.

**Якщо Pi не з'явилась у мережі.** Через 3 хв без мережі rpi5os сама
«вимикає» картку і перезавантажується (див. «Відкат на SSD»). Причину видно на
ПК: вставити картку і відкрити `RPI5OS-BOOT\rpi5os-boot.log`. Щоб спробувати
ще раз, поверни boot-файли на місце й поклади виправлений
`wpa_supplicant.conf` (крок 5):

```bash
mv "$B"/disabled/* "$B"/ && rmdir "$B/disabled"
tail -n 20 "$B/rpi5os-boot.log"
```

## Raspberry Pi OS уже на SSD: перемкнутись на SD

Якщо Pi стартує з NVMe SSD, вставлена картка ігнорується: порядок
завантаження задає `BOOT_ORDER` в EEPROM. Його цифри читаються справа наліво:
`1` = SD, `6` = NVMe, `4` = USB, `f` = почати знову. Наприклад, `0xf461`
означає SD → NVMe → USB, а `0xf416` (так ставить `raspi-config`, коли
обираєш NVMe) означає NVMe → SD → USB.

Кроки 1–3 виконуються на Raspberry Pi OS, з якою Pi зараз стартує. На SSD
змінюється тільки конфіг EEPROM.

**0. Зайти на Raspberry Pi OS** з ПК (підстав свої ім'я користувача й
hostname):

```bash
ssh user@raspberrypi
```

**1. Скрипти з репо** (тієї ж версії, що й образ):

```bash
mkdir -p ~/rpi5os && cd ~/rpi5os
for s in boot-order.sh sd-boot.sh flash-sd.sh; do
	curl -fsSLO "https://raw.githubusercontent.com/dfaliush/custom_os_raspberry_pi/buildroot-v1.0.0/buildroot/scripts/pi/$s"
done
sudo bash boot-order.sh show                # BOOT_ORDER зараз: 0x...
```

**2. Записати картку.** Або на ПК, як у розділі вище (кроки 1–5), і вставити
в Pi, або прямо з Pi, не виймаючи картку зі слота. Для другого варіанта Pi має
бути підключена до Wi-Fi через NetworkManager: `flash-sd.sh` бере SSID і
пароль з активного з'єднання і пише `wpa_supplicant.conf` сам.

```bash
curl -LO https://github.com/dfaliush/custom_os_raspberry_pi/releases/download/buildroot-v1.0.0/rpi5os-buildroot-v1.0.0-sdcard.img.xz
printf 'user:%s\n' "$(openssl passwd -6)" > /dev/shm/rpi5os-userconf.txt    # openssl двічі спитає пароль
sudo bash flash-sd.sh rpi5os-buildroot-v1.0.0-sdcard.img.xz
```

`flash-sd.sh` пише тільки в `/dev/mmcblk0` і відмовиться, якщо з цього
пристрою працює поточна система. Записане він звіряє за sha256.

**3. SD першою в порядку завантаження:**

```bash
sudo bash boot-order.sh sd-first            # бекап у ~/rpi5os-eeprom-backup.conf, потім BOOT_ORDER=0xf461
sudo reboot
```

Під час reboot bootloader оновлює EEPROM і стартує з SD. Якщо Pi все ж
піднялась з SSD, перевір `sudo bash boot-order.sh show` і перезавантаж ще
раз. SSH-сесія обірветься. Через ~1 хв підключайся вже до rpi5os, як
описано в розділі «Перший вхід» нижче.

**Як ходити між системами після цього:**

| Що треба | Команда |
| --- | --- |
| з rpi5os на SSD | `sudo boot-ssd && sudo reboot` (або вийняти картку й перезавантажити) |
| з SSD знову на rpi5os | `sudo bash ~/rpi5os/sd-boot.sh on && sudo reboot` |
| подивитись стан і лог rpi5os з SSD | `sudo bash ~/rpi5os/sd-boot.sh status` |
| повернути EEPROM як було | `sudo bash ~/rpi5os/boot-order.sh restore && sudo reboot` |

З `BOOT_ORDER=0xf461` і без картки (або з вимкненою) Pi сама стартує з
SSD, тож `sd-first` можна не відкочувати.

## Перший вхід

Усі команди виконуються на ПК. Ім'я користувача й пароль ті, що в
`userconf.txt`. SSH-клієнт уже є в Ubuntu, macOS і Windows 10/11.

**0. Чи видно Pi в мережі.** `rpi5os.local` знаходиться через mDNS:

| ОС | Перевірка | Якщо не знаходиться |
| --- | --- | --- |
| Ubuntu | `ping -c 1 rpi5os.local` | на Ubuntu Server немає mDNS-резолвера: `sudo apt install avahi-daemon libnss-mdns` |
| macOS | `ping -c 1 rpi5os.local` | Bonjour вбудований; перевір, що Mac і Pi в одній мережі |
| Windows | `ping -n 1 rpi5os.local` | взяти IP пристрою `rpi5os` зі списку DHCP роутера і далі писати його замість `rpi5os.local` |

**1. Якщо rpi5os на цій картці вже стояла раніше,** прибери старий host key.
Кожна установка генерує нові ключі, і без цього ssh відмовить з `REMOTE HOST
IDENTIFICATION HAS CHANGED`. Команда однакова на всіх ОС:

```bash
ssh-keygen -R rpi5os.local
```

**2. Увійти за паролем.** На питання про fingerprint відповісти `yes`:

```bash
ssh user@rpi5os.local
exit                                        # назад на ПК: наступні команди виконуються там
```

**3. Додати свій ключ.** В образі ключів немає.

Ubuntu / macOS:

```bash
[ -f ~/.ssh/id_ed25519.pub ] || ssh-keygen -t ed25519    # створити ключ, якщо його ще немає
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@rpi5os.local
```

Якщо `ssh-copy-id` немає (старі версії macOS):

```bash
cat ~/.ssh/id_ed25519.pub | ssh user@rpi5os.local "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

Windows: створити ключ, якщо його ще немає (`ssh-keygen -t ed25519`), потім
у PowerShell:

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh user@rpi5os.local "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

У cmd (`C:\>`): `type %USERPROFILE%\.ssh\id_ed25519.pub | ssh …`, далі так
само. У Git Bash працює `ssh-copy-id`, як в Ubuntu.

> Якщо `type … | ssh` у PowerShell 5.1 нічого не дописав (файл лишився
> порожнім) — встав ключ прямо в команду: `ssh … "echo 'ssh-ed25519 AAAA…' >> ~/.ssh/authorized_keys"`.

**4. Перевірити вхід за ключем і вимкнути паролі.** Перша команда має
пройти без запиту пароля. `sudo` спитає пароль користувача.

Ubuntu, macOS, Git Bash і cmd:

```bash
ssh -o BatchMode=yes user@rpi5os.local true && ssh -t user@rpi5os.local sudo ssh-keys-only
```

PowerShell 5.1 (`&&` там немає):

```powershell
ssh -o BatchMode=yes user@rpi5os.local true; if ($?) { ssh -t user@rpi5os.local sudo ssh-keys-only }
```

`ssh-keys-only` відмовиться, якщо `authorized_keys` порожній: так неможливо
відрізати собі доступ. Далі вхід лише за ключем: `ssh user@rpi5os.local`.

## Yocto-образ (ітерація 2)

Та сама ОС, зібрана через Yocto 6.0 «Wrynose» (тека `yocto/`, рішення в
[`docs/specs/2026-10-01-yocto-design.md`](docs/specs/2026-10-01-yocto-design.md)).
Для користувача все так само, як вище, крім трьох речей:

| Що | Buildroot | Yocto |
| --- | --- | --- |
| файл релізу | `rpi5os-buildroot-v1.0.0-sdcard.img.xz` | `rpi5os-yocto-v1.0.0-sdcard.img.xz` |
| тег релізу | `buildroot-v1.0.0` | `yocto-v1.0.0` |
| адреса в мережі | `rpi5os.local` | `rpi5os-yocto.local` |

Тобто в командах розділів «Встановити готовий образ», «Raspberry Pi OS уже на
SSD» і «Перший вхід» підстав ці імена. Мітка FAT (`RPI5OS-BOOT`), файли
`userconf.txt` і `wpa_supplicant.conf`, `ssh-keys-only`, `boot-ssd`, автовідкат
і скрипти `flash-sd.sh` / `sd-boot.sh` / `boot-order.sh` — ті самі.

**Перший вхід у Yocto-образ.** Ті самі кроки, що в розділі «Перший вхід»,
тільки з `rpi5os-yocto.local`. `ssh-keygen -R` не потрібен, якщо раніше на
цьому hostname нічого не стояло.

```bash
ssh user@rpi5os-yocto.local                 # 1. пароль з userconf.txt
exit                                        #    обов'язково: кроки 2–3 виконуються на ПК, не на Pi
```

2–3 у cmd (у PowerShell замість `%USERPROFILE%` пиши `$env:USERPROFILE`, а
замість `&&` — `; if ($?) { … }`):

```cmd
type %USERPROFILE%\.ssh\id_ed25519.pub | ssh user@rpi5os-yocto.local "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys"
ssh -o BatchMode=yes user@rpi5os-yocto.local true && ssh -t user@rpi5os-yocto.local sudo ssh-keys-only
```

Ubuntu / macOS: `ssh-copy-id user@rpi5os-yocto.local`, потім другий рядок.

> Якщо друга команда питає пароль або пише `Permission denied (publickey…)`,
> ключ не дописався. Найчастіше причина в тому, що крок 2 виконали в сесії на
> самій Pi, а не на ПК: тоді в `~/.ssh/authorized_keys` лежить рядок на
> кшталт `%USERPROFILE%.sshid_ed25519.pub: not found`. Перевір:
> `ssh user@rpi5os-yocto.local cat .ssh/authorized_keys`. Виправити можна,
> записавши ключ напряму:
> `ssh user@rpi5os-yocto.local "echo 'ssh-ed25519 AAAA… коментар' > ~/.ssh/authorized_keys"`
> (вміст свого `id_ed25519.pub`).

Як перевірити, що запущено саме Yocto-образ:

```bash
ssh user@rpi5os-yocto.local 'grep -E "^NAME|VERSION_ID|IMAGE_ID" /etc/os-release; uname -r; systemctl is-system-running'
# NAME=rpi5os, VERSION_ID=1.0.0, IMAGE_ID=rpi5os-yocto, kernel 6.18.x, running
```

Тут systemd, тож доступні `systemctl`, `journalctl -b` і `networkctl`.

**Зібрати** (перший раз кілька годин і ~100–150 ГБ на ext4, далі
інкрементально):

```bash
sudo apt install gawk wget git diffstat unzip texinfo gcc build-essential chrpath socat cpio \
	python3 python3-pip python3-pexpect xz-utils debianutils iputils-ping python3-git \
	python3-jinja2 python3-subunit zstd liblz4-tool file locales libacl1
```

```powershell
wsl -d Ubuntu -- bash yocto/scripts/build.sh
wsl -d Ubuntu -- bash yocto/scripts/dist.sh
```

`build.sh` бере `openembedded-core` і `bitbake` на тегу `yocto-6.0.3`,
`meta-raspberrypi` на прибитому коміті, копіює `yocto/meta-rpi5os` у
`~/yocto/layers` і запускає `bitbake rpi5os-image`. Образ:
`~/yocto/build/tmp/deploy/images/raspberrypi5/rpi5os-image-raspberrypi5.rootfs.wic`,
артефакти релізу — у `~/yocto/dist/`: `.img.xz`, `SHA256SUMS`, `layers.txt`
(ревізії шарів і `local.conf`), `license.manifest`, `.spdx.json` (SBOM).

Пастки, на які натрапили з Yocto (firmware Wi-Fi поза `IMAGE_INSTALL`, цикл
systemd, локаль для bitbake), і результати T1–T7 на залізі — у spec, розділи
«Знайдено під час реалізації» і «Результати на залізі».

## Стенд

| Що | Деталі |
| --- | --- |
| Плата | Raspberry Pi 5 Model B Rev 1.1, 8 ГБ |
| Основна ОС | Raspberry Pi OS trixie на NVMe SSD, `ssh user@raspberrypi`. **SSD не чіпаємо** |
| rpi5os | на microSD у слоті тієї ж Pi (`/dev/mmcblk0`) |
| Мережа | тільки Wi-Fi |
| Збірка | Windows 11 + WSL2 Ubuntu 22.04 (24 ядра, 31 ГБ RAM) |

## Структура

```text
custom_os_raspberry_pi/
├─ docs/specs/                    # дизайн обох ітерацій
├─ yocto/                         # ітерація 2, див. «Yocto-образ»
│  ├─ meta-rpi5os/                # шар: distro rpi5os, rpi5os-image, скрипти й systemd units
│  └─ scripts/build.sh, dist.sh   # WSL: від нуля до .wic і артефакти релізу
└─ buildroot/                     # BR2_EXTERNAL, name: RPI5OS
   ├─ configs/rpi5os_defconfig    # raspberrypi5_defconfig + наші зміни (розмічено в файлі)
   ├─ VERSION                     # версія образу → /etc/os-release, ім'я релізу
   ├─ board/rpi5os/
   │  ├─ config.txt, cmdline.txt  # boot-розділ: kernel=Image, regdom=UA
   │  ├─ genimage.cfg.in          # розмітка SD: boot 64M (FAT) + rootfs ext4
   │  ├─ post-build.sh            # sshd_config, lock root, /boot у fstab, перевірка секретів
   │  ├─ post-image.sh            # sdcard.img + приклади конфігів на FAT
   │  ├─ bootfs/*.example         # шаблони wpa_supplicant.conf і userconf.txt
   │  └─ rootfs-overlay/          # init-скрипти й утиліти rpi5os
   └─ scripts/
      ├─ build.sh                 # WSL: від нуля до sdcard.img
      ├─ dist.sh                  # WSL: .img.xz, .config, manifest ліцензій, SHA256SUMS
      ├─ flash-to-pi.sh           # Git Bash: образ → microSD Pi по ssh
      └─ pi/                      # виконуються на Raspberry Pi OS
         ├─ flash-sd.sh           # dd на mmcblk0 з перевірками + конфіги на FAT
         ├─ sd-boot.sh            # on|off|status: увімкнути/вимкнути SD-завантаження
         └─ boot-order.sh         # sd-first|restore|show: BOOT_ORDER в EEPROM
```

## Зібрати

Разово поставити залежності у WSL:

```bash
sudo apt install build-essential unzip bc libncurses-dev rsync cpio file wget git
```

Збірка (перший раз ~30–60 хв, далі інкрементально):

```powershell
wsl -d Ubuntu -- bash buildroot/scripts/build.sh
wsl -d Ubuntu -- bash buildroot/scripts/dist.sh
```

`build.sh` копіює `buildroot/` у `~/br/external` (на ext4, з явними правами),
клонує Buildroot `2026.02.3` у `~/br/buildroot` і збирає в `~/br/output`.
Результат: `~/br/output/images/sdcard.img`, артефакти релізу — у `~/br/dist/`.

> **Пастки WSL.** (1) Збирати тільки на ext4 (`~`), не на `/mnt/d`: drvfs не
> тримає права й регістр імен. (2) WSL дописує в `PATH` теки Windows з
> пробілами, і Buildroot відмовляється стартувати («Your PATH contains
> spaces»). `build.sh` вирізає з `PATH` усе, що на `/mnt/`.

## Пастки, знайдені на залізі

- **Pi 5 Rev 1.1 = кремній D0, потрібен `overlays/bcm2712d0.dtbo`.** Firmware
  бере базовий `bcm2712-rpi-5-b.dtb` і накладає на нього цей overlay
  (`vclog -m` на Raspberry Pi OS: `Loaded overlay 'bcm2712d0'`). У
  `raspberrypi5_defconfig` overlays вимкнені, і перший образ падав у kernel
  panic за 2–4 с: rootfs жодного разу не змонтувався (`tune2fs -l`:
  `Mount count: 0`), зелений LED горів рівно, без кодів помилки.
  `post-image.sh` тепер кладе overlay з того ж дерева kernel і падає, якщо його немає.
- **Без монітора й UART діагностували так:** `vclog -m` (лог bootloader),
  `tune2fs -l` на rootfs SD (чи доходило до монтування), час від reboot до
  повернення на SSD, і **`tryboot`**: на FAT немає `config.txt`, є
  `tryboot.txt`; звичайний boot SD пропускає (`[sdcard] config.txt not found`
  → NVMe), а `sudo reboot "0 tryboot"` один раз запускає rpi5os. З
  `panic=10 rootwait=30` у cmdline будь-яке падіння саме повертало Pi на SSD.
- **BusyBox `addgroup user group` не працює** без `FEATURE_ADDUSER_TO_GROUP`,
  а в skeleton немає `/home`. Обидва мовчки ламали `userconf.txt`: вхід за
  паролем був, але без home і без `sudo`. `S30bootcfg` тепер створює home
  явно, дописує `wheel` у `/etc/group` і пише результат у лог.
- **Пакет `wpa_supplicant` кладе свій `/etc/wpa_supplicant.conf`** з
  `network={key_mgmt=NONE}` («до будь-якої відкритої мережі»). Його ловить
  перевірка секретів у `post-build.sh`, файл видаляється.
- **`nmcli -g` екранує `:` і `\`**: `flash-sd.sh` читає SSID/PSK з `--escape no`.
- **`udhcpc` при `leasefail` запускає `avahi-autoipd`**, і той вішає на `wlan0`
  `169.254.x.x`. Перша версія `S99fallback` рахувала будь-яку IPv4 і писала
  `OK: 169.254.x.x/16`, доки DHCP ще не відповів. З неправильним PSK або
  без роутера Pi лишилась би на SD недосяжною. Тепер link-local не рахується.
  Перевірено на залізі: з `psk="wrong"` відкат на SSD через ~200 с, у лог
  записано `wpa_state=SCANNING`.

## Записати свою збірку з ПК прямо на Pi (розробка)

Для власної збірки з `~/br/dist`, без кард-рідера: образ пишеться з Raspberry
Pi OS на SSD у microSD тієї ж Pi. Образ і тимчасові файли лежать у `/dev/shm`
(RAM), на SSD нічого не пишеться.

**1. Пароль першого входу** (робиш сам, пароль нікуди не передається відкритим):

Зайти на Pi (`ssh user@raspberrypi`) і вже там виконати (openssl двічі спитає пароль):

```bash
printf 'user:%s\n' "$(openssl passwd -6)" > /dev/shm/rpi5os-userconf.txt
```

На Pi лягає тільки sha512-crypt hash, і той у RAM.

**2. Запис** (Git Bash):

```bash
bash buildroot/scripts/flash-to-pi.sh //wsl.localhost/Ubuntu/home/<user>/br/dist/rpi5os-buildroot-v1.0.0-sdcard.img.xz
```

`flash-sd.sh` на Pi перевіряє, що ціль — справді microSD (`TRAN=mmc`, не
носій `/` чи `/boot/firmware`), пише `dd`, звіряє sha256 записаного і кладе на
FAT-розділ `userconf.txt` та `wpa_supplicant.conf`. Wi-Fi береться з активного
з'єднання NetworkManager на самій Pi: PSK не виходить за її межі.

**3. Порядок завантаження.** У Pi стояло `BOOT_ORDER=0xf146` (NVMe першим),
з таким microSD ніколи не стартує. Ставимо SD першою (детальніше в розділі
«Raspberry Pi OS уже на SSD: перемкнутись на SD»):

```bash
ssh user@raspberrypi "sudo bash /dev/shm/boot-order.sh sd-first && sudo reboot"
```

З вийнятою або вимкненою SD Pi сама йде на NVMe.

## Як воно стартує

`mount -a` (FAT-розділ → `/boot`, `umask=0077`) → `S10udev` (вантажить
`brcmfmac`) → `S30bootcfg` (створює користувача з `userconf.txt`, переносить
`wpa_supplicant.conf` у `/etc`, **видаляє обидва з FAT**) → `S41wifi`
(`wpa_supplicant` + `udhcpc -b`) → `sshd`, `avahi-daemon` → `S99fallback`.

Чому `S41wifi`, а не `ifupdown` з `inet dhcp`: ifupdown запускає `udhcpc -n`,
який здається після кількох спроб, а асоціація з точкою на 5 ГГц буває довшою.

## Відкат на SSD

Wi-Fi тут єдиний канал: rpi5os, яка не вийшла в мережу, була б недосяжна.

- **Автоматично.** `S99fallback` чекає 3 хв IPv4 на `wlan0` і живий `sshd`.
  Не дочекався → пише діагностику в `/boot/rpi5os-boot.log`, вимикає SD
  (`boot-ssd`) і перезавантажується. Pi стартує з SSD, лог видно звідти:
  `sudo bash /dev/shm/sd-boot.sh status`. Вимкнути автовідкат: покласти
  порожній `no-fallback` на FAT-розділ.
- **Вручну з rpi5os:** `sudo boot-ssd && sudo reboot`.
- **Знову на rpi5os з SSD:** `sudo bash /dev/shm/sd-boot.sh on && sudo reboot`.
- **Повністю повернути як було:** `sudo bash /dev/shm/boot-order.sh restore`.

«Вимкнути SD» означає перенести boot-файли в `disabled/` на тому ж FAT:
без `config.txt` і kernel bootloader вважає картку порожньою і йде далі по
`BOOT_ORDER`.

## Реліз

Тег `buildroot-v<VERSION>` (Yocto-ітерація отримає `yocto-v<VERSION>`).
Assets з `~/br/dist/`: `.img.xz`, `SHA256SUMS`, `buildroot.config`,
`legal-info-manifest.csv` (пакети, версії, ліцензії).

Як записати реліз без збірки: розділ «Встановити готовий образ на microSD».
