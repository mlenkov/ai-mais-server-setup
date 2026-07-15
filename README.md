# AI Mais Server Setup

Автоматизированное развёртывание стека: **Caddy → Yandex-Auth (Python) → Hermes Agent** на Debian 12.

## Архитектура

```
Internet ──► Caddy:443 ──► Yandex-Auth:4180 ──► Hermes:9119
                 ▲              ▲  (127.0.0.1)       ▲  (127.0.0.1)
                 │              │                     │
              TLS/SSL      Yandex OAuth          AI Agent API
```

| Компонент | Пользователь | Порт | Доступ |
|-----------|-------------|------|--------|
| Caddy | `caddy` | `0.0.0.0:443` | Публичный (TLS) |
| Yandex-Auth | `mais` | `127.0.0.1:4180` | Только localhost |
| Hermes Agent | `hermes` | `127.0.0.1:9119` | Только localhost |

**Ключевое требование безопасности:** Yandex-Auth и Hermes слушают ТОЛЬКО `127.0.0.1`. Прямой доступ к портам 4180 и 9119 снаружи невозможен.

**Поток аутентификации:**
1. Пользователь открывает `https://ai.mais.agency/`
2. Caddy отправляет `forward_auth` запрос к Yandex-Auth:4180 (`/auth`)
3. Если нет cookie → Yandex-Auth возвращает 302 redirect на `/start`
4. `/start` → редирект на Yandex OAuth
5. После входа → callback на `/oauth2/callback` → Yandex-Auth устанавливает cookie
6. Повторный запрос → cookie валидна → Yandex-Auth возвращает 200 + заголовки пользователя
7. Caddy пропускает запрос к Hermes Dashboard:9119

### Caddy-маршруты (`ai.mais.agency`)

| Путь | Бэкенд | Описание |
|---|---|---|
| `/start`, `/callback`, `/logout`, `/ping` | Yandex-Auth:4180 | OAuth endpoints |
| `/*` | forward_auth → Yandex-Auth:4180 → Hermes:9119 | Всё остальное — через OAuth к Dashboard |

## Предварительные требования

- Debian 12 (чистая установка)
- Домен `ai.mais.agency`, направленный на сервер
- Права root (`sudo`)
- Git, curl (будут установлены при необходимости)

## Получение Yandex OAuth Credentials

1. Перейдите на https://oauth.yandex.ru
2. Нажмите **"Создать приложение"** (или "Зарегистрировать новое приложение")
3. Укажите:
   - **Название:** `AI Mais Auth`
   - **Платформа:** Веб-сервисы
   - **Redirect URI:** `https://ai.mais.agency/oauth2/callback`
   - **Доступ к данным:** `login:email`, `login:info`
4. После создания приложения скопируйте:
   - **ID приложения** → `YANDEX_CLIENT_ID`
   - **Пароль приложения** → `YANDEX_CLIENT_SECRET`

## Установка

### 1. Подготовка secrets

```bash
mkdir -p /opt/secrets
```

Создайте `/opt/secrets/hermes.env` (опционально, если Hermes использует внешний роутер):

```ini
# OPENCODE_ZEN_API_KEY=sk-zen-your_key
```

### 2. Yandex-Auth (вручную)

```bash
mkdir -p /opt/yandex-auth
# Скопируйте yandex-auth/auth.py в /opt/yandex-auth/
# Скопируйте yandex-auth/yandex-auth.service в /etc/systemd/system/

# Отредактируйте /etc/systemd/system/yandex-auth.service — укажите свои секреты
# YANDEX_CLIENT_ID, YANDEX_CLIENT_SECRET, COOKIE_SECRET

systemctl daemon-reload
systemctl enable --now yandex-auth
```

### 3. Запуск основного установщика

```bash
git clone <repo-url> /opt/ai-mais-server-setup
cd /opt/ai-mais-server-setup
sudo python3 setup.py
```

Скрипт выполнит по порядку:

1. **Secrets** — проверит наличие ключей (опционально)
2. **Caddy** — установит из apt, настроит reverse_proxy на yandex-auth и hermes
3. **Hermes Agent** — создаст пользователя, установит через официальный инсталлятор, настроит systemd unit

### 4. Добавление email'ов в whitelist

Отредактируйте `/etc/oauth2-proxy/authenticated-emails.txt`:

```
user@example.com
```

Yandex-Auth подхватит изменения без перезапуска.

## Проверка

### После установки проверьте статус сервисов:

```bash
systemctl status caddy
systemctl status yandex-auth
systemctl status hermes-agent
```

### Проверьте, что всё слушает только localhost:

```bash
ss -tlnp | grep -E '(4180|9119)'
```

Оба порта должны быть привязаны к `127.0.0.1`.

### Полный цикл аутентификации:

1. Откройте `https://ai.mais.agency` в браузере
2. Должен произойти редирект на `oauth.yandex.ru`
3. После входа в Яндекс — доступ к Hermes Dashboard

## Логи

```bash
journalctl -u caddy -f
journalctl -u yandex-auth -f
journalctl -u hermes-agent -f
```

## Обновление компонентов

### Yandex-Auth

Обновите `auth.py` и перезапустите сервис:

```bash
systemctl restart yandex-auth
```

### Hermes Agent

```bash
sudo -u hermes hermes update
```

### Caddy

```bash
apt update && apt upgrade caddy
```

## Telegram Bot

Для работы Telegram бота требуется Cloudflare Worker (прокси, так как Telegram API заблокирован).

### Cloudflare Worker

```javascript
export default {
  async fetch(request) {
    const url = new URL(request.url);
    const token = url.pathname.split('/')[1];
    if (!token || !token.startsWith('bot')) {
      return new Response('Use: /bot<TOKEN>/<method>', { status: 400 });
    }
    url.hostname = 'api.telegram.org';
    url.protocol = 'https:';
    return fetch(url.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });
  },
};
```

Развернуть на [dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → Create Worker.

### Настройка Hermes

В `~/.hermes/.env`:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=your_user_id
```

В `~/.hermes/config.yaml`:
```yaml
platforms:
  telegram:
    extra:
      base_url: https://your-worker.your-subdomain.workers.dev/bot
```

### Запуск

```bash
hermes gateway
```

Бот появится онлайн. Отправьте `/start` в Telegram.

## Идемпотентность

Скрипт можно безопасно запускать многократно. Каждый шаг проверяет текущее состояние:

- Пакет установлен? → пропустить `apt install`
- Systemd unit активен? → пропустить `systemctl start`
- Hermes уже установлен? → пропустить инсталлятор
