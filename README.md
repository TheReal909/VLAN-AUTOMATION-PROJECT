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
