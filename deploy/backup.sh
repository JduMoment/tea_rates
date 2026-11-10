#!/usr/bin/env bash
# Бэкап прода: дамп Postgres + архив фото к отзывам. Хранит последние KEEP_DAYS дней.
#   ./deploy/backup.sh                 — в ./backups
#   BACKUP_DIR=/srv/backups ./deploy/backup.sh
# По расписанию (каждую ночь в 4:15) — строка для `crontab -e`:
#   15 4 * * * cd /srv/tea_rates && ./deploy/backup.sh >> /var/log/tea_rates_backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."
COMPOSE="docker compose -f deploy/docker-compose.prod.yml"
BACKUP_DIR="${BACKUP_DIR:-$PWD/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"  # каждая копия фото — полная, на маленьком диске много не держим
STAMP="$(date +%Y-%m-%d_%H%M)"
mkdir -p "$BACKUP_DIR"

# База: пользователь и имя базы — из окружения контейнера
$COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$BACKUP_DIR/db_$STAMP.dump"

# Фото: том media бэкенда
$COMPOSE run --rm --no-deps -T -v "$BACKUP_DIR:/backup" --entrypoint sh backend \
  -c "tar -czf /backup/media_$STAMP.tar.gz -C /app/media ."

find "$BACKUP_DIR" -name 'db_*.dump' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'media_*.tar.gz' -mtime +"$KEEP_DAYS" -delete
echo "$(date '+%F %T') бэкап готов: db_$STAMP.dump, media_$STAMP.tar.gz"
