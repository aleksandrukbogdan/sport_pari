#!/bin/sh
set -eu
. /scripts/lib.sh

generate_root() {
  vault operator generate-root -cancel >/dev/null 2>&1 || true
  INIT=$(vault operator generate-root -init -format=json)
  NONCE=$(printf '%s\n' "$INIT" | sed -n 's/.*"nonce": *"\([^"]*\)".*/\1/p')
  OTP=$(printf '%s\n' "$INIT" | sed -n 's/.*"otp": *"\([^"]*\)".*/\1/p')
  DONE=$(vault operator generate-root -nonce="$NONCE" -format=json - < /state/unseal.key)
  ENC=$(printf '%s\n' "$DONE" | sed -n 's/.*"encoded_token": *"\([^"]*\)".*/\1/p')
  vault operator generate-root -decode="$ENC" -otp="$OTP"
}

rand() {
  head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32
}

seed() {
  if vault kv metadata get "secret/$1/keycloak" >/dev/null 2>&1; then
    echo "secret/$1/keycloak exists, skipped"
    return
  fi
  printf '{"admin_username":"admin","admin_password":"%s","db_password":"%s","client_secret":"%s"}' "$2" "$3" "$4" \
    | vault kv put "secret/$1/keycloak" - >/dev/null
  echo "secret/$1/keycloak seeded"
}

wait_vault
mkdir -p /state/approle
REINIT=0

if ! is_initialized; then
  OUT=$(vault operator init -key-shares=1 -key-threshold=1 -format=json)
  KEY=$(printf '%s\n' "$OUT" | awk '/unseal_keys_b64/ {getline; gsub(/[ ",]/, ""); print; exit}')
  ROOT=$(printf '%s\n' "$OUT" | sed -n 's/.*"root_token": *"\([^"]*\)".*/\1/p')
  (umask 277; printf '%s' "$KEY" > /state/unseal.key)
  vault operator unseal "$KEY" >/dev/null
  unset KEY OUT
  REINIT=1
  echo "vault initialized, unseal key written to /state/unseal.key"
else
  if [ ! -s /state/unseal.key ]; then
    echo "vault is initialized but /state/unseal.key is missing" >&2
    exit 1
  fi
  if is_sealed; then
    unseal_with_file
  fi
  ROOT=$(generate_root)
fi

export VAULT_TOKEN="$ROOT"
unset ROOT
trap 'vault token revoke -self >/dev/null 2>&1 && echo "temporary root token revoked" >&2' EXIT

vault secrets list -format=json | grep -q '"secret/"' || vault secrets enable -path=secret -version=2 kv >/dev/null

seed test admin keycloak dev-secret-change-me
seed prod "$(rand)" "$(rand)" "$(rand)"

for env in test prod; do
  vault policy write "keycloak-$env" - >/dev/null <<EOF
path "secret/data/$env/*" {
  capabilities = ["read"]
}
path "secret/metadata/$env/*" {
  capabilities = ["read"]
}
EOF
done

vault policy write operator - >/dev/null <<'EOF'
path "secret/data/*" {
  capabilities = ["create", "read", "update", "patch", "delete", "list"]
}
path "secret/metadata/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/delete/*" {
  capabilities = ["update"]
}
path "secret/undelete/*" {
  capabilities = ["update"]
}
EOF

vault auth list -format=json | grep -q '"approle/"' || vault auth enable approle >/dev/null

for env in test prod; do
  vault write "auth/approle/role/keycloak-$env" token_policies="keycloak-$env" token_ttl=15m token_max_ttl=1h >/dev/null
  if [ "$REINIT" = 1 ] || [ ! -s "/state/approle/$env.env" ]; then
    RID=$(vault read -field=role_id "auth/approle/role/keycloak-$env/role-id")
    SID=$(vault write -f -field=secret_id "auth/approle/role/keycloak-$env/secret-id")
    (umask 277; printf 'VAULT_ROLE_ID=%s\nVAULT_SECRET_ID=%s\n' "$RID" "$SID" > "/state/approle/$env.env")
    echo "approle credentials for $env written"
  else
    echo "approle credentials for $env exist, skipped"
  fi
done

vault auth list -format=json | grep -q '"userpass/"' || vault auth enable userpass >/dev/null

if vault read auth/userpass/users/operator >/dev/null 2>&1; then
  echo "user operator exists, skipped"
else
  if [ ! -t 0 ] || [ ! -t 1 ]; then
    echo "operator password prompt needs a terminal: run without -T" >&2
    exit 1
  fi
  printf 'Operator password: ' >&2
  stty -echo
  read -r P1
  stty echo
  printf '\nRepeat password: ' >&2
  stty -echo
  read -r P2
  stty echo
  printf '\n' >&2
  if [ -z "$P1" ] || [ "$P1" != "$P2" ]; then
    echo "passwords do not match or are empty" >&2
    exit 1
  fi
  PWFILE=$(mktemp)
  (umask 077; printf '%s' "$P1" > "$PWFILE")
  vault write auth/userpass/users/operator password=@"$PWFILE" policies=operator >/dev/null
  rm -f "$PWFILE"
  unset P1 P2
  echo "user operator created"
fi

echo "bootstrap complete"
