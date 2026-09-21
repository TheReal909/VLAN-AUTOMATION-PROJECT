# VLAN Automation Portal

This repository lays out a Django-based VLAN management portal with separate apps for inventory, discovery, change control, and auditing.

## Project layout

- `vlan_portal/config/` - Django settings, URL routing, deployment config
- `vlan_portal/inventory/` - facilities, switches, VLAN profiles
- `vlan_portal/discovery/` - MAC table collection and CLI parsers
- `vlan_portal/changes/` - change requests, approvals, jobs, rollback logic
- `vlan_portal/audit/` - append-only audit records and SIEM export
- `vlan_portal/templates/` - server-rendered templates
- `vlan_portal/tests/` - parser, policy, and integration tests

## Local setup

1. Create a Python 3.12+ virtual environment:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Copy the example environment file and update values:
   ```bash
   cp .env.example .env
   ```
4. Run migrations and start the app:
   ```bash
   python vlan_portal/manage.py migrate
   python vlan_portal/manage.py runserver
   ```

## Inventory validation

Validate an XLSX inventory without changing the database:

```bash
python vlan_portal/manage.py validate_inventory /path/to/inventory.xlsx
```

The command checks switch identity, management IPs, model families, MDF/IDF roles,
upstream references, and VLAN policy rows. It is intentionally read-only.

Live discovery uses read-only SSH credentials supplied through local environment
variables. Never commit these values:

```text
DISCOVERY_SSH_USERNAME=readonly-user
DISCOVERY_SSH_PASSWORD=secret
DISCOVERY_SSH_PORT=22
DISCOVERY_SSH_TIMEOUT=10

CHANGE_EXECUTION_ENABLED=False
CHANGE_COMMAND_MODE=legacy
CHANGE_SSH_USERNAME=change-user
CHANGE_SSH_PASSWORD=secret
CHANGE_SSH_PORT=22
CHANGE_SSH_TIMEOUT=10
```

## Database

This project expects PostgreSQL running locally. A typical configuration is:

```text
postgresql://postgres:postgres@localhost:5432/vlan_portal
```

## Optional authentication

If you are using Active Directory or LDAPS directly, add:

```bash
pip install django-auth-ldap
```

and configure the values in `.env` and the Django LDAP settings in `config/settings.py`.
