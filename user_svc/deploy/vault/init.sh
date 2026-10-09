#!/bin/sh
set -eu
. /scripts/lib.sh

APP_ENV="${APP_ENV:-test}"
case "$APP_ENV" in
  test|prod) ;;
  *)
    echo "APP_ENV must be test or prod" >&2
    exit 1
    ;;
esac

wait_vault

if ! is_initialized; then
  echo "vault is not initialized: run vault-bootstrap first" >&2
  exit 1
fi

if is_sealed; then
  unseal_with_file
  echo "vault unsealed"
fi

if [ ! -s "/state/approle/$APP_ENV.env" ]; then
  echo "approle credentials for $APP_ENV not found: run vault-bootstrap first" >&2
  exit 1
fi

VAULT_TOKEN=$(approle_login "$APP_ENV")
export VAULT_TOKEN

rm -f /secrets/runtime.env /secrets/runtime.env.tmp

ADMIN_USERNAME=$(vault kv get -field=admin_username "secret/$APP_ENV/keycloak")
ADMIN_PASSWORD=$(vault kv get -field=admin_password "secret/$APP_ENV/keycloak")
DB_PASSWORD=$(vault kv get -field=db_password "secret/$APP_ENV/keycloak")
CLIENT_SECRET=$(vault kv get -field=client_secret "secret/$APP_ENV/keycloak")

{
  printf 'export KC_BOOTSTRAP_ADMIN_USERNAME=%s\n' "$(shquote "$ADMIN_USERNAME")"
  printf 'export KC_BOOTSTRAP_ADMIN_PASSWORD=%s\n' "$(shquote "$ADMIN_PASSWORD")"
  printf 'export KC_DB_PASSWORD=%s\n' "$(shquote "$DB_PASSWORD")"
  printf 'export POSTGRES_PASSWORD=%s\n' "$(shquote "$DB_PASSWORD")"
  printf 'export USER_SVC_CLIENT_SECRET=%s\n' "$(shquote "$CLIENT_SECRET")"
  printf 'export KEYCLOAK_CLIENT_SECRET=%s\n' "$(shquote "$CLIENT_SECRET")"
} > /secrets/runtime.env.tmp

chmod 444 /secrets/runtime.env.tmp
mv /secrets/runtime.env.tmp /secrets/runtime.env
echo "runtime.env written for $APP_ENV"
