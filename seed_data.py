from werkzeug.security import generate_password_hash
from models.database import init_db, execute_db, query_db


def seed():
    """Seed the database with demo users."""
    init_db()

    # Check if already seeded
    existing = query_db('SELECT COUNT(*) as count FROM users')
    if existing and existing[0]['count'] > 0:
        print("[!] Database already seeded. Skipping...")
        return

    password = generate_password_hash('pass123')

    # Students
    users = [
        ('STU001', password, 'Arun Kumar', 'STU001', 'CSE', 3, 'Block A', '', 'student', '9876543210'),
        ('STU002', password, 'Priya Sharma', 'STU002', 'ECE', 2, 'Block B', '', 'student', '9876543211'),
        ('STU003', password, 'Rahul Verma', 'STU003', 'CSE', 4, 'Block A', '', 'student', '9876543212'),
        ('STU004', password, 'Sneha Reddy', 'STU004', 'ECE', 3, 'Block C', '', 'student', '9876543213'),
        # HODs
        ('HOD_CSE', password, 'Dr. Ramesh Iyer', '', 'CSE', None, '', '', 'hod', ''),
        ('HOD_ECE', password, 'Dr. Lakshmi Nair', '', 'ECE', None, '', '', 'hod', ''),
        # Wardens
        ('WARDEN1', password, 'Mr. Suresh Pillai', '', '', None, '', '', 'warden', ''),
        # Security
        ('SEC001', password, 'Raju Singh', '', '', None, '', '', 'security', ''),
        ('SEC002', password, 'Mohan Das', '', '', None, '', '', 'security', ''),
    ]

    for u in users:
        execute_db(
            '''INSERT INTO users
               (username, password_hash, name, roll_no, department, year, hostel_block, photo_url, role, parent_contact)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            u
        )

    print("[OK] Database seeded with demo users!")
    print("")
    print("Demo Accounts:")
    print("-" * 45)
    print(f"  {'Role':<12} {'Username':<12} {'Password'}")
    print("-" * 45)
    print(f"  {'Student':<12} {'STU001':<12} pass123")
    print(f"  {'Student':<12} {'STU002':<12} pass123")
    print(f"  {'HOD (CSE)':<12} {'HOD_CSE':<12} pass123")
    print(f"  {'HOD (ECE)':<12} {'HOD_ECE':<12} pass123")
    print(f"  {'Warden':<12} {'WARDEN1':<12} pass123")
    print(f"  {'Security':<12} {'SEC001':<12} pass123")
    print("-" * 45)


if __name__ == '__main__':
    seed()
