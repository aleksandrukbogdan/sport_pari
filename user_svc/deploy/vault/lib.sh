vault_status() {
  vault status -format=json 2>/dev/null || true
}

wait_vault() {
  i=0
  until vault_status | grep -q '"initialized"'; do
    i=$((i + 1))
    if [ "$i" -gt 60 ]; then
      echo "vault is unreachable at ${VAULT_ADDR}" >&2
      exit 1
    fi
    sleep 2
  done
}

is_initialized() {
  vault_status | grep -q '"initialized": true'
}

is_sealed() {
  vault_status | grep -q '"sealed": true'
}

unseal_with_file() {
  if [ ! -s /state/unseal.key ]; then
    echo "unseal key not found at /state/unseal.key: run vault-bootstrap first" >&2
    exit 1
  fi
  vault operator unseal "$(cat /state/unseal.key)" >/dev/null
}

approle_login() {
  . "/state/approle/$1.env"
  vault write -field=token auth/approle/login role_id="$VAULT_ROLE_ID" secret_id="$VAULT_SECRET_ID"
}

shquote() {
  printf "'"
  printf '%s' "$1" | sed "s/'/'\\\\''/g"
  printf "'"
}
