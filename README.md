# AI Mais Server Setup

Автоматизированное развёртывание стека: **Caddy → OAuth2-Proxy (Yandex) → Hermes Agent** на Debian 12.

## Архитектура

```
Internet ──► Caddy:443 ──► OAuth2-Proxy:4180 ──► Hermes:8080
                 ▲              ▲  (127.0.0.1)       ▲  (127.0.0.1)
                 │              │                     │
              TLS/SSL      Yandex OAuth         AI Agent API
```

| Компонент | Пользователь | Порт | Доступ |
|-----------|-------------|------|--------|
| Caddy | `caddy` | `0.0.0.0:443` | Публичный (TLS) |
| OAuth2-Proxy | `oauth2-proxy` | `127.0.0.1:4180` | Только localhost |
| Hermes Agent | `hermes` | `127.0.0.1:8080` | Только localhost |

**Ключевое требование безопасности:** Hermes и OAuth2-Proxy слушают ТОЛЬКО `127.0.0.1`. Прямой доступ к порту 8080 снаружи невозможен.

## Предварительные требования

- Debian 12 (чистая установка)
- Домен `ai.mais.agency`, направленный на сервер
- Права root (`sudo`)
- Git, curl, xz-utils (будут установлены при необходимости)

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

## Получение OpenCode Zen API Key

1. Зарегистрируйтесь на https://opencode.ai
2. В настройках аккаунта создайте API-ключ
3. Скопируйте ключ → `OPENCODE_ZEN_API_KEY`

## Установка

### 1. Подготовка secrets

```bash
mkdir -p /opt/secrets
```

Создайте `/opt/secrets/hermes.env`:

```ini
YANDEX_CLIENT_ID=your_client_id
YANDEX_CLIENT_SECRET=your_client_secret
OPENCODE_ZEN_API_KEY=sk-zen-your_key
# OAUTH2_PROXY_COOKIE_SECRET=  # будет сгенерирован автоматически
```

### 2. Запуск установки

```bash
git clone <repo-url> /opt/ai-mais-server-setup
cd /opt/ai-mais-server-setup
sudo python3 setup.py
```

Скрипт выполнит по порядку:

1. **Secrets** — проверит наличие ключей, сгенерирует `OAUTH2_PROXY_COOKIE_SECRET`
2. **Caddy** — установит из apt, настроит reverse_proxy на 4180
3. **OAuth2-Proxy** — скачает бинарник (v7.15.3), создаст пользователя и systemd unit
4. **Hermes Agent** — создаст пользователя, установит через официальный инсталлятор, настроит OpenCode Zen, запустит dashboard на 8080

### 3. Добавление email'ов в whitelist

Отредактируйте `/etc/oauth2-proxy/authenticated-emails.txt`:

```
user@example.com
another@example.com
```

Затем перезапустите OAuth2-Proxy:

```bash
systemctl restart oauth2-proxy
```

## Проверка

### После установки проверьте статус сервисов:

```bash
systemctl status caddy
systemctl status oauth2-proxy
systemctl status hermes-agent
```

### Проверьте, что всё слушает только localhost:

```bash
ss -tlnp | grep -E '(4180|8080)'
```

Оба порта должны быть привязаны к `127.0.0.1`.

### Полный цикл аутентификации:

1. Откройте `https://ai.mais.agency` в браузере
2. Должен произойти редирект на `oauth.yandex.ru`
3. После входа в Яндекс — доступ к Hermes Dashboard

## Логи

```bash
journalctl -u caddy -f
journalctl -u oauth2-proxy -f
journalctl -u hermes-agent -f
```

## Обновление компонентов

### OAuth2-Proxy

Обновите версию в `src/oauth2_proxy.py` (`OAUTH2_PROXY_VERSION`) и перезапустите скрипт.

### Hermes Agent

```bash
sudo -u hermes hermes update
```

### Caddy

```bash
apt update && apt upgrade caddy
```

## Идемпотентность

Скрипт можно безопасно запускать многократно. Каждый шаг проверяет текущее состояние:

- Пакет установлен? → пропустить `apt install`
- Бинарник нужной версии? → пропустить скачивание
- Systemd unit активен? → пропустить `systemctl start`
- Hermes уже установлен? → пропустить инсталлятор

## Общая информация

| Параметр | Значение |
|----------|----------|
| Провайдер Hermes | OpenCode Zen |
| Модель | `opencode-zen/deepseek-v4-flash-free` |
| OAuth2-Proxy версия | v7.15.3 |
| ОС | Debian 12 |
