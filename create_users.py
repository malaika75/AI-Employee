#!/usr/bin/env python3
"""
User Management Script
Create and manage users for the AI Employee Dashboard
"""
import json
import bcrypt
from pathlib import Path

# Create vault directory if it doesn't exist
vault_path = Path("vault")
vault_path.mkdir(exist_ok=True)

# Users file path
users_file = vault_path / "Users.json"

def load_users():
    """Load existing users from file"""
    if users_file.exists():
        with open(users_file, 'r') as f:
            return json.load(f)
    return {}

def save_users(users_data):
    """Save users to file"""
    with open(users_file, 'w') as f:
        json.dump(users_data, f, indent=2)

def create_user(username, password, role):
    """Create a new user"""
    users_data = load_users()

    # Check if username already exists
    for user in users_data.values():
        if user['username'] == username:
            print(f"Error: Username '{username}' already exists!")
            return False

    # Generate new user ID
    if users_data:
        new_id = str(max([int(k) for k in users_data.keys()]) + 1)
    else:
        new_id = "1"

    # Hash password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # Add new user
    users_data[new_id] = {
        "username": username,
        "password": hashed_password,
        "role": role
    }

    # Save to file
    save_users(users_data)
    print(f"\n✅ User created successfully!")
    print(f"   Username: {username}")
    print(f"   Role: {role}")
    return True

def list_users():
    """List all existing users"""
    users_data = load_users()
    if not users_data:
        print("No users found.")
        return

    print("\n📋 Current Users:")
    print("-" * 50)
    for user_id, user in users_data.items():
        print(f"   ID: {user_id} | Username: {user['username']} | Role: {user['role']}")
    print("-" * 50)

def reset_admin():
    """Reset admin user to default"""
    users_data = {
        "1": {
            "username": "admin",
            "password": bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            "role": "Admin"
        }
    }
    save_users(users_data)
    print("\n✅ Admin user reset successfully!")
    print("   Username: admin")
    print("   Password: admin123")
    print("   Role: Admin")

def main():
    """Main menu"""
    print("=" * 50)
    print("   AI Employee - User Management")
    print("=" * 50)

    while True:
        print("\nOptions:")
        print("1. Create new user")
        print("2. List all users")
        print("3. Reset admin user (admin/admin123)")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            print("\n--- Create New User ---")
            username = input("Enter username: ").strip()
            if not username:
                print("Error: Username cannot be empty!")
                continue

            password = input("Enter password: ").strip()
            if not password:
                print("Error: Password cannot be empty!")
                continue

            print("\nAvailable roles:")
            print("  1. Admin (Full access)")
            print("  2. Approver (Can approve tasks, view financials)")
            print("  3. Viewer (Read-only access)")

            role_choice = input("Enter role (1-3): ").strip()

            if role_choice == "1":
                role = "Admin"
            elif role_choice == "2":
                role = "Approver"
            elif role_choice == "3":
                role = "Viewer"
            else:
                print("Error: Invalid role choice!")
                continue

            create_user(username, password, role)

        elif choice == "2":
            list_users()

        elif choice == "3":
            confirm = input("\n⚠️  This will reset admin user to default. Continue? (yes/no): ").strip().lower()
            if confirm == "yes":
                reset_admin()
            else:
                print("Cancelled.")

        elif choice == "4":
            print("\nGoodbye!")
            break

        else:
            print("Error: Invalid choice!")

if __name__ == "__main__":
    main()