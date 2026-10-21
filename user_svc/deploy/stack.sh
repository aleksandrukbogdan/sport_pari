#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COMPOSE=(docker compose -f deploy/docker-compose.yml)
STATE=deploy/vault/state
DB_VOLUME=user-svc_keycloak-db
VAULT_URL=http://127.0.0.1:8200

info() { printf '==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage: deploy/stack.sh <command> [test|prod]

  up [env]   start the whole stack (default env: test)
  status     show containers and Vault state
  down       stop the stack, keep data
  reset      remove all containers, volumes and Vault state
EOF
}

confirm() {
  local answer
  read -r -p "$1 [y/N] " answer
  case "$answer" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

json_escape() {
  local s=${1//\\/\\\\}
  printf '%s' "${s//\"/\\\"}"
}

require_docker() {
  docker info >/dev/null 2>&1 || die "Docker is not running"
}

check_gmail() {
  local line=""
  line=$( { exec 3<>/dev/tcp/smtp.gmail.com/587 && read -t 8 -r line <&3 && printf '%s' "$line"; } 2>/dev/null ) || true
  case "$line" in
    220*) info "smtp.gmail.com:587 is reachable" ;;
    *) warn "smtp.gmail.com:587 did not answer (is a VPN on?). Verification emails will not be sent." ;;
  esac
}

vault_api_up() {
  curl -sf "$VAULT_URL/v1/sys/seal-status" >/dev/null
}

vault_initialized() {
  curl -s "$VAULT_URL/v1/sys/seal-status" | grep -q '"initialized":true'
}

api_healthy() {
  curl -sf http://localhost:8000/health >/dev/null
}

wait_for() {
  local what=$1 tries=$2 i=0
  shift 2
  until "$@"; do
    i=$((i + 1))
    [ "$i" -ge "$tries" ] && die "timed out waiting for $what"
    sleep 3
  done
}

state_ready() {
  [ -s "$STATE/unseal.key" ] && [ -s "$STATE/approle/$1.env" ]
}

has_google_secret() {
  "${COMPOSE[@]}" run -T --rm --entrypoint sh vault-init -c '
    . /scripts/lib.sh
    VAULT_TOKEN=$(approle_login "$APP_ENV")
    export VAULT_TOKEN
    vault kv get -field=smtp_user "secret/$APP_ENV/google-smtp" >/dev/null 2>&1 &&
      vault kv get -field=smtp_password "secret/$APP_ENV/google-smtp" >/dev/null 2>&1
  ' </dev/null >/dev/null 2>&1
}

prompt_google_secret() {
  local user pass op json
  printf 'Google SMTP secret for %s is not set in Vault.\n' "$APP_ENV"
  read -r -p "Google account (empty to skip): " user
  if [ -z "$user" ]; then
    warn "skipped: add secret/$APP_ENV/google-smtp in Vault later"
    return 0
  fi
  read -r -s -p "Google app password: " pass
  echo
  read -r -s -p "Vault operator password: " op
  echo
  json=$(printf '{"smtp_user":"%s","smtp_password":"%s"}' "$(json_escape "$user")" "$(json_escape "$pass")")
  printf '%s\n%s\n' "$op" "$json" | "${COMPOSE[@]}" run -T --rm --entrypoint sh vault-init -c '
    IFS= read -r PW
    IFS= read -r JSON
    TOKEN=$(vault write -field=token auth/userpass/login/operator password="$PW") || exit 1
    printf "%s" "$JSON" | VAULT_TOKEN=$TOKEN vault kv put "secret/$APP_ENV/google-smtp" - >/dev/null
  ' >/dev/null 2>&1 || die "could not write the secret (wrong operator password?)"
  info "secret/$APP_ENV/google-smtp saved"
}

check_env_switch() {
  local last=""
  if [ -s "$STATE/last-env" ]; then
    last=$(cat "$STATE/last-env")
  fi
  if [ -n "$last" ] && [ "$last" != "$ENV" ] && docker volume ls -q | grep -qx "$DB_VOLUME"; then
    warn "the Keycloak database was created for env '$last', its password does not match '$ENV'"
    confirm "Remove the Keycloak database ($DB_VOLUME) and continue? Vault data is kept." || die "aborted"
    "${COMPOSE[@]}" down >/dev/null 2>&1 </dev/null || true
    docker volume rm "$DB_VOLUME" >/dev/null
  fi
}

cmd_up() {
  ENV=${1:-test}
  case "$ENV" in
    test|prod) ;;
    *) die "env must be test or prod" ;;
  esac
  export APP_ENV=$ENV

  require_docker
  check_gmail
  check_env_switch

  info "starting Vault"
  "${COMPOSE[@]}" up -d vault </dev/null
  wait_for "Vault API" 40 vault_api_up

  if ! vault_initialized || ! state_ready "$ENV"; then
    info "running Vault bootstrap"
    "${COMPOSE[@]}" --profile bootstrap run --rm vault-bootstrap || die "bootstrap failed (if the unseal key is missing, run: deploy/stack.sh reset)"
  fi

  info "unsealing Vault and loading secrets for $ENV"
  "${COMPOSE[@]}" run -T --rm vault-init </dev/null || die "vault-init failed"

  has_google_secret || prompt_google_secret

  info "starting the stack ($ENV)"
  "${COMPOSE[@]}" build --quiet </dev/null >/dev/null
  "${COMPOSE[@]}" up -d </dev/null
  wait_for "the API" 100 api_healthy
  printf '%s\n' "$ENV" > "$STATE/last-env"

  local admin_hint="password in Vault: secret/prod/keycloak"
  if [ "$ENV" = test ]; then
    admin_hint="admin / admin"
  fi
  cat <<EOF

Stack is up (env: $ENV)
  API:      http://localhost:8000/docs
  Keycloak: http://localhost:8080  (realm sport-pari, admin: $admin_hint)
  Vault:    http://127.0.0.1:8200  (login method: Username, user: operator)

SMTP settings from Vault are applied by keycloak-sync within 30 seconds.
EOF
}

cmd_status() {
  require_docker
  "${COMPOSE[@]}" ps -a --format 'table {{.Service}}\t{{.State}}\t{{.Status}}' </dev/null
  local seal
  seal=$(curl -s "$VAULT_URL/v1/sys/seal-status" || true)
  case "$seal" in
    *'"initialized":false'*) echo "Vault: not initialized" ;;
    *'"sealed":true'*) echo "Vault: sealed" ;;
    *'"sealed":false'*) echo "Vault: unsealed" ;;
    *) echo "Vault: not reachable" ;;
  esac
  if [ -s "$STATE/last-env" ]; then
    echo "Last env: $(cat "$STATE/last-env")"
  fi
}

cmd_down() {
  require_docker
  "${COMPOSE[@]}" down </dev/null
}

cmd_reset() {
  require_docker
  confirm "This removes all containers, volumes (Vault, Keycloak data) and Vault state files. Continue?" || die "aborted"
  "${COMPOSE[@]}" down -v --remove-orphans </dev/null
  rm -rf "$STATE/unseal.key" "$STATE/approle" "$STATE/last-env"
  info "reset complete"
}

case "${1:-}" in
  up) shift; cmd_up "$@" ;;
  status) cmd_status ;;
  down) cmd_down ;;
  reset) cmd_reset ;;
  *) usage; exit 1 ;;
esac
