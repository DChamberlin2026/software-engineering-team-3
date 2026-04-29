# Simulated E-Banking System

This repository contains the Django implementation for the Simulated E-Banking System (SEBS). SEBS is a locally hosted web application that uses simulated account data and simulated banking transactions for course demonstration purposes.

## Database Design

The SEBS database layer uses Django models with SQLite for local development. The core database entities are `UserProfile`, `Account`, `Transaction`, and `ActivityLog`.

Django's built-in `User` model is used for authentication data, including username, password hash, email, first name, last name, and last login. The `UserProfile` model extends this with a role field for customer or administrator access.

The `Account` model stores simulated bank accounts. Each account belongs to one user and includes an account number, account name, account type, and balance.

The `Transaction` model stores deposits, withdrawals, transfer-in records, and transfer-out records. Transfers are represented by two transaction records: one for the source account and one for the destination account.

The `ActivityLog` model stores important system events such as deposits, withdrawals, transfers, login events, failed logins, logout events, and administrative account changes.

## Database Requirement Mapping

- `DB-REQ-001`: Customer account records are stored in the `Account` model.
- `DB-REQ-002`: Account identifiers and balances are stored in the `Account` model.
- `DB-REQ-003`: Transaction records are stored in the `Transaction` model.
- `DB-REQ-004`: Authentication information is handled through Django's built-in `User` model.
- `REL-REQ-001`: Account balances and transaction records are kept consistent through database service functions.
- `REL-REQ-002`: Failed transfer and withdrawal operations raise errors before modifying stored account data.

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate