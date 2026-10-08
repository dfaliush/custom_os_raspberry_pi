# Продовжити збірку Yocto-образу з ROS 2 на іншому комп'ютері

> **Виконано 2026-10-08:** збірку завершено на іншому ПК (окрема WSL Ubuntu
> 24.04 на D:, 51 хв), образ перевірено на Pi, реліз `yocto-v1.1.0`. Результати
> і пастки: [`2026-10-08-ros2-build-guide.md`](2026-10-08-ros2-build-guide.md),
> розділи 3–4. Документ лишається як історія.

Дата: 2026-10-08. Повний опис кроків і що в них відбувається:
[`2026-10-08-ros2-build-guide.md`](2026-10-08-ros2-build-guide.md). Тут лише
те, що потрібно, щоб підхопити збірку з того місця, де її зупинили.

## Де зупинилися

- Збірка `bitbake rpi5os-image` на ПК з 8 ядрами і 12 ГБ для WSL зупинена
  через SIGINT після 3874 з 10689 задач (≈1 год). Помилок не було: єдиний
  `ERROR: Command execution failed: Stopped build` і є зупинка. Пройдено
  native-частину (інструменти хоста для крос-збірки), крос-компілятор,
  ядро і ROS-пакети для target ще попереду.
- Все, що зроблено, лежить у робочій теці репо: нова тека `ros2/`, шар
  `yocto/meta-rpi5os-ros/`, submodules у `yocto/layers/`, правки `build.sh`,
  `dist.sh`, `rpi5os.conf` (версія 1.1.0), фікс автовідкату в обох образах,
  документи в `docs/`. Збірка нічого в репо не змінює: усе, що їй треба,
  `build.sh` клонує й копіює в `~/yocto` сам.

## 1. На цьому ПК: закомітити і запушити

```bash
cd /d/git/custom_os_raspberry_pi
git status --short                      # має бути список з ros2/, yocto/meta-rpi5os-ros/, yocto/layers/, docs/
git add -A
git commit -m "ros2: counter_pkg, meta-rpi5os-ros layer, meta-ros submodules; fallback armed until first network"
git push
```

Submodules у коміті записані як коміти-піни (`.gitmodules` + два записи
`160000`), їх вміст у репо не потрапляє.

## 2. Кеш не переноситься

Зберігається лише те, що в GitHub. `~/yocto` на цьому ПК (downloads, sstate,
build) не переноситься: на новому ПК збірка йде з нуля, тобто ще раз
викачає джерела (кілька ГБ) і пройде всі 10,7 тис. задач. Орієнтир: та сама
година на native-частину плюс кілька годин на крос-компілятор, ядро і ROS.

## 3. На новому ПК: WSL і збірка

1. WSL 2 з Ubuntu 24.04, користувач, `.wslconfig`, хост-пакети Yocto:
   розділ 0 у guide. Диск WSL на розділі, де є 100+ ГБ вільних. У `.wslconfig` виставити під машину: `memory` на
   2–4 ГБ менше за фізичну пам'ять, `processors` = кількість ядер.
   `build.sh` сам обмежує паралельність до `RAM/2` задач.
2. Репо на диск Windows (не в `/mnt/c` з пробілами в шляху):

   ```bash
   git clone https://github.com/dfaliush/custom_os_raspberry_pi.git D:/git/custom_os_raspberry_pi
   ```

   `git submodule update` не потрібен: `build.sh` читає коміти submodules
   з git-індексу і клонує шари в `~/yocto/layers` сам. Усе, що потрібно для
   збірки, є в репо: рецепти, скрипти, піни шарів.
3. Збірка з кореня репо (PowerShell; `<distro>` це ім'я з `wsl --list`,
   наприклад `Ubuntu-24.04`):

   ```powershell
   wsl -d <distro> -- bash yocto/scripts/build.sh -p      # хвилини: клонує шари, парсить рецепти, показує помилки конфігурації
   wsl -d <distro> -- bash yocto/scripts/build.sh         # години: образ у ~/yocto/build/tmp/deploy/images/raspberrypi5/
   wsl -d <distro> -- bash yocto/scripts/dist.sh          # артефакти релізу в ~/yocto/dist
   ```

   Збірку можна зупиняти (Ctrl-C один раз, bitbake дочікує поточні задачі)
   і запускати знову тією самою командою: продовжить з того місця.

## 4. Після збірки

1. Записати `~/yocto/dist/rpi5os-yocto-v1.1.0-sdcard.img.xz` на картку,
   `userconf.txt` і `wpa_supplicant.conf` на FAT, як у README.
2. Перевірити на Pi за розділом 4 guide: `systemctl status
   rpi5os-counter.service`, `ros2 node list`, `ros2 topic echo /counter`,
   `counter_control stop|start`, demo-нода.
3. Заповнити два `TODO` в guide (тривалість збірки й розмір образу, вивід
   перевірки на Pi), прибрати «чернетка».
4. Реліз: тег `yocto-v1.1.0`, файли з `~/yocto/dist` у GitHub Releases.

## Якщо щось не збирається

- `bitbake` падає на рецепті з meta-ros: лог у
  `~/yocto/build/tmp/work/<arch>/<рецепт>/<версія>/temp/log.do_<task>`.
  Повторити одну задачу: `build.sh <рецепт>` (аргументи йдуть bitbake як є).
- Не вистачає пам'яті (`g++: fatal error: Killed`): зменшити
  `BB_NUMBER_THREADS`/`PARALLEL_MAKE` у `build.sh` або додати `swap` у
  `.wslconfig`.
- Попередження `Failed to fetch URL ... attempting MIRRORS` нормальні:
  джерело береться з дзеркала Yocto.
