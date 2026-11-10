# Деплой на VPS

Прод — один сервер с Docker: Postgres, бэкенд (FastAPI + собранный фронт) и Caddy, который
сам получает HTTPS-сертификат Let's Encrypt для `5listov.ru`.

Файлы:

| Файл | Зачем |
|---|---|
| `deploy/docker-compose.prod.yml` | сервисы прода: `db`, `backend`, `caddy` |
| `deploy/Dockerfile.prod` | образ: собирает фронт, ставит бэкенд, при старте делает `alembic upgrade head` |
| `deploy/Caddyfile` | HTTPS, сжатие, лимит загрузки 12 МБ, редирект `www` → без `www` |
| `deploy/backup.sh` | ночной бэкап базы и фото |

## 1. Сервер и домен

1. VPS с Ubuntu 22.04+, от 1 ГБ памяти и 10 ГБ диска, открыты порты 80 и 443.
2. Docker: `curl -fsSL https://get.docker.com | sh`.
3. Swap на 1 ГБ — **до первой сборки** (больше не нужно: на сборке занято ~100 МБ swap, а диск маленький). Работающему сайту хватает ~300 МБ, но сборка образа
   (`npm ci` + `vite build`) на сервере с 1 ГБ без swap падает по нехватке памяти:
   ```bash
   sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
   sudo mkswap /swapfile && sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
4. У регистратора домена — A-записи на IP сервера для `5listov.ru` и `www.5listov.ru`.
   Пока они не заработают, Caddy не получит сертификат.

## 2. Код и настройки

```bash
git clone <репозиторий> /srv/tea_rates && cd /srv/tea_rates
cp .env.example .env
nano .env
```

Что обязательно поменять в `.env` для прода:

| Переменная | Значение |
|---|---|
| `POSTGRES_PASSWORD` | длинный случайный пароль (`openssl rand -base64 24`) |
| `PUBLIC_URL` | `https://5listov.ru` |
| `COOKIE_SECURE` | `1` |
| `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET` | из https://oauth.yandex.ru — **выпустите новый секрет**: старый был в переписке |
| `SMTP_*`, `MAIL_FROM` | почта для писем «смена пароля» (ниже) |
| `ALERT_EMAIL` | куда слать письма об ошибках на сайте: `curagin.vanya@yandex.ru` |

`POSTGRES_HOST`/`POSTGRES_PORT` трогать не нужно — в compose они заданы как `db:5432`.

### Почта (восстановление пароля)

Проще всего Яндекс 360 для домена (бесплатно для небольшой почты):

1. Подключить домен `5listov.ru` в https://admin.yandex.ru и создать ящик, например `noreply@5listov.ru`.
2. В настройках ящика — «Пароли приложений» → новый пароль для почты.
3. В `.env`:
   ```
   SMTP_HOST=smtp.yandex.ru
   SMTP_PORT=465
   SMTP_SECURITY=ssl
   SMTP_USER=noreply@5listov.ru
   SMTP_PASSWORD=<пароль приложения>
   MAIL_FROM=5 листов <noreply@5listov.ru>
   ALERT_EMAIL=curagin.vanya@yandex.ru
   ```

Если `SMTP_HOST` пустой, письма не уходят, а пишутся в лог бэкенда.

## 3. Первый запуск

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
docker compose -f deploy/docker-compose.prod.yml logs -f backend   # «Running upgrade … initial schema», затем uvicorn
```

База создаётся пустой: миграция заводит только справочник видов чая.
Проверка: https://5listov.ru/api/health → `{"status":"ok"}`.

## 4. Обновление

```bash
cd /srv/tea_rates && git pull
docker compose -f deploy/docker-compose.prod.yml up -d --build
docker builder prune -af && docker image prune -f  # кэш сборок (~0,5 ГБ) и старые образы — иначе 10 ГБ диска быстро кончатся
```

Миграции применяются сами при старте бэкенда. Свободное место: `df -h /`.

### Изменили модели — новая миграция

На машине разработчика, при запущенной dev-базе:

```bash
alembic revision --autogenerate -m "что поменялось"   # проверьте сгенерированный файл глазами
alembic upgrade head
```

Файл из `back/migrations/versions/` коммитится вместе с изменением моделей.

## Логи и письма об ошибках

Логи всех контейнеров — в Docker, не больше 5 файлов по 10 МБ на сервис (старые удаляются сами):

```bash
docker compose -f deploy/docker-compose.prod.yml logs -f --tail=200 backend   # бэкенд
docker compose -f deploy/docker-compose.prod.yml logs --since=1h backend | grep ERROR
```

Каждая ошибка на сайте (ответ 500, `log.exception` в коде) приходит письмом на `ALERT_EMAIL`: что упало,
адрес запроса, id пользователя и трейсбек. Одинаковые ошибки склеиваются на 10 минут (следующее письмо
скажет, сколько раз она повторилась), всего не больше 20 писем в час. Нужен настроенный SMTP (раздел 2).

## 5. Бэкапы

Бэкапить нужно **и базу, и фото** (том `media`): в базе только ссылки на файлы.

```bash
./deploy/backup.sh                       # → ./backups/db_<дата>.dump и media_<дата>.tar.gz
crontab -e                               # каждую ночь в 4:15:
15 4 * * * cd /srv/tea_rates && ./deploy/backup.sh >> /var/log/tea_rates_backup.log 2>&1
```

Хранятся 7 дней (`KEEP_DAYS`). Каждую ночь архивируются все фото целиком, так что бэкапы занимают
примерно 7 × размер тома `media` — на диске 10 ГБ следите за `df -h /` и `du -sh backups`. Копируйте папку `backups` ещё куда-нибудь (другой сервер,
облачное хранилище) — бэкап на том же диске не спасёт, если умрёт сервер.

### Восстановление

```bash
C="docker compose -f deploy/docker-compose.prod.yml"
$C stop backend
$C exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' < backups/db_<дата>.dump
$C run --rm --no-deps -T -v "$PWD/backups:/backup" --entrypoint sh backend \
  -c "rm -rf /app/media/* && tar -xzf /backup/media_<дата>.tar.gz -C /app/media"
$C start backend
```

## 6. Дубли магазинов

Магазины добавляют пользователи. Один и тот же сайт дважды завести нельзя — это держит уникальный
ключ в базе (`https://www.shop.ru/catalog` и `shop.ru` считаются одним сайтом, на площадках вроде
ВКонтакте и Ozon — с учётом страницы продавца). Похожие названия форма показывает до создания.

Но один магазин может прийти с разными адресами (сайт и группа ВКонтакте). Такие пары ищет отчёт:

```bash
docker compose -f deploy/docker-compose.prod.yml exec backend python -m back.shop_duplicates
```
